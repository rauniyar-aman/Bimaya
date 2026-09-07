"""Tests for the admin-panel REST APIs (``/api/v1/admin/...``).

Every endpoint is gated by :class:`IsPlatformAdmin`: customers/providers get
403, anonymous gets 401. State-changing actions reuse the shared model methods
and fan out notifications, so the tests assert both the transition and that the
right recipient(s) received an in-app notification.

Uploads route to a throwaway ``MEDIA_ROOT`` so the repo's media folder is never
touched; ``tearDownModule`` removes it.
"""

import io
import shutil
import tempfile
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

from apps.documents.models import CustomerKyc
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider
from apps.purchases.models import PolicyPurchase

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)

_MEDIA_ROOT = tempfile.mkdtemp(prefix="bimaya-adminpanel-tests-")


def tearDownModule():
    shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)


def make_admin(email="admin@bimaya.test"):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.ADMIN, is_verified=True
    )


def make_customer(email="cust@bimaya.test"):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.CUSTOMER, is_verified=True
    )


def make_provider(email="prov@bimaya.test", company="Everest Life", *, approved=False):
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.PROVIDER, is_verified=True
    )
    provider = Provider.objects.create(
        user=user, company_name=company, is_approved=approved
    )
    return provider


def make_policy(provider, category, name="Motor Shield", **kwargs):
    defaults = {
        "premium": Decimal("10000.00"),
        "coverage_amount": Decimal("1000000.00"),
        "term_months": 12,
        "status": Policy.Status.APPROVED,
    }
    defaults.update(kwargs)
    return Policy.objects.create(
        provider=provider, category=category, name=name, **defaults
    )


def make_image(name="doc.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_kyc(customer, *, status=CustomerKyc.Status.PENDING, **overrides):
    defaults = {
        "is_self": True,
        "full_name": "Sita Sharma",
        "permanent_address": "Kathmandu",
        "document_type": CustomerKyc.DocumentType.NID,
        "document_number": "NID-123",
        "document_front": make_image("front.png"),
        "status": status,
    }
    defaults.update(overrides)
    return CustomerKyc.objects.create(customer=customer, **defaults)


def make_purchase(customer, policy, **overrides):
    return PolicyPurchase.objects.create(
        customer=customer,
        policy=policy,
        nominee_name="Sita Sharma",
        nominee_relationship="Spouse",
        nominee_contact="9800000000",
        **overrides,
    )


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminAccessControlTests(APITestCase):
    """Every admin endpoint rejects non-admins the same way."""

    def setUp(self):
        self.customer = make_customer()
        self.provider = make_provider()
        self.url = reverse("admin-provider-list")

    def test_anonymous_is_unauthorized(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_is_forbidden(self):
        self.client.force_authenticate(self.customer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_provider_is_forbidden(self):
        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_is_allowed(self):
        self.client.force_authenticate(make_admin())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminProviderTests(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=False)
        make_policy(self.provider, self.category)
        self.client.force_authenticate(self.admin)

    def test_list_includes_policy_count_and_owner(self):
        response = self.client.get(reverse("admin-provider-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row = response.data["results"][0]
        self.assertEqual(row["policy_count"], 1)
        self.assertEqual(row["owner_email"], self.provider.user.email)

    def test_filter_by_is_approved(self):
        make_provider("prov2@bimaya.test", "Approved Co", approved=True)
        response = self.client.get(
            reverse("admin-provider-list"), {"is_approved": "true"}
        )
        names = {r["company_name"] for r in response.data["results"]}
        self.assertEqual(names, {"Approved Co"})

    def test_approve_flips_flag_and_notifies(self):
        response = self.client.post(
            reverse("admin-provider-approve", args=[self.provider.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_approved"])
        self.provider.refresh_from_db()
        self.assertTrue(self.provider.is_approved)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.provider.user,
                type=Notification.Type.PROVIDER_APPROVED,
            ).exists()
        )

    def test_approve_is_idempotent(self):
        self.client.post(reverse("admin-provider-approve", args=[self.provider.id]))
        self.client.post(reverse("admin-provider-approve", args=[self.provider.id]))
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.provider.user,
                type=Notification.Type.PROVIDER_APPROVED,
            ).count(),
            1,
        )

    def test_revoke_clears_flag(self):
        self.provider.is_approved = True
        self.provider.save(update_fields=["is_approved"])
        response = self.client.post(
            reverse("admin-provider-revoke", args=[self.provider.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_approved"])
        self.provider.refresh_from_db()
        self.assertFalse(self.provider.is_approved)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminKycTests(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.customer = make_customer()
        self.kyc = make_kyc(self.customer)
        self.client.force_authenticate(self.admin)

    def test_list_and_filter_by_status(self):
        make_kyc(
            make_customer("c2@bimaya.test"),
            status=CustomerKyc.Status.VERIFIED,
            document_number="NID-999",
        )
        response = self.client.get(
            reverse("admin-kyc-list"), {"status": CustomerKyc.Status.PENDING}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = {r["status"] for r in response.data["results"]}
        self.assertEqual(statuses, {CustomerKyc.Status.PENDING})

    def test_detail_hides_raw_image_urls(self):
        response = self.client.get(reverse("admin-kyc-detail", args=[self.kyc.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["has_front"])
        self.assertFalse(response.data["has_back"])
        self.assertNotIn("document_front", response.data)

    def test_download_front_document(self):
        response = self.client.get(
            reverse("admin-kyc-document-front", args=[self.kyc.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(b"".join(response.streaming_content))

    def test_download_missing_back_is_404(self):
        response = self.client.get(
            reverse("admin-kyc-document-back", args=[self.kyc.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_transitions_and_notifies(self):
        response = self.client.post(reverse("admin-kyc-verify", args=[self.kyc.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.kyc.refresh_from_db()
        self.assertEqual(self.kyc.status, CustomerKyc.Status.VERIFIED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.customer, type=Notification.Type.KYC_VERIFIED
            ).exists()
        )

    def test_reject_requires_note(self):
        response = self.client.post(
            reverse("admin-kyc-reject", args=[self.kyc.id]),
            {"note": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("note", response.data["errors"])

    def test_reject_transitions_and_notifies(self):
        response = self.client.post(
            reverse("admin-kyc-reject", args=[self.kyc.id]),
            {"note": "Document unreadable."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.kyc.refresh_from_db()
        self.assertEqual(self.kyc.status, CustomerKyc.Status.REJECTED)
        self.assertEqual(self.kyc.review_note, "Document unreadable.")
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.customer, type=Notification.Type.KYC_REJECTED
            ).exists()
        )


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminPurchaseForwardTests(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.client.force_authenticate(self.admin)

    def _paid_purchase(self, *, kyc_status=CustomerKyc.Status.VERIFIED):
        kyc = make_kyc(self.customer, status=kyc_status)
        purchase = make_purchase(self.customer, self.policy, kyc=kyc)
        purchase.mark_paid()
        return purchase

    def test_list_and_filter_by_status(self):
        self._paid_purchase()
        response = self.client.get(
            reverse("admin-purchase-list"), {"status": PolicyPurchase.Status.PAID}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        statuses = {r["status"] for r in response.data["results"]}
        self.assertEqual(statuses, {PolicyPurchase.Status.PAID})

    def test_forward_happy_path_notifies_customer_and_provider(self):
        purchase = self._paid_purchase()
        response = self.client.post(
            reverse("admin-purchase-forward", args=[purchase.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, PolicyPurchase.Status.FORWARDED)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.customer, type=Notification.Type.PURCHASE_FORWARDED
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.provider.user,
                type=Notification.Type.PROVIDER_NEW_ISSUANCE,
            ).exists()
        )

    def test_forward_requires_paid(self):
        kyc = make_kyc(self.customer, status=CustomerKyc.Status.VERIFIED)
        purchase = make_purchase(self.customer, self.policy, kyc=kyc)  # PENDING_PAYMENT
        response = self.client.post(
            reverse("admin-purchase-forward", args=[purchase.id])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "purchase_not_forwardable")

    def test_forward_requires_verified_kyc(self):
        purchase = self._paid_purchase(kyc_status=CustomerKyc.Status.PENDING)
        response = self.client.post(
            reverse("admin-purchase-forward", args=[purchase.id])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "purchase_not_forwardable")
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, PolicyPurchase.Status.PAID)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminUserAndPolicyTests(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.client.force_authenticate(self.admin)

    def test_user_list_filter_by_role(self):
        response = self.client.get(
            reverse("admin-user-list"), {"role": User.Role.PROVIDER}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roles = {r["role"] for r in response.data["results"]}
        self.assertEqual(roles, {User.Role.PROVIDER})

    def test_user_detail_has_activity_counts(self):
        make_purchase(self.customer, self.policy)
        response = self.client.get(
            reverse("admin-user-detail", args=[self.customer.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["purchase_count"], 1)
        self.assertEqual(response.data["claim_count"], 0)

    def test_policy_list_filter_by_provider(self):
        response = self.client.get(
            reverse("admin-policy-list"), {"provider": self.provider.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], self.policy.name)


@no_throttle
@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class AdminAnalyticsTests(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.provider = make_provider(approved=True)
        self.policy = make_policy(self.provider, self.category)
        self.customer = make_customer()
        self.url = reverse("admin-analytics")

    def test_customer_is_forbidden(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_anonymous_is_unauthorized(self):
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_totals_breakdowns_and_monthly_series(self):
        paid = make_purchase(
            self.customer, self.policy, status=PolicyPurchase.Status.PAID
        )
        make_purchase(self.customer, self.policy)  # PENDING_PAYMENT
        Payment.objects.create(
            policy_purchase=paid,
            amount=Decimal("12000.00"),
            gateway=Payment.Gateway.ESEWA,
            status=Payment.Status.SUCCESS,
            paid_at=timezone.now(),
        )
        self.client.force_authenticate(self.admin)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        stats = {s["key"]: s for s in data["stats"]}
        self.assertEqual(stats["users"]["value"], 3)  # admin, provider, customer
        self.assertEqual(stats["providers"]["value"], 1)
        self.assertEqual(stats["policies"]["value"], 1)
        self.assertEqual(stats["purchases"]["value"], 2)
        self.assertEqual(stats["premium"]["value"], "12000.00")
        self.assertEqual(stats["premium"]["format"], "currency")

        by_role = {r["key"]: r["value"] for r in data["users_by_role"]}
        self.assertEqual(by_role[User.Role.CUSTOMER], 1)
        self.assertEqual(by_role[User.Role.PROVIDER], 1)
        self.assertEqual(by_role[User.Role.ADMIN], 1)

        by_status = {r["key"]: r["value"] for r in data["purchases_by_status"]}
        self.assertEqual(by_status[PolicyPurchase.Status.PAID], 1)
        self.assertEqual(by_status[PolicyPurchase.Status.PENDING_PAYMENT], 1)
        # Every status is present, even those with no rows.
        self.assertEqual(
            len(data["purchases_by_status"]), len(PolicyPurchase.Status.choices)
        )

        self.assertEqual(data["providers"], {"total": 1, "approved": 1, "pending": 0})
        self.assertEqual(data["queues"]["paid_purchases"], 1)

        self.assertEqual(len(data["monthly"]), 6)
        current = data["monthly"][-1]  # oldest-first, so the last is this month
        self.assertEqual(current["purchases"], 2)
        self.assertEqual(current["premium"], "12000.00")
