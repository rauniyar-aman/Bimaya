"""Tests for the provider analytics endpoint (``/api/v1/provider/analytics/``).

The endpoint is gated by ``IsProvider``/``IsVerified`` and every number is scoped
to the signed-in provider's own policies, so the key test drives two providers
and asserts one never sees the other's book.
"""

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.payments.models import Payment
from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider
from apps.purchases.models import PolicyPurchase

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_provider(email, company, *, approved=True):
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.PROVIDER, is_verified=True
    )
    return Provider.objects.create(user=user, company_name=company, is_approved=approved)


def make_policy(provider, category, name):
    return Policy.objects.create(
        provider=provider,
        category=category,
        name=name,
        premium=Decimal("10000.00"),
        coverage_amount=Decimal("1000000.00"),
        term_months=12,
        status=Policy.Status.APPROVED,
    )


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
class ProviderAnalyticsTests(APITestCase):
    def setUp(self):
        self.url = reverse("provider-analytics")
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.customer = User.objects.create_user(
            email="customer@bimaya.test",
            password="Himalaya#2026",
            role=User.Role.CUSTOMER,
            is_verified=True,
        )
        self.provider = make_provider("prov-a@bimaya.test", "Everest Life")
        self.other = make_provider("prov-b@bimaya.test", "Annapurna General")

    def test_customer_is_forbidden(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_anonymous_is_unauthorized(self):
        self.assertEqual(
            self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_missing_profile_returns_code(self):
        user = User.objects.create_user(
            email="lonely@bimaya.test",
            password="Himalaya#2026",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.client.force_authenticate(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["code"], "provider_profile_missing")

    def test_scoped_to_own_policies(self):
        mine = make_policy(self.provider, self.category, "Motor Shield")
        theirs = make_policy(self.other, self.category, "Rival Cover")

        my_paid = make_purchase(self.customer, mine, status=PolicyPurchase.Status.PAID)
        make_purchase(self.customer, theirs, status=PolicyPurchase.Status.PAID)
        Payment.objects.create(
            policy_purchase=my_paid,
            amount=Decimal("8000.00"),
            gateway=Payment.Gateway.KHALTI,
            status=Payment.Status.SUCCESS,
            paid_at=timezone.now(),
        )

        self.client.force_authenticate(self.provider.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        stats = {s["key"]: s for s in data["stats"]}
        self.assertEqual(stats["policies"]["value"], 1)
        self.assertEqual(stats["purchases"]["value"], 1)  # the rival's is excluded
        self.assertEqual(stats["premium"]["value"], "8000.00")

        by_status = {r["key"]: r["value"] for r in data["purchases_by_status"]}
        self.assertEqual(by_status[PolicyPurchase.Status.PAID], 1)

        # Provider scope carries no platform-wide breakdowns.
        self.assertNotIn("users_by_role", data)
        self.assertNotIn("queues", data)

        self.assertEqual(len(data["monthly"]), 6)
        current = data["monthly"][-1]
        self.assertEqual(current["purchases"], 1)
        self.assertEqual(current["premium"], "8000.00")
