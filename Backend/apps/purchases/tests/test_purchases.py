"""Tests for the customer purchase endpoints (``/api/v1/purchases/``)."""

from datetime import date
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider

from ..models import PolicyPurchase

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_customer(email="cust@bimaya.test"):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.CUSTOMER, is_verified=True
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
        self.client.force_authenticate(self.customer)
        response = self.client.post(self.list_url, self._payload(policy), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], PolicyPurchase.Status.PENDING_PAYMENT)
        self.assertIsNone(response.data["policy_number"])
        purchase = PolicyPurchase.objects.get(id=response.data["id"])
        self.assertEqual(purchase.customer, self.customer)

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
        self.purchase.activate()
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
class PolicyPurchaseActivationTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider()
        self.policy = make_policy(self.provider, self.category, term_months=12)
        self.customer = make_customer()
        self.purchase = PolicyPurchase.objects.create(
            customer=self.customer,
            policy=self.policy,
            nominee_name="Sita Sharma",
            nominee_relationship="Spouse",
            nominee_contact="9800000000",
        )

    def test_activate_generates_policy_number_and_term_dates(self):
        self.purchase.activate()
        self.assertEqual(self.purchase.status, PolicyPurchase.Status.ACTIVE)
        self.assertTrue(self.purchase.policy_number.startswith(f"BIM-{date.today().year}-"))
        self.assertEqual(len(self.purchase.policy_number), len(f"BIM-{date.today().year}-") + 6)
        self.assertEqual(self.purchase.start_date, date.today())

    def test_activate_is_idempotent_on_policy_number(self):
        self.purchase.activate()
        first_number = self.purchase.policy_number
        self.purchase.activate()
        self.assertEqual(self.purchase.policy_number, first_number)
