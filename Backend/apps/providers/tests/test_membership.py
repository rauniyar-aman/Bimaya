"""Access-control tests for provider team members (owner / staff / viewer).

A provider organisation can have several accounts: the owner is
``Provider.user``; staff and viewers are :class:`ProviderMembership` rows.
Writes are gated by role in
:class:`~apps.providers.access.IsProviderTeamMember` — owners and staff may
change things, viewers are read-only, and only the owner may edit the company
profile. Every member is scoped to their own organisation's objects.
"""

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider, ProviderMembership, ProviderRole

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)


def make_provider_user(email):
    return User.objects.create_user(
        email=email,
        password="Himalaya#2026",
        role=User.Role.PROVIDER,
        is_verified=True,
    )


@no_throttle
class ProviderTeamAccessTests(APITestCase):
    def setUp(self):
        self.owner = make_provider_user("owner@bimaya.test")
        self.provider = Provider.objects.create(
            user=self.owner, company_name="Everest Life", is_approved=True
        )
        self.staff = make_provider_user("staff@bimaya.test")
        ProviderMembership.objects.create(
            provider=self.provider, user=self.staff, role=ProviderRole.STAFF
        )
        self.viewer = make_provider_user("viewer@bimaya.test")
        ProviderMembership.objects.create(
            provider=self.provider, user=self.viewer, role=ProviderRole.VIEWER
        )
        self.category = InsuranceCategory.objects.create(name="Vehicle")

    def _policy(self, **kwargs):
        defaults = {
            "name": "Motor Shield",
            "premium": Decimal("10000.00"),
            "coverage_amount": Decimal("1000000.00"),
            "term_months": 12,
            "status": Policy.Status.APPROVED,
        }
        defaults.update(kwargs)
        return Policy.objects.create(
            provider=self.provider, category=self.category, **defaults
        )

    def _create_payload(self):
        return {
            "name": "New Plan",
            "category": self.category.id,
            "premium": "5000.00",
            "coverage_amount": "500000.00",
            "term_months": 12,
        }

    # --- reads: every member of the organisation may read ------------------

    def test_all_members_can_list_policies(self):
        self._policy()
        for member in (self.owner, self.staff, self.viewer):
            self.client.force_authenticate(member)
            response = self.client.get(reverse("provider-policy-list"))
            self.assertEqual(response.status_code, status.HTTP_200_OK, member.email)
            self.assertEqual(response.data["count"], 1, member.email)

    # --- writes: owner/staff may write, viewers may not --------------------

    def test_staff_can_create_policy(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            reverse("provider-policy-list"), self._create_payload()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Policy.objects.filter(provider=self.provider, name="New Plan").exists()
        )

    def test_viewer_cannot_create_policy(self):
        self.client.force_authenticate(self.viewer)
        response = self.client.post(
            reverse("provider-policy-list"), self._create_payload()
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Policy.objects.filter(name="New Plan").exists())

    def test_staff_can_submit_policy_but_viewer_cannot(self):
        policy = self._policy(status=Policy.Status.DRAFT)
        url = reverse("provider-policy-submit", args=[policy.id])

        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.staff)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        policy.refresh_from_db()
        self.assertEqual(policy.status, Policy.Status.PENDING)

    def test_staff_can_deactivate_policy_but_viewer_cannot(self):
        policy = self._policy(status=Policy.Status.APPROVED)
        url = reverse("provider-policy-deactivate", args=[policy.id])

        self.client.force_authenticate(self.viewer)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.staff)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        policy.refresh_from_db()
        self.assertEqual(policy.status, Policy.Status.INACTIVE)

    def test_viewer_cannot_issue_or_decide_claims(self):
        # The role gate rejects a viewer before any object lookup, so a bogus id
        # is enough to prove the write is blocked.
        self.client.force_authenticate(self.viewer)
        issue = self.client.post(
            reverse("provider-issuance-issue", args=[999]), {"policy_number": "X"}
        )
        self.assertEqual(issue.status_code, status.HTTP_403_FORBIDDEN)
        approve = self.client.post(
            reverse("provider-claim-approve", args=[999]),
            {"approved_amount": "1.00"},
            format="json",
        )
        self.assertEqual(approve.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_passes_the_role_gate_on_issue_and_claims(self):
        # Staff clear the role gate; the bogus id then 404s — proving the block a
        # viewer hits above is the role gate, not the endpoint itself.
        self.client.force_authenticate(self.staff)
        issue = self.client.post(
            reverse("provider-issuance-issue", args=[999]), {"policy_number": "X"}
        )
        self.assertEqual(issue.status_code, status.HTTP_404_NOT_FOUND)
        approve = self.client.post(
            reverse("provider-claim-approve", args=[999]),
            {"approved_amount": "1.00"},
            format="json",
        )
        self.assertEqual(approve.status_code, status.HTTP_404_NOT_FOUND)

    # --- profile: any member reads, only the owner edits -------------------

    def test_my_role_reflects_each_member(self):
        expected = {
            self.owner: ProviderRole.OWNER.value,
            self.staff: ProviderRole.STAFF.value,
            self.viewer: ProviderRole.VIEWER.value,
        }
        for member, role in expected.items():
            self.client.force_authenticate(member)
            response = self.client.get(reverse("provider-profile"))
            self.assertEqual(response.status_code, status.HTTP_200_OK, member.email)
            self.assertEqual(response.data["my_role"], role, member.email)

    def test_only_owner_can_edit_profile(self):
        url = reverse("provider-profile")
        for member in (self.staff, self.viewer):
            self.client.force_authenticate(member)
            response = self.client.patch(url, {"support_phone": "+977-1-4000000"})
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, member.email
            )

        self.client.force_authenticate(self.owner)
        response = self.client.patch(url, {"support_phone": "+977-1-4000000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.support_phone, "+977-1-4000000")

    # --- scoping: a member sees only their own organisation ----------------

    def test_member_cannot_see_another_organisations_policies(self):
        self._policy(name="Mine")
        other_owner = make_provider_user("other-owner@bimaya.test")
        other = Provider.objects.create(
            user=other_owner, company_name="Other Co", is_approved=True
        )
        other_policy = Policy.objects.create(
            provider=other,
            category=self.category,
            name="Theirs",
            premium=Decimal("1.00"),
            coverage_amount=Decimal("1.00"),
            term_months=12,
            status=Policy.Status.APPROVED,
        )

        self.client.force_authenticate(self.staff)
        listing = self.client.get(reverse("provider-policy-list"))
        names = {row["name"] for row in listing.data["results"]}
        self.assertEqual(names, {"Mine"})

        detail = self.client.get(
            reverse("provider-policy-detail", args=[other_policy.id])
        )
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
