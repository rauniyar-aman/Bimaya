"""Tests for the public catalog endpoints (categories, policies, compare)."""

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
        user=user,
        company_name=company,
        is_approved=approved,
        kyc_status=Provider.KycStatus.VERIFIED if approved else Provider.KycStatus.PENDING,
    )
    return provider


def make_policy(provider, category, name, **kwargs):
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


@no_throttle
class CategoryEndpointTests(APITestCase):
    def setUp(self):
        self.life = InsuranceCategory.objects.create(name="Life", order=1)
        self.health = InsuranceCategory.objects.create(name="Health", order=2)
        InsuranceCategory.objects.create(name="Archived", is_active=False)
        self.provider = make_provider("p1@bimaya.test", "Everest Life")
        make_policy(self.provider, self.life, "Term Shield")

    def test_list_returns_only_active_categories(self):
        response = self.client.get(reverse("category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = {row["slug"] for row in response.data}
        self.assertEqual(slugs, {"life", "health"})

    def test_list_includes_public_policy_count(self):
        response = self.client.get(reverse("category-list"))
        by_slug = {row["slug"]: row for row in response.data}
        self.assertEqual(by_slug["life"]["policy_count"], 1)
        self.assertEqual(by_slug["health"]["policy_count"], 0)

    def test_detail_by_slug(self):
        response = self.client.get(reverse("category-detail", args=["life"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Life")

    def test_no_auth_required(self):
        # No credentials attached at all.
        response = self.client.get(reverse("category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@no_throttle
class PolicyListVisibilityTests(APITestCase):
    def setUp(self):
        self.life = InsuranceCategory.objects.create(name="Life", order=1)
        self.health = InsuranceCategory.objects.create(name="Health", order=2)
        self.approved_provider = make_provider("ok@bimaya.test", "Everest Life")
        self.pending_provider = make_provider(
            "pending@bimaya.test", "New Insurer", approved=False
        )

        self.public = make_policy(
            self.approved_provider, self.life, "Public Term",
            premium=Decimal("12000.00"), coverage_amount=Decimal("5000000.00"),
            is_featured=True,
        )
        # Not public: draft, even though the provider is approved.
        make_policy(
            self.approved_provider, self.life, "Draft Term", status=Policy.Status.DRAFT
        )
        # Not public: approved policy but the provider is not approved.
        make_policy(self.pending_provider, self.health, "Unapproved Provider Plan")

    def test_list_excludes_non_public_policies(self):
        response = self.client.get(reverse("policy-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Public Term")

    def test_filter_by_category_slug(self):
        make_policy(self.approved_provider, self.health, "Health Plan")
        response = self.client.get(reverse("policy-list"), {"category": "health"})
        names = {row["name"] for row in response.data["results"]}
        self.assertEqual(names, {"Health Plan"})

    def test_filter_by_premium_range(self):
        make_policy(
            self.approved_provider, self.life, "Cheap Plan", premium=Decimal("1000.00")
        )
        response = self.client.get(reverse("policy-list"), {"premium_max": "5000"})
        names = {row["name"] for row in response.data["results"]}
        self.assertEqual(names, {"Cheap Plan"})

    def test_search_by_name(self):
        response = self.client.get(reverse("policy-list"), {"search": "Public"})
        self.assertEqual(response.data["count"], 1)

    def test_ordering_by_premium(self):
        make_policy(
            self.approved_provider, self.life, "Cheaper", premium=Decimal("500.00")
        )
        response = self.client.get(reverse("policy-list"), {"ordering": "premium"})
        first = response.data["results"][0]
        self.assertEqual(first["name"], "Cheaper")

    def test_detail_of_public_policy(self):
        response = self.client.get(reverse("policy-detail", args=[self.public.slug]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["provider"]["company_name"], "Everest Life")

    def test_detail_of_non_public_policy_is_404(self):
        draft = Policy.objects.get(name="Draft Term")
        response = self.client.get(reverse("policy-detail", args=[draft.slug]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@no_throttle
class PolicyCompareTests(APITestCase):
    def setUp(self):
        self.category = InsuranceCategory.objects.create(name="Life")
        self.provider = make_provider("ok@bimaya.test", "Everest Life")
        self.policies = [
            make_policy(self.provider, self.category, f"Plan {i}") for i in range(5)
        ]
        self.draft = make_policy(
            self.provider, self.category, "Draft Plan", status=Policy.Status.DRAFT
        )

    def test_compare_returns_requested_public_policies(self):
        ids = f"{self.policies[0].id},{self.policies[1].id}"
        response = self.client.get(reverse("policy-compare"), {"ids": ids})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_compare_is_capped_at_four(self):
        ids = ",".join(str(p.id) for p in self.policies)
        response = self.client.get(reverse("policy-compare"), {"ids": ids})
        self.assertEqual(len(response.data), 4)

    def test_compare_excludes_non_public(self):
        ids = f"{self.policies[0].id},{self.draft.id}"
        response = self.client.get(reverse("policy-compare"), {"ids": ids})
        self.assertEqual(len(response.data), 1)

    def test_compare_preserves_requested_order(self):
        ids = f"{self.policies[2].id},{self.policies[0].id}"
        response = self.client.get(reverse("policy-compare"), {"ids": ids})
        returned = [row["id"] for row in response.data]
        self.assertEqual(returned, [self.policies[2].id, self.policies[0].id])

    def test_compare_without_ids_is_empty(self):
        response = self.client.get(reverse("policy-compare"))
        self.assertEqual(response.data, [])
