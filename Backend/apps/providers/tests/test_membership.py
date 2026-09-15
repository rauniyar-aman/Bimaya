"""Access-control tests for provider team members under the granular RBAC.

A provider organisation can have several accounts: the owner is
``Provider.user`` (the implicit ``OWNER`` role, always full control); added
members are :class:`ProviderMembership` rows, each holding one assignable role.
Access is gated per-permission by
:class:`~apps.providers.access.HasProviderPermission` against the code matrix in
:mod:`apps.providers.rbac`. The important behaviour change from the old
owner/staff/viewer scheme is that **reads are role-scoped** — a Claims Officer
cannot list policies, a Finance Viewer is read-only — and every member is still
scoped to their own organisation's objects.
"""

from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.policies.models import InsuranceCategory, Policy
from apps.providers.models import Provider, ProviderMembership, ProviderRole
from apps.providers.rbac import OWNER

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
        self.company_admin = self._member("admin@bimaya.test", ProviderRole.COMPANY_ADMIN)
        self.policy_manager = self._member("policy@bimaya.test", ProviderRole.POLICY_MANAGER)
        self.claims_officer = self._member("claims@bimaya.test", ProviderRole.CLAIMS_OFFICER)
        self.finance_viewer = self._member("finance@bimaya.test", ProviderRole.FINANCE_VIEWER)
        self.category = InsuranceCategory.objects.create(name="Vehicle")

    def _member(self, email, role):
        user = make_provider_user(email)
        ProviderMembership.objects.create(provider=self.provider, user=user, role=role)
        return user

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

    # --- reads: now scoped to roles holding policy.view --------------------

    def test_policy_view_holders_can_list_policies(self):
        self._policy()
        for member in (
            self.owner,
            self.company_admin,
            self.policy_manager,
            self.finance_viewer,
        ):
            self.client.force_authenticate(member)
            response = self.client.get(reverse("provider-policy-list"))
            self.assertEqual(response.status_code, status.HTTP_200_OK, member.email)
            self.assertEqual(response.data["count"], 1, member.email)

    def test_claims_officer_cannot_list_policies(self):
        # A Claims Officer holds no policy.view — the read is now role-scoped.
        self._policy()
        self.client.force_authenticate(self.claims_officer)
        response = self.client.get(reverse("provider-policy-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- writes: policy roles may write, finance is read-only --------------

    def test_policy_manager_can_create_policy(self):
        self.client.force_authenticate(self.policy_manager)
        response = self.client.post(
            reverse("provider-policy-list"), self._create_payload()
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Policy.objects.filter(provider=self.provider, name="New Plan").exists()
        )

    def test_finance_viewer_cannot_create_policy(self):
        self.client.force_authenticate(self.finance_viewer)
        response = self.client.post(
            reverse("provider-policy-list"), self._create_payload()
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Policy.objects.filter(name="New Plan").exists())

    def test_policy_manager_can_submit_but_finance_cannot(self):
        policy = self._policy(status=Policy.Status.DRAFT)
        url = reverse("provider-policy-submit", args=[policy.id])

        self.client.force_authenticate(self.finance_viewer)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.policy_manager)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        policy.refresh_from_db()
        self.assertEqual(policy.status, Policy.Status.PENDING)

    def test_policy_manager_can_deactivate_but_finance_cannot(self):
        policy = self._policy(status=Policy.Status.APPROVED)
        url = reverse("provider-policy-deactivate", args=[policy.id])

        self.client.force_authenticate(self.finance_viewer)
        self.assertEqual(self.client.post(url).status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.policy_manager)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        policy.refresh_from_db()
        self.assertEqual(policy.status, Policy.Status.INACTIVE)

    # --- feature isolation: policy vs claims roles do not overlap ----------

    def test_claims_officer_passes_claim_gate_but_cannot_issue(self):
        # Claims Officer clears the claim.decide gate (bogus id then 404s) but
        # holds no issuance.issue, so issuance is refused at the gate.
        self.client.force_authenticate(self.claims_officer)
        issue = self.client.post(
            reverse("provider-issuance-issue", args=[999]), {"policy_number": "X"}
        )
        self.assertEqual(issue.status_code, status.HTTP_403_FORBIDDEN)
        approve = self.client.post(
            reverse("provider-claim-approve", args=[999]),
            {"approved_amount": "1.00"},
            format="json",
        )
        self.assertEqual(approve.status_code, status.HTTP_404_NOT_FOUND)

    def test_policy_manager_passes_issue_gate_but_cannot_decide_claims(self):
        # The mirror image: Policy Manager clears issuance.issue (bogus id 404s)
        # but holds no claim.decide, so approving a claim is refused at the gate.
        self.client.force_authenticate(self.policy_manager)
        issue = self.client.post(
            reverse("provider-issuance-issue", args=[999]), {"policy_number": "X"}
        )
        self.assertEqual(issue.status_code, status.HTTP_404_NOT_FOUND)
        approve = self.client.post(
            reverse("provider-claim-approve", args=[999]),
            {"approved_amount": "1.00"},
            format="json",
        )
        self.assertEqual(approve.status_code, status.HTTP_403_FORBIDDEN)

    # --- profile: any member reads, only company.edit holders edit ---------

    def test_my_role_reflects_each_member(self):
        expected = {
            self.owner: OWNER,
            self.company_admin: ProviderRole.COMPANY_ADMIN.value,
            self.policy_manager: ProviderRole.POLICY_MANAGER.value,
            self.claims_officer: ProviderRole.CLAIMS_OFFICER.value,
            self.finance_viewer: ProviderRole.FINANCE_VIEWER.value,
        }
        for member, role in expected.items():
            self.client.force_authenticate(member)
            response = self.client.get(reverse("provider-profile"))
            self.assertEqual(response.status_code, status.HTTP_200_OK, member.email)
            self.assertEqual(response.data["my_role"], role, member.email)

    def test_owner_and_company_admin_can_edit_profile_others_cannot(self):
        url = reverse("provider-profile")
        for member in (self.policy_manager, self.claims_officer, self.finance_viewer):
            self.client.force_authenticate(member)
            response = self.client.patch(url, {"support_phone": "+977-1-4000000"})
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN, member.email
            )

        for member in (self.company_admin, self.owner):
            self.client.force_authenticate(member)
            response = self.client.patch(url, {"support_phone": "+977-1-4000000"})
            self.assertEqual(response.status_code, status.HTTP_200_OK, member.email)

    def test_company_admin_editing_profile_does_not_steal_ownership(self):
        # Regression guard: company.edit lets a Company Admin update the profile,
        # but the owning account must stay the original owner.
        self.client.force_authenticate(self.company_admin)
        response = self.client.patch(
            reverse("provider-profile"), {"support_phone": "+977-1-5550000"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.provider.refresh_from_db()
        self.assertEqual(self.provider.user_id, self.owner.id)
        self.assertEqual(self.provider.support_phone, "+977-1-5550000")

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

        self.client.force_authenticate(self.company_admin)
        listing = self.client.get(reverse("provider-policy-list"))
        names = {row["name"] for row in listing.data["results"]}
        self.assertEqual(names, {"Mine"})

        detail = self.client.get(
            reverse("provider-policy-detail", args=[other_policy.id])
        )
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
