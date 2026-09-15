"""Tests for permission resolution and audit recording (:mod:`apps.staff.services`)."""

from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.staff.models import AuditLogEntry, StaffRoleAssignment
from apps.staff.permissions import HasStaffPermission
from apps.staff.rbac import ALL_PERMS, Perm, StaffRole
from apps.staff.services import record_audit, staff_permissions, staff_role_values

User = get_user_model()


def _admin(email="admin@bimaya.test", **extra):
    return User.objects.create_user(
        email=email, password="Himalaya#2026", role=User.Role.ADMIN, is_verified=True, **extra
    )


class StaffPermissionsResolutionTests(TestCase):
    def test_anonymous_holds_nothing(self):
        anon = SimpleNamespace(is_authenticated=False, is_platform_admin=False)
        self.assertEqual(staff_permissions(anon), set())

    def test_non_admin_holds_nothing(self):
        customer = User.objects.create_user(
            email="c@bimaya.test", password="Himalaya#2026", is_verified=True
        )
        self.assertEqual(staff_permissions(customer), set())

    def test_admin_without_a_role_holds_nothing(self):
        # A platform admin with no staff role assigned resolves to no granular
        # permissions — least privilege, not implicit full access.
        admin = _admin()
        self.assertEqual(staff_permissions(admin), set())

    def test_superuser_holds_everything(self):
        superuser = User.objects.create_superuser(
            email="root@bimaya.test", password="Himalaya#2026"
        )
        self.assertEqual(staff_permissions(superuser), set(ALL_PERMS))

    def test_assigned_role_grants_exactly_its_permissions(self):
        admin = _admin()
        StaffRoleAssignment.objects.create(
            user=admin, role=StaffRole.FINANCE_OFFICER.value
        )
        perms = staff_permissions(admin)
        self.assertIn(Perm.COMMISSION_MANAGE, perms)
        self.assertNotIn(Perm.KYC_APPROVE, perms)

    def test_multiple_roles_union(self):
        admin = _admin()
        StaffRoleAssignment.objects.create(
            user=admin, role=StaffRole.FINANCE_OFFICER.value
        )
        StaffRoleAssignment.objects.create(
            user=admin, role=StaffRole.POLICY_MODERATOR.value
        )
        perms = staff_permissions(admin)
        self.assertIn(Perm.COMMISSION_MANAGE, perms)
        self.assertIn(Perm.POLICY_APPROVE, perms)

    def test_staff_role_values_lists_assignments(self):
        admin = _admin()
        StaffRoleAssignment.objects.create(
            user=admin, role=StaffRole.CLAIMS_OFFICER.value
        )
        self.assertEqual(staff_role_values(admin), [StaffRole.CLAIMS_OFFICER.value])


class HasStaffPermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _view(self, required):
        return SimpleNamespace(required_permission=required)

    def _request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_denies_non_admin(self):
        customer = User.objects.create_user(
            email="c@bimaya.test", password="Himalaya#2026", is_verified=True
        )
        permission = HasStaffPermission()
        self.assertFalse(
            permission.has_permission(
                self._request(customer), self._view(Perm.KYC_APPROVE)
            )
        )

    def test_grants_admin_with_the_permission(self):
        admin = _admin()
        StaffRoleAssignment.objects.create(
            user=admin, role=StaffRole.KYC_COMPLIANCE_OFFICER.value
        )
        permission = HasStaffPermission()
        self.assertTrue(
            permission.has_permission(
                self._request(admin), self._view(Perm.KYC_APPROVE)
            )
        )

    def test_denies_admin_missing_the_permission(self):
        admin = _admin()
        StaffRoleAssignment.objects.create(
            user=admin, role=StaffRole.MARKETING_OFFICER.value
        )
        permission = HasStaffPermission()
        self.assertFalse(
            permission.has_permission(
                self._request(admin), self._view(Perm.KYC_APPROVE)
            )
        )

    def test_unmapped_view_falls_back_to_admin_only(self):
        # A view that declares no required_permission stays admin-only — an
        # ordinary admin passes, a non-admin does not.
        admin = _admin()
        permission = HasStaffPermission()
        self.assertTrue(
            permission.has_permission(self._request(admin), self._view(None))
        )

    def test_superuser_passes_any_view(self):
        superuser = User.objects.create_superuser(
            email="root@bimaya.test", password="Himalaya#2026"
        )
        permission = HasStaffPermission()
        self.assertTrue(
            permission.has_permission(
                self._request(superuser), self._view(Perm.SYSTEM_CONFIGURE)
            )
        )


class RecordAuditTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin = _admin()

    def test_writes_one_entry_with_actor_snapshot(self):
        request = self.factory.post("/", REMOTE_ADDR="203.0.113.7")
        request.user = self.admin
        entry = record_audit(
            actor=self.admin,
            action=Perm.KYC_APPROVE,
            module="kyc",
            entity_type="CustomerKyc",
            entity_id=42,
            changes={"status": [None, "VERIFIED"]},
            request=request,
        )
        self.assertIsNotNone(entry)
        self.assertEqual(AuditLogEntry.objects.count(), 1)
        self.assertEqual(entry.actor, self.admin)
        self.assertEqual(entry.actor_role, User.Role.ADMIN)
        self.assertEqual(entry.action, Perm.KYC_APPROVE)
        self.assertEqual(entry.entity_id, "42")
        self.assertEqual(entry.ip_address, "203.0.113.7")

    def test_prefers_forwarded_for_client_ip(self):
        request = self.factory.post(
            "/", HTTP_X_FORWARDED_FOR="198.51.100.5, 10.0.0.1", REMOTE_ADDR="10.0.0.1"
        )
        request.user = self.admin
        entry = record_audit(
            actor=self.admin, action=Perm.PROVIDER_APPROVE, request=request
        )
        self.assertEqual(entry.ip_address, "198.51.100.5")

    def test_best_effort_never_raises(self):
        # A logging failure must not blow up the business action it records; the
        # helper swallows the error and returns None.
        with mock.patch.object(
            AuditLogEntry.objects, "create", side_effect=RuntimeError("db down")
        ):
            result = record_audit(actor=self.admin, action=Perm.KYC_APPROVE)
        self.assertIsNone(result)
