"""The ``seed_staff_roles`` command maps existing admins to System Owner."""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.staff.models import StaffRoleAssignment
from apps.staff.rbac import StaffRole

User = get_user_model()


class SeedStaffRolesTests(TestCase):
    def _admin(self, email):
        return User.objects.create_user(
            email=email,
            password="Himalaya#2026",
            role=User.Role.ADMIN,
            is_verified=True,
        )

    def test_grants_system_owner_to_each_admin(self):
        admin = self._admin("admin@bimaya.test")
        call_command("seed_staff_roles")
        self.assertTrue(
            StaffRoleAssignment.objects.filter(
                user=admin, role=StaffRole.SYSTEM_OWNER.value
            ).exists()
        )

    def test_is_idempotent(self):
        self._admin("admin@bimaya.test")
        call_command("seed_staff_roles")
        call_command("seed_staff_roles")
        self.assertEqual(
            StaffRoleAssignment.objects.filter(
                role=StaffRole.SYSTEM_OWNER.value
            ).count(),
            1,
        )

    def test_does_not_touch_non_admins(self):
        User.objects.create_user(
            email="cust@bimaya.test", password="Himalaya#2026", is_verified=True
        )
        call_command("seed_staff_roles")
        self.assertEqual(StaffRoleAssignment.objects.count(), 0)
