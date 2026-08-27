"""Tests for the provider's own-policy management endpoints."""

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_provider(email, company, *, approved=True):
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.PROVIDER, is_verified=True
    )
    provider = Provider.objects.create(
        user=user, company_name=company, is_approved=approved
    )
    return user, provider


@no_throttle
class ProviderPolicyCrudTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.user, self.provider = make_provider("prov@bimaya.test", "Everest Life")
        self.list_url = reverse("provider-policy-list")

    def _valid_payload(self, **overrides):
        payload = {
            "name": "Term Shield",
            "category": self.category.id,
            "premium": "12000.00",
            "premium_frequency": Policy.Frequency.YEARLY,
            "coverage_amount": "5000000.00",
            "term_months": 240,
            "features": ["Big cover", "Low premium"],
            "add_ons": ["Accident rider"],
        }
        payload.update(overrides)
        return payload

    def test_create_policy_starts_as_draft(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.list_url, self._valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Policy.Status.DRAFT)
        policy = Policy.objects.get(id=response.data["id"])
        self.assertEqual(policy.provider, self.provider)

    def test_create_ignores_client_supplied_status(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            self.list_url,
            self._valid_payload(status=Policy.Status.APPROVED),
            format="json",
        )
        self.assertEqual(response.data["status"], Policy.Status.DRAFT)

    def test_draft_policy_is_not_public(self):
        self.client.force_authenticate(self.user)
        self.client.post(self.list_url, self._valid_payload(), format="json")
        # Public list should not show the draft.
        public = self.client.get(reverse("policy-list"))
        self.assertEqual(public.data["count"], 0)

    def test_list_shows_only_own_policies(self):
        _, other = make_provider("other@bimaya.test", "Other Co")
        Policy.objects.create(
            provider=other, category=self.category, name="Other Plan",
            premium=Decimal("1"), coverage_amount=Decimal("1"), term_months=12,
        )
        Policy.objects.create(
            provider=self.provider, category=self.category, name="Mine",
            premium=Decimal("1"), coverage_amount=Decimal("1"), term_months=12,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.list_url)
        names = {row["name"] for row in response.data["results"]}
        self.assertEqual(names, {"Mine"})

    def test_submit_moves_draft_to_pending(self):
        policy = Policy.objects.create(
            provider=self.provider, category=self.category, name="Draft",
            premium=Decimal("1"), coverage_amount=Decimal("1"), term_months=12,
            status=Policy.Status.DRAFT,
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("provider-policy-submit", args=[policy.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        policy.refresh_from_db()
        self.assertEqual(policy.status, Policy.Status.PENDING)

    def test_submit_rejects_approved_policy(self):
        policy = Policy.objects.create(
            provider=self.provider, category=self.category, name="Live",
            premium=Decimal("1"), coverage_amount=Decimal("1"), term_months=12,
            status=Policy.Status.APPROVED,
        )
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("provider-policy-submit", args=[policy.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "policy_not_submittable")

    def test_editing_approved_policy_reverts_to_pending(self):
        policy = Policy.objects.create(
            provider=self.provider, category=self.category, name="Live",
            premium=Decimal("1"), coverage_amount=Decimal("1"), term_months=12,
            status=Policy.Status.APPROVED,
        )
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            reverse("provider-policy-detail", args=[policy.id]),
            {"summary": "Now with more cover"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        policy.refresh_from_db()
        self.assertEqual(policy.status, Policy.Status.PENDING)

    def test_cannot_access_another_providers_policy(self):
        _, other = make_provider("other@bimaya.test", "Other Co")
        policy = Policy.objects.create(
            provider=other, category=self.category, name="Other Plan",
            premium=Decimal("1"), coverage_amount=Decimal("1"), term_months=12,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("provider-policy-detail", args=[policy.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_without_profile_returns_clear_error(self):
        user = User.objects.create_user(
            email="noprofile@bimaya.test", password="Himalaya#2026",
            role=User.Role.PROVIDER, is_verified=True,
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.list_url, self._valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "provider_profile_required")

    def test_customer_cannot_create_policy(self):
        customer = User.objects.create_user(
            email="cust@bimaya.test", password="Himalaya#2026",
            role=User.Role.CUSTOMER, is_verified=True,
        )
        self.client.force_authenticate(customer)
        response = self.client.post(self.list_url, self._valid_payload(), format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
