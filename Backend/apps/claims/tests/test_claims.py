"""Tests for the claims endpoints (``/api/v1/claims/`` and
``/api/v1/provider/claims/``) and the claim state machine.

Uploads are routed to a throwaway ``MEDIA_ROOT`` so the repo's media folder is
never touched; ``tearDownModule`` removes it.
"""

import io
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider
from apps.purchases.models import PolicyPurchase

from ..models import Claim, ClaimDocument, ClaimPayout

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)

_MEDIA_ROOT = tempfile.mkdtemp(prefix="bimaya-claims-tests-")


def tearDownModule():
    shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)


def make_customer(email="cust@bimaya.test"):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.CUSTOMER, is_verified=True
    )


def make_provider(email="prov@bimaya.test", company="Everest Life", *, approved=True):
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.PROVIDER, is_verified=True
    )
    return Provider.objects.create(user=user, company_name=company, is_approved=approved)


def make_policy(provider, category, name="Motor Shield", **kwargs):
    defaults = {
        "premium": Decimal("10000.00"),
        "coverage_amount": Decimal("1000000.00"),
        "term_months": 12,
        "status": Policy.Status.APPROVED,
    }
    defaults.update(kwargs)
    return Policy.objects.create(provider=provider, category=category, name=name, **defaults)


def make_active_purchase(customer, policy, **overrides):
    """A purchase driven all the way to ``ACTIVE`` (start_date = today)."""
    purchase = PolicyPurchase.objects.create(
        customer=customer,
        policy=policy,
        nominee_name="Sita Sharma",
        nominee_relationship="Spouse",
        nominee_contact="9800000000",
        **overrides,
    )
    purchase.mark_paid()
    purchase.forward_to_provider()
    purchase.issue(f"NLI-{purchase.id}")
    return purchase


def make_png(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "blue").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_pdf(name="report.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4\n%%EOF\n", content_type="application/pdf")


def make_claim(customer, purchase, **overrides):
    defaults = {
        "incident_date": timezone.localdate(),
        "incident_location": "Kathmandu",
        "description": "The insured vehicle was damaged in a collision.",
        "claimed_amount": Decimal("15000.00"),
    }
    defaults.update(overrides)
    return Claim.objects.create(customer=customer, purchase=purchase, **defaults)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ClaimCreateTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.list_url = reverse("claim-list")

    def _payload(self, purchase, **overrides):
        payload = {
            "purchase": purchase.id,
            "incident_date": str(timezone.localdate()),
            "incident_location": "Kathmandu",
            "description": "Windshield shattered by a falling rock.",
            "claimed_amount": "15000.00",
            "documents": [make_png("photo.png"), make_pdf("report.pdf")],
        }
        payload.update(overrides)
        return payload

    def test_customer_files_claim_with_documents(self):
        purchase = make_active_purchase(self.customer, self.policy)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url, self._payload(purchase), format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Claim.Status.SUBMITTED)
        self.assertEqual(len(response.data["documents"]), 2)
        claim = Claim.objects.get(id=response.data["id"])
        self.assertEqual(claim.customer, self.customer)
        self.assertEqual(claim.documents.count(), 2)

    def test_cannot_claim_against_non_active_policy(self):
        purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            nominee_name="Sita",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
        )  # PENDING_PAYMENT
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url, self._payload(purchase), format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("purchase", response.data["errors"])

    def test_cannot_claim_against_another_customers_policy(self):
        other = make_customer("other@bimaya.test")
        purchase = make_active_purchase(other, self.policy)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url, self._payload(purchase), format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("purchase", response.data["errors"])

    def test_at_least_one_document_required(self):
        purchase = make_active_purchase(self.customer, self.policy)
        payload = self._payload(purchase)
        payload.pop("documents")
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.list_url, payload, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("documents", response.data["errors"])

    def test_cannot_open_second_claim_while_one_is_open(self):
        purchase = make_active_purchase(self.customer, self.policy)
        make_claim(self.customer, purchase)  # SUBMITTED, still open
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url, self._payload(purchase), format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("purchase", response.data["errors"])

    def test_future_incident_date_rejected(self):
        purchase = make_active_purchase(self.customer, self.policy)
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url,
            self._payload(purchase, incident_date=str(tomorrow)),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("incident_date", response.data["errors"])

    def test_incident_before_cover_start_rejected(self):
        purchase = make_active_purchase(self.customer, self.policy)
        yesterday = timezone.localdate() - timedelta(days=1)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url,
            self._payload(purchase, incident_date=str(yesterday)),
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("incident_date", response.data["errors"])

    def test_provider_cannot_file_a_claim(self):
        purchase = make_active_purchase(self.customer, self.policy)
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            self.list_url, self._payload(purchase), format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_shows_only_own_claims(self):
        purchase = make_active_purchase(self.customer, self.policy)
        mine = make_claim(self.customer, purchase)
        other = make_customer("other@bimaya.test")
        other_purchase = make_active_purchase(other, self.policy)
        make_claim(other, other_purchase)
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.list_url)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {mine.id})


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ClaimDetailTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = make_active_purchase(self.customer, self.policy)
        self.claim = make_claim(self.customer, self.purchase)

    def test_owner_can_view_detail(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("claim-detail", args=[self.claim.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.claim.id)

    def test_other_customer_cannot_view(self):
        self.client.force_authenticate(make_customer("other@bimaya.test"))
        response = self.client.get(reverse("claim-detail", args=[self.claim.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_is_unauthorized(self):
        response = self.client.get(reverse("claim-detail", args=[self.claim.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ProviderClaimQueueTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = make_active_purchase(self.customer, self.policy)
        self.claim = make_claim(self.customer, self.purchase)
        self.list_url = reverse("provider-claim-list")

    def test_queue_scoped_to_own_policies(self):
        rival = make_provider("rival@bimaya.test", "Rival Co")
        rival_policy = make_policy(rival, self.category, name="Rival Plan")
        rival_purchase = make_active_purchase(
            make_customer("c2@bimaya.test"), rival_policy
        )
        make_claim(rival_purchase.customer, rival_purchase)
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {self.claim.id})

    def test_status_filter(self):
        make_claim(
            self.customer,
            make_active_purchase(make_customer("c3@bimaya.test"), self.policy),
            status=Claim.Status.SETTLED,
        )
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.list_url, {"status": Claim.Status.SUBMITTED})
        statuses = {row["status"] for row in response.data["results"]}
        self.assertEqual(statuses, {Claim.Status.SUBMITTED})

    def test_start_review(self):
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-claim-start-review", args=[self.claim.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, Claim.Status.UNDER_REVIEW)

    def test_start_review_wrong_state(self):
        self.claim.start_review()  # already UNDER_REVIEW
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-claim-start-review", args=[self.claim.id])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "claim_not_decidable")

    def test_request_more_info(self):
        self.claim.start_review()
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-claim-request-info", args=[self.claim.id]),
            {"note": "Please attach the police report."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, Claim.Status.MORE_INFO)
        self.assertEqual(self.claim.review_note, "Please attach the police report.")

    def test_request_more_info_requires_note(self):
        self.claim.start_review()
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-claim-request-info", args=[self.claim.id]),
            {"note": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("note", response.data["errors"])

    def test_approve(self):
        self.claim.start_review()
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-claim-approve", args=[self.claim.id]),
            {"approved_amount": "12000.00", "note": "Approved in full."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, Claim.Status.APPROVED)
        self.assertEqual(self.claim.approved_amount, Decimal("12000.00"))
        self.assertIsNotNone(self.claim.decided_at)

    def test_approve_requires_under_review(self):
        self.client.force_authenticate(self.provider.user)  # still SUBMITTED
        response = self.client.post(
            reverse("provider-claim-approve", args=[self.claim.id]),
            {"approved_amount": "12000.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "claim_not_decidable")

    def test_reject(self):
        self.claim.start_review()
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            reverse("provider-claim-reject", args=[self.claim.id]),
            {"note": "Damage predates the cover."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, Claim.Status.REJECTED)

    def test_other_provider_cannot_act(self):
        rival = make_provider("rival@bimaya.test", "Rival Co")
        self.client.force_authenticate(rival.user)
        response = self.client.post(
            reverse("provider-claim-start-review", args=[self.claim.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ClaimResubmitTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = make_active_purchase(self.customer, self.policy)
        self.claim = make_claim(
            self.customer, self.purchase, status=Claim.Status.MORE_INFO
        )

    def test_resubmit_with_extra_document(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            reverse("claim-resubmit", args=[self.claim.id]),
            {"documents": [make_pdf("police-report.pdf")]},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, Claim.Status.UNDER_REVIEW)
        self.assertEqual(self.claim.documents.count(), 1)

    def test_resubmit_wrong_state(self):
        self.claim.status = Claim.Status.SUBMITTED
        self.claim.save(update_fields=["status"])
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("claim-resubmit", args=[self.claim.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "claim_not_resubmittable")

    def test_other_customer_cannot_resubmit(self):
        self.client.force_authenticate(make_customer("other@bimaya.test"))
        response = self.client.post(reverse("claim-resubmit", args=[self.claim.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ClaimPayoutTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = make_active_purchase(self.customer, self.policy)
        self.claim = make_claim(
            self.customer,
            self.purchase,
            status=Claim.Status.APPROVED,
            approved_amount=Decimal("12000.00"),
        )
        self.initiate_url = reverse("provider-claim-payout-initiate", args=[self.claim.id])
        self.confirm_url = reverse("provider-claim-payout-confirm", args=[self.claim.id])

    def test_initiate_creates_simulated_payout(self):
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            self.initiate_url, {"gateway": ClaimPayout.Gateway.ESEWA}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["simulated"])
        self.assertEqual(response.data["status"], ClaimPayout.Status.INITIATED)
        self.assertEqual(self.claim.payouts.count(), 1)

    def test_initiate_requires_approved_claim(self):
        self.claim.status = Claim.Status.UNDER_REVIEW
        self.claim.save(update_fields=["status"])
        self.client.force_authenticate(self.provider.user)
        response = self.client.post(
            self.initiate_url, {"gateway": ClaimPayout.Gateway.ESEWA}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "claim_not_payable")

    def test_cannot_initiate_twice(self):
        self.client.force_authenticate(self.provider.user)
        self.client.post(
            self.initiate_url, {"gateway": ClaimPayout.Gateway.ESEWA}, format="json"
        )
        response = self.client.post(
            self.initiate_url, {"gateway": ClaimPayout.Gateway.KHALTI}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "claim_not_payable")

    def test_confirm_settles_claim(self):
        self.client.force_authenticate(self.provider.user)
        self.client.post(
            self.initiate_url, {"gateway": ClaimPayout.Gateway.KHALTI}, format="json"
        )
        response = self.client.post(self.confirm_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Claim.Status.SETTLED)
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, Claim.Status.SETTLED)
        self.assertIsNotNone(self.claim.settled_at)
        payout = self.claim.payouts.get()
        self.assertEqual(payout.status, ClaimPayout.Status.SUCCESS)

    def test_second_confirm_is_rejected(self):
        self.client.force_authenticate(self.provider.user)
        self.client.post(
            self.initiate_url, {"gateway": ClaimPayout.Gateway.KHALTI}, format="json"
        )
        self.client.post(self.confirm_url, {}, format="json")
        response = self.client.post(self.confirm_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "payout_not_confirmable")


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ClaimDocumentDownloadTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = make_active_purchase(self.customer, self.policy)
        self.claim = make_claim(self.customer, self.purchase)
        self.document = ClaimDocument.objects.create(
            claim=self.claim, file=make_png("bill.png")
        )
        self.url = reverse("claim-document", args=[self.claim.id, self.document.id])

    def _body(self, response):
        return b"".join(response.streaming_content)

    def test_owner_downloads_document(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(self._body(response))

    def test_underwriting_provider_downloads_document(self):
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_customer_cannot_download(self):
        self.client.force_authenticate(make_customer("other@bimaya.test"))
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_provider_cannot_download(self):
        rival = make_provider("rival@bimaya.test", "Rival Co")
        self.client.force_authenticate(rival.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_cannot_download(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ClaimStateMachineTests(APITestCase):
    """The submit → review → decide → settle lifecycle at the model level."""

    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = make_active_purchase(self.customer, self.policy)
        self.claim = make_claim(self.customer, self.purchase)

    def test_start_review_requires_submitted(self):
        self.claim.start_review()
        with self.assertRaises(ValueError):
            self.claim.start_review()

    def test_request_more_info_requires_under_review(self):
        with self.assertRaises(ValueError):
            self.claim.request_more_info("more please")

    def test_resubmit_requires_more_info(self):
        with self.assertRaises(ValueError):
            self.claim.resubmit()

    def test_approve_requires_under_review(self):
        with self.assertRaises(ValueError):
            self.claim.approve(Decimal("100.00"))

    def test_reject_requires_under_review(self):
        with self.assertRaises(ValueError):
            self.claim.reject("no")

    def test_mark_settled_requires_approved(self):
        with self.assertRaises(ValueError):
            self.claim.mark_settled()

    def test_full_lifecycle_to_settled(self):
        self.claim.start_review()
        self.claim.request_more_info("Attach the police report.")
        self.claim.resubmit()
        self.claim.approve(Decimal("12000.00"), "Approved.")
        self.assertEqual(self.claim.status, Claim.Status.APPROVED)
        payout = ClaimPayout.objects.create(
            claim=self.claim,
            amount=self.claim.approved_amount,
            gateway=ClaimPayout.Gateway.ESEWA,
        )
        payout.mark_success("SIMPAYOUT-TEST")
        self.claim.refresh_from_db()
        self.assertEqual(self.claim.status, Claim.Status.SETTLED)
        self.assertIsNotNone(self.claim.settled_at)
