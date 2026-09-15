"""Unit tests for the code-defined RBAC catalog (:mod:`apps.staff.rbac`).

These assert the *policy* — the matrix in code — without touching the database:
every role grants exactly the permissions its spec section lists, System Owner
holds all of them, and least privilege holds for the sensitive actions.
"""

from django.test import SimpleTestCase

from apps.staff.rbac import (
    ALL_PERMS,
    ROLE_PERMISSIONS,
    Perm,
    StaffRole,
    permissions_for,
)


class RbacCatalogTests(SimpleTestCase):
    def test_every_role_has_a_permission_set(self):
        for role in StaffRole:
            self.assertIn(role.value, ROLE_PERMISSIONS)

    def test_system_owner_holds_every_permission(self):
        self.assertEqual(ROLE_PERMISSIONS[StaffRole.SYSTEM_OWNER.value], ALL_PERMS)

    def test_catalog_is_non_trivial(self):
        # The spec defines ~90 granular permissions; guard against an empty or
        # accidentally-truncated catalog.
        self.assertGreater(len(ALL_PERMS), 80)

    def test_role_permissions_are_subsets_of_the_catalog(self):
        for role, perms in ROLE_PERMISSIONS.items():
            with self.subTest(role=role):
                self.assertTrue(perms <= ALL_PERMS)

    def test_least_privilege_on_sensitive_actions(self):
        # Only roles whose job includes the action hold it — the spec's §21
        # least-privilege rule for KYC/financial/approval actions.
        cases = {
            Perm.KYC_APPROVE: {
                StaffRole.SYSTEM_OWNER,
                StaffRole.OPERATIONS_MANAGER,
                StaffRole.KYC_COMPLIANCE_OFFICER,
            },
            Perm.KYC_DOCUMENT_VIEW: {
                StaffRole.SYSTEM_OWNER,
                StaffRole.KYC_COMPLIANCE_OFFICER,
            },
            Perm.COMMISSION_MANAGE: {
                StaffRole.SYSTEM_OWNER,
                StaffRole.FINANCE_OFFICER,
            },
            Perm.PROVIDER_APPROVE: {
                StaffRole.SYSTEM_OWNER,
                StaffRole.OPERATIONS_MANAGER,
            },
            Perm.POLICY_APPROVE: {
                StaffRole.SYSTEM_OWNER,
                StaffRole.POLICY_MODERATOR,
            },
            Perm.CUSTOMER_SUSPEND: {
                StaffRole.SYSTEM_OWNER,
                StaffRole.OPERATIONS_MANAGER,
            },
        }
        for perm, holders in cases.items():
            holder_values = {role.value for role in holders}
            granted_to = {
                role for role, perms in ROLE_PERMISSIONS.items() if perm in perms
            }
            with self.subTest(perm=perm):
                self.assertEqual(granted_to, holder_values)

    def test_customer_support_cannot_touch_finance_or_kyc_documents(self):
        support = ROLE_PERMISSIONS[StaffRole.CUSTOMER_SUPPORT.value]
        self.assertNotIn(Perm.KYC_DOCUMENT_VIEW, support)
        self.assertNotIn(Perm.COMMISSION_MANAGE, support)
        self.assertNotIn(Perm.PAYMENT_REFUND, support)

    def test_permissions_for_unions_multiple_roles(self):
        combined = permissions_for(
            [StaffRole.POLICY_MODERATOR.value, StaffRole.FINANCE_OFFICER.value]
        )
        self.assertIn(Perm.POLICY_APPROVE, combined)
        self.assertIn(Perm.COMMISSION_MANAGE, combined)

    def test_permissions_for_ignores_unknown_roles(self):
        self.assertEqual(permissions_for(["NOT_A_ROLE"]), set())
