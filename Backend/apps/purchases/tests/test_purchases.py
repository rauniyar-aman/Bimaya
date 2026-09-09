"""Tests for the customer purchase endpoints (``/api/v1/purchases/``)."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import CustomerKyc
from apps.payments.models import Payment
from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider

from ..models import PolicyPurchase, ProviderPayout

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_customer(email="cust@bimaya.test"):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.CUSTOMER, is_verified=True
    )


def make_self_kyc(customer, *, is_self=True, status=CustomerKyc.Status.PENDING):
    return CustomerKyc.objects.create(
        customer=customer,
        is_self=is_self,
        full_name="Sita Sharma",
        permanent_address="Kathmandu",
        document_type=CustomerKyc.DocumentType.NID,
        document_number="NID-123",
        document_front="kyc/2026/09/front.png",
        status=status,
    )


def make_provider(email="prov@bimaya.test", company="Everest Life", *, approved=True):
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.PROVIDER, is_verified=True
    )
    return Provider.objects.create(user=user, company_name=company, is_approved=approved)


def make_policy(provider, category, name="Term Shield", **kwargs):
    defaults = {
        "premium": Decimal("10000.00"),
        "coverage_amount": Decimal("1000000.00"),
        "term_months": 12,
        "status": Policy.Status.APPROVED,
    }
    defaults.update(kwargs)
    return Policy.objects.create(provider=provider, category=category, name=name, **defaults)


@no_throttle
class PolicyPurchaseCreateTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.customer = make_customer()
        self.list_url = reverse("purchase-list")

    def _payload(self, policy, **overrides):
        payload = {
            "policy": policy.id,
            "nominee_name": "Sita Sharma",
            "nominee_relationship": "Spouse",
            "nominee_contact": "9800000000",
        }
        payload.update(overrides)
        return payload

    def test_can_purchase_public_policy(self):
        policy = make_policy(self.provider, self.category)
        kyc = make_self_kyc(self.customer)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url, self._payload(policy, kyc=kyc.id), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], PolicyPurchase.Status.PENDING_PAYMENT)
        self.assertIsNone(response.data["policy_number"])
        purchase = PolicyPurchase.objects.get(id=response.data["id"])
        self.assertEqual(purchase.customer, self.customer)
        self.assertEqual(purchase.kyc, kyc)

    def test_purchase_requires_kyc(self):
        policy = make_policy(self.provider, self.category)
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.list_url, self._payload(policy), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("kyc", response.data["errors"])

    def test_cannot_use_another_customers_kyc(self):
        policy = make_policy(self.provider, self.category)
        other = make_customer("other@bimaya.test")
        other_kyc = make_self_kyc(other)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url, self._payload(policy, kyc=other_kyc.id), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("kyc", response.data["errors"])

    def test_self_purchase_requires_self_kyc(self):
        policy = make_policy(self.provider, self.category)
        beneficiary_kyc = make_self_kyc(self.customer, is_self=False)
        self.client.force_authenticate(self.customer)
        response = self.client.post(
            self.list_url,
            self._payload(policy, kyc=beneficiary_kyc.id, insured_is_self=True),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("kyc", response.data["errors"])

    def test_cannot_purchase_draft_policy(self):
        policy = make_policy(self.provider, self.category, status=Policy.Status.DRAFT)
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.list_url, self._payload(policy), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("policy", response.data["errors"])

    def test_cannot_purchase_policy_from_unapproved_provider(self):
        pending_provider = make_provider(
            "pending@bimaya.test", "New Insurer", approved=False
        )
        policy = make_policy(pending_provider, self.category, name="Unapproved Plan")
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.list_url, self._payload(policy), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_provider_cannot_create_a_purchase(self):
        policy = make_policy(self.provider, self.category)
        provider_user = User.objects.get(email=self.provider.user.email)
        self.client.force_authenticate(provider_user)
        response = self.client.post(self.list_url, self._payload(policy), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_shows_only_own_purchases(self):
        policy = make_policy(self.provider, self.category)
        other_customer = make_customer("other@bimaya.test")
        PolicyPurchase.objects.create(
            customer=other_customer,
            policy=policy,
            nominee_name="Other Nominee",
            nominee_relationship="Sibling",
            nominee_contact="9811111111",
        )
        mine = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=policy,
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
        )
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.list_url)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {mine.id})


@no_throttle
class PolicyPurchaseDetailTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
        )

    def test_owner_can_view_detail(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(reverse("purchase-detail", args=[self.purchase.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.purchase.id)

    def test_other_customer_cannot_view_purchase(self):
        other = make_customer("other@bimaya.test")
        self.client.force_authenticate(other)
        response = self.client.get(reverse("purchase-detail", args=[self.purchase.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_is_unauthorized(self):
        response = self.client.get(reverse("purchase-detail", args=[self.purchase.id]))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@no_throttle
class PolicyPurchaseCancelTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
        )

    def test_cancel_pending_purchase(self):
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("purchase-cancel", args=[self.purchase.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, PolicyPurchase.Status.CANCELLED)

    def test_cannot_cancel_active_purchase(self):
        self.purchase.status = PolicyPurchase.Status.ACTIVE
        self.purchase.save(update_fields=["status"])
        self.client.force_authenticate(self.customer)
        response = self.client.post(reverse("purchase-cancel", args=[self.purchase.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "purchase_not_cancellable")
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, PolicyPurchase.Status.ACTIVE)

    def test_other_customer_cannot_cancel(self):
        other = make_customer("other@bimaya.test")
        self.client.force_authenticate(other)
        response = self.client.post(reverse("purchase-cancel", args=[self.purchase.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@no_throttle
class PurchaseStateMachineTests(APITestCase):
    """The buy → pay → forward → issue lifecycle at the model level."""

    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category, term_months=12)
        self.customer = make_customer()
        self.purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            kyc=make_self_kyc(self.customer),
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
        )

    def test_mark_paid_does_not_issue(self):
        self.purchase.mark_paid()
        self.assertEqual(self.purchase.status, PolicyPurchase.Status.PAID)
        self.assertIsNone(self.purchase.policy_number)
        self.assertIsNone(self.purchase.start_date)

    def test_forward_requires_paid(self):
        with self.assertRaises(ValueError):
            self.purchase.forward_to_provider()

    def test_issue_requires_forwarded(self):
        self.purchase.mark_paid()
        with self.assertRaises(ValueError):
            self.purchase.issue("BIM-MANUAL-1")

    def test_full_lifecycle_to_issued(self):
        self.purchase.mark_paid()
        self.purchase.forward_to_provider()
        self.purchase.issue("NLI-2026-0001")
        self.assertEqual(self.purchase.status, PolicyPurchase.Status.ACTIVE)
        self.assertEqual(self.purchase.policy_number, "NLI-2026-0001")
        self.assertEqual(self.purchase.start_date, date.today())
        self.assertIsNotNone(self.purchase.end_date)


class ProviderPayoutTests(APITestCase):
    """Commission accounting: a payout is created when a policy is issued."""

    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()  # default commission_rate = 10.00
        self.policy = make_policy(
            self.provider, self.category, premium=Decimal("10000.00")
        )
        self.customer = make_customer()

    def _issue(self):
        purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            kyc=make_self_kyc(self.customer),
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
            status=PolicyPurchase.Status.FORWARDED,
        )
        purchase.issue("NLI-2026-0100")
        return purchase

    def test_payout_created_on_issue_with_correct_amounts(self):
        purchase = self._issue()
        payout = ProviderPayout.objects.get(purchase=purchase)
        self.assertEqual(payout.provider, self.provider)
        self.assertEqual(payout.gross_amount, Decimal("10000.00"))
        self.assertEqual(payout.commission_rate, Decimal("10.00"))
        self.assertEqual(payout.commission_amount, Decimal("1000.00"))
        self.assertEqual(payout.net_amount, Decimal("9000.00"))
        self.assertEqual(payout.status, ProviderPayout.Status.PENDING)

    def test_payout_is_idempotent(self):
        purchase = self._issue()
        # A second call must not create a duplicate payout.
        ProviderPayout.create_for_purchase(purchase)
        self.assertEqual(ProviderPayout.objects.filter(purchase=purchase).count(), 1)

    def test_rate_is_snapshotted_at_issuance(self):
        purchase = self._issue()
        payout = ProviderPayout.objects.get(purchase=purchase)
        # Changing the provider's rate later must not rewrite history.
        self.provider.commission_rate = Decimal("25.00")
        self.provider.save(update_fields=["commission_rate"])
        payout.refresh_from_db()
        self.assertEqual(payout.commission_rate, Decimal("10.00"))
        self.assertEqual(payout.commission_amount, Decimal("1000.00"))

    def test_custom_rate_is_applied(self):
        self.provider.commission_rate = Decimal("12.50")
        self.provider.save(update_fields=["commission_rate"])
        purchase = self._issue()
        payout = ProviderPayout.objects.get(purchase=purchase)
        self.assertEqual(payout.commission_amount, Decimal("1250.00"))
        self.assertEqual(payout.net_amount, Decimal("8750.00"))

    def test_mark_paid_sets_status_and_timestamp(self):
        purchase = self._issue()
        payout = ProviderPayout.objects.get(purchase=purchase)
        payout.mark_paid()
        payout.refresh_from_db()
        self.assertEqual(payout.status, ProviderPayout.Status.PAID)
        self.assertIsNotNone(payout.paid_at)


@no_throttle
class ProviderIssuanceTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.provider_user = self.provider.user
        self.purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            kyc=make_self_kyc(self.customer, status=CustomerKyc.Status.VERIFIED),
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
            status=PolicyPurchase.Status.FORWARDED,
        )
        self.list_url = reverse("provider-issuance-list")
        self.issue_url = reverse("provider-issuance-issue", args=[self.purchase.id])

    def test_queue_lists_only_forwarded_own_purchases(self):
        # A non-forwarded purchase should not appear.
        PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            kyc=make_self_kyc(make_customer("c2@bimaya.test")),
            nominee_name="X",
            nominee_relationship="Y",
            nominee_contact="9800000001",
            status=PolicyPurchase.Status.PAID,
        )
        self.client.force_authenticate(self.provider_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {self.purchase.id})

    def test_provider_issues_with_own_number(self):
        self.client.force_authenticate(self.provider_user)
        response = self.client.post(
            self.issue_url, {"policy_number": "NLI-2026-0009"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.purchase.refresh_from_db()
        self.assertEqual(self.purchase.status, PolicyPurchase.Status.ACTIVE)
        self.assertEqual(self.purchase.policy_number, "NLI-2026-0009")

    def test_duplicate_policy_number_rejected(self):
        other = make_provider("p2@bimaya.test", "Other Co")
        PolicyPurchase.objects.create(
            customer=self.customer,
            policy=make_policy(other, self.category, name="Other Plan"),
            kyc=make_self_kyc(make_customer("c3@bimaya.test")),
            nominee_name="X",
            nominee_relationship="Y",
            nominee_contact="9800000002",
            status=PolicyPurchase.Status.ACTIVE,
            policy_number="DUP-1",
        )
        self.client.force_authenticate(self.provider_user)
        response = self.client.post(
            self.issue_url, {"policy_number": "DUP-1"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("policy_number", response.data["errors"])

    def test_other_provider_cannot_issue(self):
        other = make_provider("p3@bimaya.test", "Rival Co")
        self.client.force_authenticate(other.user)
        response = self.client.post(
            self.issue_url, {"policy_number": "RIV-1"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_issue_non_forwarded_purchase(self):
        self.purchase.status = PolicyPurchase.Status.PAID
        self.purchase.save(update_fields=["status"])
        self.client.force_authenticate(self.provider_user)
        response = self.client.post(
            self.issue_url, {"policy_number": "NLI-2026-0010"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "purchase_not_issuable")


@no_throttle
class ProviderPurchaseListTests(APITestCase):
    """The provider's read-only sales/history list across their own policies."""

    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.mine = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
            status=PolicyPurchase.Status.ACTIVE,
        )
        self.url = reverse("provider-purchase-list")

    def test_lists_all_own_purchases_regardless_of_status(self):
        # A pending-payment purchase on my policy should still appear here.
        PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            nominee_name="X",
            nominee_relationship="Y",
            nominee_contact="9800000001",
            status=PolicyPurchase.Status.PENDING_PAYMENT,
        )
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertIn("customer_name", response.data["results"][0])

    def test_excludes_other_providers_purchases(self):
        rival = make_provider("rival@bimaya.test", "Rival Co")
        PolicyPurchase.objects.create(
            customer=make_customer("c2@bimaya.test"),
            policy=make_policy(rival, self.category, name="Rival Plan"),
            nominee_name="X",
            nominee_relationship="Y",
            nominee_contact="9800000002",
            status=PolicyPurchase.Status.ACTIVE,
        )
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {self.mine.id})

    def test_status_filter(self):
        PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            nominee_name="X",
            nominee_relationship="Y",
            nominee_contact="9800000003",
            status=PolicyPurchase.Status.CANCELLED,
        )
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url, {"status": PolicyPurchase.Status.ACTIVE})
        statuses = {row["status"] for row in response.data["results"]}
        self.assertEqual(statuses, {PolicyPurchase.Status.ACTIVE})

    def test_customer_forbidden(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@no_throttle
class ProviderPayoutListTests(APITestCase):
    """The provider's read-only payout ledger, scoped to their own sales."""

    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.mine = self._issue(self.policy, "NLI-PAYOUT-1")
        self.url = reverse("provider-payout-list")

    def _issue(self, policy, number):
        # ``issue`` only needs a FORWARDED purchase; issuance creates the payout.
        purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=policy,
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
            status=PolicyPurchase.Status.FORWARDED,
        )
        purchase.issue(number)
        return purchase

    def test_lists_own_payouts_with_amounts(self):
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["policy_name"], self.policy.name)
        self.assertEqual(row["policy_number"], "NLI-PAYOUT-1")
        self.assertEqual(row["gross_amount"], "10000.00")
        self.assertEqual(row["commission_amount"], "1000.00")
        self.assertEqual(row["net_amount"], "9000.00")
        self.assertEqual(row["status"], ProviderPayout.Status.PENDING)
        # No cross-provider PII (no provider name / customer details on the row).
        self.assertNotIn("provider_name", row)

    def test_excludes_other_providers_payouts(self):
        rival = make_provider("rival@bimaya.test", "Rival Co")
        rival_policy = make_policy(rival, self.category, name="Rival Plan")
        PolicyPurchase.objects.create(
            customer=make_customer("c2@bimaya.test"),
            policy=rival_policy,
            nominee_name="X",
            nominee_relationship="Y",
            nominee_contact="9800000002",
            status=PolicyPurchase.Status.FORWARDED,
        ).issue("RIV-PAYOUT-1")
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url)
        numbers = {row["policy_number"] for row in response.data["results"]}
        self.assertEqual(numbers, {"NLI-PAYOUT-1"})

    def test_status_filter(self):
        payout = ProviderPayout.objects.get(purchase=self.mine)
        payout.mark_paid()
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url, {"status": ProviderPayout.Status.PENDING})
        self.assertEqual(response.data["count"], 0)

    def test_customer_forbidden(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@no_throttle
class PurchaseDocumentTests(APITestCase):
    """Owner-only certificate + receipt PDF downloads."""

    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            kyc=make_self_kyc(self.customer, status=CustomerKyc.Status.VERIFIED),
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
            status=PolicyPurchase.Status.ACTIVE,
            policy_number="NLI-2026-0001",
            start_date=date(2026, 9, 7),
            end_date=date(2027, 9, 7),
        )

    def _get(self, name):
        return self.client.get(reverse(name, args=[self.purchase.id]))

    def _pdf_bytes(self, response):
        return b"".join(response.streaming_content)

    def test_owner_downloads_certificate_pdf(self):
        self.client.force_authenticate(self.customer)
        response = self._get("purchase-certificate")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("Bimaya-Policy-NLI-2026-0001.pdf", response["Content-Disposition"])
        self.assertTrue(self._pdf_bytes(response).startswith(b"%PDF"))

    def test_certificate_unavailable_before_issue(self):
        self.purchase.status = PolicyPurchase.Status.PAID
        self.purchase.policy_number = None
        self.purchase.save(update_fields=["status", "policy_number"])
        self.client.force_authenticate(self.customer)
        response = self._get("purchase-certificate")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "document_not_available")

    def test_other_customer_cannot_download_certificate(self):
        self.client.force_authenticate(make_customer("other@bimaya.test"))
        response = self._get("purchase-certificate")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_anonymous_cannot_download_certificate(self):
        response = self._get("purchase-certificate")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_downloads_receipt_after_payment(self):
        Payment.objects.create(
            policy_purchase=self.purchase,
            amount=self.policy.premium,
            gateway=Payment.Gateway.ESEWA,
            status=Payment.Status.SUCCESS,
            gateway_transaction_id="TXN-123",
            paid_at=timezone.now(),
        )
        self.client.force_authenticate(self.customer)
        response = self._get("purchase-receipt")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertTrue(self._pdf_bytes(response).startswith(b"%PDF"))

    def test_receipt_unavailable_without_successful_payment(self):
        # An initiated-but-not-succeeded payment must not yield a receipt.
        Payment.objects.create(
            policy_purchase=self.purchase,
            amount=self.policy.premium,
            gateway=Payment.Gateway.KHALTI,
            status=Payment.Status.INITIATED,
        )
        self.client.force_authenticate(self.customer)
        response = self._get("purchase-receipt")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "document_not_available")
