"""RBAC tests for provider organisations.

Complements ``test_membership.py`` (policy access + org scoping) with:

* the *code* catalog — roles, the full-access roles, the least-privilege matrix;
* the permission resolver (:mod:`apps.providers.access`);
* the per-endpoint **access matrix** across the provider APIs, driven directly
  from the role→permission table so the gate and the policy cannot drift apart;
* self-service team management (create / re-role / disable-self guard / scoping /
  non-admin refusal);
* the roles catalog endpoint;
* the profile ``public_id`` / ``my_permissions`` shape;
* provider KYC documents (upload / list / delete-pending / download scoping) and
  admin-side KYC review.
"""

import shutil
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.documents.models import ProviderKyc
from apps.policies.models import InsuranceCategory, Policy
from apps.providers.access import provider_permissions, role_for
from apps.providers.models import Provider, ProviderMembership, ProviderRole
from apps.providers.rbac import (
    ALL_PROVIDER_PERMS,
    OWNER,
    PROVIDER_ROLE_PERMISSIONS,
    ProviderPerm,
    permissions_for,
)
from apps.staff.models import StaffRoleAssignment
from apps.staff.rbac import StaffRole

User = get_user_model()

no_throttle = mock.patch(
    "rest_framework.throttling.SimpleRateThrottle.allow_request",
    new=lambda self, request, view: True,
)

_MEDIA_ROOT = tempfile.mkdtemp(prefix="bimaya-provider-rbac-tests-")

# Every assignable role (owner is implicit and never a membership row).
ASSIGNABLE_ROLES = [role.value for role in ProviderRole]


def tearDownModule():
    shutil.rmtree(_MEDIA_ROOT, ignore_errors=True)


def make_provider_user(email):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.PROVIDER, is_verified=True
    )


def make_admin(email="admin@bimaya.test"):
    """A platform administrator holding every staff permission (System Owner)."""
    user = User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.ADMIN, is_verified=True
    )
    StaffRoleAssignment.objects.create(user=user, role=StaffRole.SYSTEM_OWNER.value)
    return user


class ProviderRbacCatalogTests(SimpleTestCase):
    """The code catalog: the assignable roles and the least-privilege matrix."""

    def test_five_assignable_roles_owner_is_a_sentinel(self):
        self.assertEqual(
            set(ASSIGNABLE_ROLES),
            {
                "COMPANY_ADMIN",
                "POLICY_MANAGER",
                "CLAIMS_OFFICER",
                "SALES_MANAGER",
                "FINANCE_VIEWER",
            },
        )
        self.assertNotIn(OWNER, ASSIGNABLE_ROLES)

    def test_owner_and_company_admin_hold_everything(self):
        self.assertEqual(permissions_for([OWNER]), set(ALL_PROVIDER_PERMS))
        self.assertEqual(
            PROVIDER_ROLE_PERMISSIONS[ProviderRole.COMPANY_ADMIN.value],
            ALL_PROVIDER_PERMS,
        )

    def test_matrix_matches_least_privilege_spec(self):
        self.assertEqual(
            PROVIDER_ROLE_PERMISSIONS[ProviderRole.POLICY_MANAGER.value],
            {
                ProviderPerm.POLICY_VIEW,
                ProviderPerm.POLICY_CREATE,
                ProviderPerm.POLICY_EDIT,
                ProviderPerm.POLICY_DELETE,
                ProviderPerm.POLICY_SUBMIT,
                ProviderPerm.POLICY_DEACTIVATE,
                ProviderPerm.ISSUANCE_VIEW,
                ProviderPerm.ISSUANCE_ISSUE,
                ProviderPerm.ANALYTICS_VIEW,
            },
        )
        self.assertEqual(
            PROVIDER_ROLE_PERMISSIONS[ProviderRole.CLAIMS_OFFICER.value],
            {
                ProviderPerm.CLAIM_VIEW,
                ProviderPerm.CLAIM_REVIEW,
                ProviderPerm.CLAIM_DECIDE,
                ProviderPerm.CLAIM_PAYOUT,
                ProviderPerm.CLAIM_MESSAGE,
            },
        )
        self.assertEqual(
            PROVIDER_ROLE_PERMISSIONS[ProviderRole.SALES_MANAGER.value],
            {
                ProviderPerm.POLICY_VIEW,
                ProviderPerm.PURCHASE_VIEW,
                ProviderPerm.ANALYTICS_VIEW,
            },
        )
        self.assertEqual(
            PROVIDER_ROLE_PERMISSIONS[ProviderRole.FINANCE_VIEWER.value],
            {
                ProviderPerm.POLICY_VIEW,
                ProviderPerm.PURCHASE_VIEW,
                ProviderPerm.PAYOUT_VIEW,
                ProviderPerm.ANALYTICS_VIEW,
            },
        )

    def test_no_role_exceeds_the_full_catalog(self):
        for role, perms in PROVIDER_ROLE_PERMISSIONS.items():
            self.assertTrue(set(perms) <= set(ALL_PROVIDER_PERMS), role)

    def test_unknown_and_empty_roles_grant_nothing(self):
        self.assertEqual(permissions_for(["NOPE"]), set())
        self.assertEqual(permissions_for([]), set())


@no_throttle
class ProviderRbacDbBase(APITestCase):
    """A provider with one member of every assignable role, plus the owner."""

    def setUp(self):
        self.owner = make_provider_user("owner@bimaya.test")
        self.provider = Provider.objects.create(
            user=self.owner, company_name="Everest Life", is_approved=True
        )
        self.category = InsuranceCategory.objects.create(name="Vehicle")
        self.members = {
            role: self._member(f"{role.lower()}@bimaya.test", role)
            for role in ASSIGNABLE_ROLES
        }

    def _member(self, email, role):
        user = make_provider_user(email)
        ProviderMembership.objects.create(provider=self.provider, user=user, role=role)
        return user


class ProviderPermissionResolverTests(ProviderRbacDbBase):
    def test_role_for_owner_returns_sentinel(self):
        self.assertEqual(role_for(self.owner, self.provider), OWNER)

    def test_role_for_member_returns_membership_role(self):
        member = self.members[ProviderRole.CLAIMS_OFFICER.value]
        self.assertEqual(
            role_for(member, self.provider), ProviderRole.CLAIMS_OFFICER.value
        )

    def test_role_for_outsider_is_none(self):
        outsider = make_provider_user("outsider@bimaya.test")
        self.assertIsNone(role_for(outsider, self.provider))

    def test_provider_permissions_per_role(self):
        self.assertEqual(
            provider_permissions(self.owner, self.provider), set(ALL_PROVIDER_PERMS)
        )
        for role, user in self.members.items():
            self.assertEqual(
                provider_permissions(user, self.provider),
                set(PROVIDER_ROLE_PERMISSIONS[role]),
                role,
            )


class ProviderAccessMatrixTests(ProviderRbacDbBase):
    """Every provider endpoint's gate, checked against the role matrix."""

    def _policy_payload(self):
        return {
            "name": "New Plan",
            "category": self.category.id,
            "premium": "5000.00",
            "coverage_amount": "500000.00",
            "term_months": 12,
        }

    def _assert_get_gated(self, urlname, perm):
        """A read endpoint returns 200 for perm holders, else 403 (owner=200)."""
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.get(reverse(urlname)).status_code,
            status.HTTP_200_OK,
            f"owner @ {urlname}",
        )
        for role, user in self.members.items():
            self.client.force_authenticate(user)
            code = self.client.get(reverse(urlname)).status_code
            expected = (
                status.HTTP_200_OK
                if perm in PROVIDER_ROLE_PERMISSIONS[role]
                else status.HTTP_403_FORBIDDEN
            )
            self.assertEqual(code, expected, f"{role} @ {urlname}")

    def test_policy_list_gated_by_policy_view(self):
        self._assert_get_gated("provider-policy-list", ProviderPerm.POLICY_VIEW)

    def test_purchase_list_gated_by_purchase_view(self):
        self._assert_get_gated("provider-purchase-list", ProviderPerm.PURCHASE_VIEW)

    def test_payout_list_gated_by_payout_view(self):
        self._assert_get_gated("provider-payout-list", ProviderPerm.PAYOUT_VIEW)

    def test_claim_list_gated_by_claim_view(self):
        self._assert_get_gated("provider-claim-list", ProviderPerm.CLAIM_VIEW)

    def test_issuance_list_gated_by_issuance_view(self):
        self._assert_get_gated("provider-issuance-list", ProviderPerm.ISSUANCE_VIEW)

    def test_policy_create_gated_by_policy_create(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.post(
                reverse("provider-policy-list"), self._policy_payload()
            ).status_code,
            status.HTTP_201_CREATED,
        )
        for role, user in self.members.items():
            self.client.force_authenticate(user)
            code = self.client.post(
                reverse("provider-policy-list"), self._policy_payload()
            ).status_code
            if ProviderPerm.POLICY_CREATE in PROVIDER_ROLE_PERMISSIONS[role]:
                self.assertEqual(code, status.HTTP_201_CREATED, role)
            else:
                self.assertEqual(code, status.HTTP_403_FORBIDDEN, role)

    def test_issuance_issue_gated_by_issuance_issue(self):
        # A holder clears the gate then 404s on the bogus id; a non-holder is
        # refused at the gate (403) before any lookup.
        url = reverse("provider-issuance-issue", args=[999])
        for role, user in self.members.items():
            self.client.force_authenticate(user)
            code = self.client.post(url, {"policy_number": "X"}).status_code
            if ProviderPerm.ISSUANCE_ISSUE in PROVIDER_ROLE_PERMISSIONS[role]:
                self.assertEqual(code, status.HTTP_404_NOT_FOUND, role)
            else:
                self.assertEqual(code, status.HTTP_403_FORBIDDEN, role)

    def test_claim_approve_gated_by_claim_decide(self):
        url = reverse("provider-claim-approve", args=[999])
        for role, user in self.members.items():
            self.client.force_authenticate(user)
            code = self.client.post(
                url, {"approved_amount": "1.00"}, format="json"
            ).status_code
            if ProviderPerm.CLAIM_DECIDE in PROVIDER_ROLE_PERMISSIONS[role]:
                self.assertEqual(code, status.HTTP_404_NOT_FOUND, role)
            else:
                self.assertEqual(code, status.HTTP_403_FORBIDDEN, role)


class ProviderMemberSelfServiceTests(ProviderRbacDbBase):
    def test_owner_can_add_member(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse("provider-member-list"),
            {
                "email": "new@bimaya.test",
                "full_name": "New Person",
                "password": "Himalaya#2026",
                "role": ProviderRole.POLICY_MANAGER.value,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="new@bimaya.test")
        self.assertEqual(user.role, User.Role.PROVIDER)
        self.assertTrue(user.is_verified)
        membership = ProviderMembership.objects.get(user=user)
        self.assertEqual(membership.provider, self.provider)
        self.assertEqual(membership.role, ProviderRole.POLICY_MANAGER.value)
        self.assertEqual(
            response.data["role"]["value"], ProviderRole.POLICY_MANAGER.value
        )
        self.assertEqual(
            set(response.data["permissions"]),
            set(PROVIDER_ROLE_PERMISSIONS[ProviderRole.POLICY_MANAGER.value]),
        )

    def test_company_admin_can_add_member(self):
        self.client.force_authenticate(self.members[ProviderRole.COMPANY_ADMIN.value])
        response = self.client.post(
            reverse("provider-member-list"),
            {
                "email": "new2@bimaya.test",
                "password": "Himalaya#2026",
                "role": ProviderRole.SALES_MANAGER.value,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_non_admin_member_cannot_view_or_manage_team(self):
        for role in (
            ProviderRole.POLICY_MANAGER.value,
            ProviderRole.CLAIMS_OFFICER.value,
            ProviderRole.SALES_MANAGER.value,
            ProviderRole.FINANCE_VIEWER.value,
        ):
            self.client.force_authenticate(self.members[role])
            self.assertEqual(
                self.client.get(reverse("provider-member-list")).status_code,
                status.HTTP_403_FORBIDDEN,
                role,
            )
            create = self.client.post(
                reverse("provider-member-list"),
                {
                    "email": f"x-{role}@bimaya.test",
                    "password": "Himalaya#2026",
                    "role": ProviderRole.FINANCE_VIEWER.value,
                },
                format="json",
            )
            self.assertEqual(create.status_code, status.HTTP_403_FORBIDDEN, role)
        self.assertFalse(User.objects.filter(email__startswith="x-").exists())

    def test_list_includes_owner_and_members_with_permissions(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("provider-member-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1 + len(ASSIGNABLE_ROLES))
        owner_row = next(r for r in response.data if r["membership_id"] is None)
        self.assertEqual(owner_row["role"]["value"], OWNER)
        self.assertEqual(owner_row["role"]["label"], "Owner")
        self.assertEqual(set(owner_row["permissions"]), set(ALL_PROVIDER_PERMS))

    def test_change_member_role(self):
        member = self.members[ProviderRole.FINANCE_VIEWER.value]
        membership = ProviderMembership.objects.get(user=member)
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            reverse("provider-member-role", args=[membership.id]),
            {"role": ProviderRole.CLAIMS_OFFICER.value},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership.refresh_from_db()
        self.assertEqual(membership.role, ProviderRole.CLAIMS_OFFICER.value)
        self.assertEqual(
            response.data["role"]["value"], ProviderRole.CLAIMS_OFFICER.value
        )

    def test_disable_and_enable_member(self):
        member = self.members[ProviderRole.SALES_MANAGER.value]
        membership = ProviderMembership.objects.get(user=member)
        self.client.force_authenticate(self.owner)
        disable = self.client.post(
            reverse("provider-member-disable", args=[membership.id])
        )
        self.assertEqual(disable.status_code, status.HTTP_200_OK)
        member.refresh_from_db()
        self.assertFalse(member.is_active)
        enable = self.client.post(
            reverse("provider-member-enable", args=[membership.id])
        )
        self.assertEqual(enable.status_code, status.HTTP_200_OK)
        member.refresh_from_db()
        self.assertTrue(member.is_active)

    def test_company_admin_cannot_disable_self(self):
        admin = self.members[ProviderRole.COMPANY_ADMIN.value]
        membership = ProviderMembership.objects.get(user=admin)
        self.client.force_authenticate(admin)
        response = self.client.post(
            reverse("provider-member-disable", args=[membership.id])
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        admin.refresh_from_db()
        self.assertTrue(admin.is_active)

    def test_cannot_manage_member_from_another_org(self):
        other_owner = make_provider_user("other-owner@bimaya.test")
        other = Provider.objects.create(
            user=other_owner, company_name="Other Co", is_approved=True
        )
        other_member = make_provider_user("other-member@bimaya.test")
        other_membership = ProviderMembership.objects.create(
            provider=other, user=other_member, role=ProviderRole.COMPANY_ADMIN.value
        )
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.get(
                reverse("provider-member-detail", args=[other_membership.id])
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.patch(
                reverse("provider-member-role", args=[other_membership.id]),
                {"role": ProviderRole.FINANCE_VIEWER.value},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        listing = self.client.get(reverse("provider-member-list"))
        emails = {row["email"] for row in listing.data}
        self.assertNotIn("other-member@bimaya.test", emails)


class ProviderRolesCatalogEndpointTests(ProviderRbacDbBase):
    def test_staff_view_holders_can_read_catalog(self):
        for user in (self.owner, self.members[ProviderRole.COMPANY_ADMIN.value]):
            self.client.force_authenticate(user)
            response = self.client.get(reverse("provider-roles"))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            values = {row["value"] for row in response.data["roles"]}
            self.assertEqual(values, set(ASSIGNABLE_ROLES))
            self.assertNotIn(OWNER, values)
            self.assertEqual(
                set(response.data["permissions"]), set(ALL_PROVIDER_PERMS)
            )

    def test_non_staff_view_roles_cannot_read_catalog(self):
        for role in (
            ProviderRole.POLICY_MANAGER.value,
            ProviderRole.CLAIMS_OFFICER.value,
            ProviderRole.SALES_MANAGER.value,
            ProviderRole.FINANCE_VIEWER.value,
        ):
            self.client.force_authenticate(self.members[role])
            self.assertEqual(
                self.client.get(reverse("provider-roles")).status_code,
                status.HTTP_403_FORBIDDEN,
                role,
            )


class ProviderProfileShapeTests(ProviderRbacDbBase):
    def test_owner_profile_has_public_id_and_all_permissions(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("provider-profile"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["public_id"], f"PRV-{self.provider.pk:05d}")
        self.assertEqual(response.data["my_role"], OWNER)
        self.assertEqual(
            set(response.data["my_permissions"]), set(ALL_PROVIDER_PERMS)
        )

    def test_member_profile_shows_scoped_permissions(self):
        member = self.members[ProviderRole.SALES_MANAGER.value]
        self.client.force_authenticate(member)
        response = self.client.get(reverse("provider-profile"))
        self.assertEqual(response.data["my_role"], ProviderRole.SALES_MANAGER.value)
        self.assertEqual(
            set(response.data["my_permissions"]),
            set(PROVIDER_ROLE_PERMISSIONS[ProviderRole.SALES_MANAGER.value]),
        )


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ProviderKycTests(ProviderRbacDbBase):
    def _file(self, name="reg.pdf"):
        return SimpleUploadedFile(
            name, b"%PDF-1.4 test", content_type="application/pdf"
        )

    def _make_doc(self, **overrides):
        defaults = {
            "provider": self.provider,
            "document_type": ProviderKyc.DocumentType.REGISTRATION,
            "file": self._file(),
            "uploaded_by": self.owner,
        }
        defaults.update(overrides)
        return ProviderKyc.objects.create(**defaults)

    def test_owner_can_upload_and_list(self):
        self.client.force_authenticate(self.owner)
        upload = self.client.post(
            reverse("provider-kyc-list"),
            {
                "document_type": ProviderKyc.DocumentType.REGISTRATION,
                "file": self._file(),
            },
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED)
        self.assertEqual(upload.data["status"], ProviderKyc.Status.PENDING)

        listing = self.client.get(reverse("provider-kyc-list"))
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listing.data), 1)
        row = listing.data[0]
        # The file is confidential — exposed only as a name, never a URL.
        self.assertNotIn("file", row)
        self.assertIn("file_name", row)

    def test_kyc_gated_to_owner_and_company_admin(self):
        for role in (
            ProviderRole.POLICY_MANAGER.value,
            ProviderRole.CLAIMS_OFFICER.value,
            ProviderRole.SALES_MANAGER.value,
            ProviderRole.FINANCE_VIEWER.value,
        ):
            self.client.force_authenticate(self.members[role])
            self.assertEqual(
                self.client.get(reverse("provider-kyc-list")).status_code,
                status.HTTP_403_FORBIDDEN,
                role,
            )
            upload = self.client.post(
                reverse("provider-kyc-list"),
                {"document_type": ProviderKyc.DocumentType.TAX, "file": self._file()},
                format="multipart",
            )
            self.assertEqual(upload.status_code, status.HTTP_403_FORBIDDEN, role)
        self.client.force_authenticate(self.members[ProviderRole.COMPANY_ADMIN.value])
        self.assertEqual(
            self.client.get(reverse("provider-kyc-list")).status_code,
            status.HTTP_200_OK,
        )

    def test_can_delete_pending_but_not_reviewed(self):
        self.client.force_authenticate(self.owner)
        verified = self._make_doc(document_type=ProviderKyc.DocumentType.LICENSE)
        verified.mark_verified(reviewer=self.owner)
        blocked = self.client.delete(
            reverse("provider-kyc-delete", args=[verified.id])
        )
        self.assertEqual(blocked.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(ProviderKyc.objects.filter(pk=verified.id).exists())

        pending = self._make_doc(document_type=ProviderKyc.DocumentType.OTHER)
        ok = self.client.delete(reverse("provider-kyc-delete", args=[pending.id]))
        self.assertEqual(ok.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProviderKyc.objects.filter(pk=pending.id).exists())

    def test_download_scoped_to_own_org(self):
        doc = self._make_doc()
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.get(
                reverse("provider-kyc-download", args=[doc.id])
            ).status_code,
            status.HTTP_200_OK,
        )
        other_owner = make_provider_user("kyc-other@bimaya.test")
        Provider.objects.create(
            user=other_owner, company_name="Other", is_approved=True
        )
        self.client.force_authenticate(other_owner)
        self.assertEqual(
            self.client.get(
                reverse("provider-kyc-download", args=[doc.id])
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_admin_can_review_verify_and_reject(self):
        admin = make_admin()
        doc = self._make_doc()
        self.client.force_authenticate(admin)

        listing = self.client.get(
            reverse("admin-provider-kyc-list", args=[self.provider.id])
        )
        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(len(listing.data), 1)

        verify = self.client.post(
            reverse("admin-provider-kyc-verify", args=[self.provider.id, doc.id])
        )
        self.assertEqual(verify.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.status, ProviderKyc.Status.VERIFIED)
        self.assertEqual(doc.reviewed_by, admin)

        blank = self.client.post(
            reverse("admin-provider-kyc-reject", args=[self.provider.id, doc.id]),
            {"note": ""},
            format="json",
        )
        self.assertEqual(blank.status_code, status.HTTP_400_BAD_REQUEST)

        good = self.client.post(
            reverse("admin-provider-kyc-reject", args=[self.provider.id, doc.id]),
            {"note": "Blurry scan"},
            format="json",
        )
        self.assertEqual(good.status_code, status.HTTP_200_OK)
        doc.refresh_from_db()
        self.assertEqual(doc.status, ProviderKyc.Status.REJECTED)
        self.assertEqual(doc.review_note, "Blurry scan")

    def test_admin_download_scoped_to_named_provider(self):
        admin = make_admin()
        doc = self._make_doc(document_type=ProviderKyc.DocumentType.TAX)
        self.client.force_authenticate(admin)
        self.assertEqual(
            self.client.get(
                reverse("admin-provider-kyc-document", args=[self.provider.id, doc.id])
            ).status_code,
            status.HTTP_200_OK,
        )
        other = Provider.objects.create(
            user=make_provider_user("adm-other@bimaya.test"),
            company_name="Other",
            is_approved=True,
        )
        self.assertEqual(
            self.client.get(
                reverse("admin-provider-kyc-document", args=[other.id, doc.id])
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_provider_kyc_requires_authentication(self):
        self.client.force_authenticate(None)
        self.assertEqual(
            self.client.get(reverse("provider-kyc-list")).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
