"""Staff-management API: access control, lifecycle, roles catalog, audit.

Complements :mod:`apps.staff.tests.test_enforcement` (which asserts the gate on
the admin-panel action endpoints). Here we drive the staff-management surface
itself — creating staff, assigning roles, enable/disable, the read-only roles
matrix and the audit log — and assert both who may reach each endpoint and what
each state change records.
"""

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.staff.models import AuditLogEntry, StaffRoleAssignment
from apps.staff.rbac import ALL_PERMS, StaffRole

User = get_user_model()

PASSWORD = "Himalaya#2026"


def make_admin(email, *roles):
    user = User.objects.create_user(
        email=email, password=PASSWORD, role=User.Role.ADMIN, is_verified=True
    )
    for role in roles:
        StaffRoleAssignment.objects.create(user=user, role=role)
    return user


class StaffManagementTestBase(APITestCase):
    def setUp(self):
        self.owner = make_admin("owner@bimaya.test", StaffRole.SYSTEM_OWNER.value)
        self.plain_admin = make_admin("plain@bimaya.test")  # admin, no staff roles
        self.ops = make_admin("ops@bimaya.test", StaffRole.OPERATIONS_MANAGER.value)
        self.target = make_admin("target@bimaya.test", StaffRole.CUSTOMER_SUPPORT.value)
        self.customer = User.objects.create_user(
            email="cust@bimaya.test", password=PASSWORD, is_verified=True
        )
        self.provider = User.objects.create_user(
            email="prov@bimaya.test",
            password=PASSWORD,
            role=User.Role.PROVIDER,
            is_verified=True,
        )


class StaffAccessControlTests(StaffManagementTestBase):
    """Every endpoint requires its granular permission; nobody else gets in."""

    def _assert_status(self, actor, method, url, expected, body=None):
        self.client.force_authenticate(actor)
        response = getattr(self.client, method)(url, body or {}, format="json")
        self.assertEqual(
            response.status_code,
            expected,
            msg=f"{method.upper()} {url} as {actor} → {response.status_code}",
        )

    def test_staff_list_requires_staff_view(self):
        url = reverse("staff-list")
        self._assert_status(None, "get", url, status.HTTP_401_UNAUTHORIZED)
        self._assert_status(self.customer, "get", url, status.HTTP_403_FORBIDDEN)
        self._assert_status(self.provider, "get", url, status.HTTP_403_FORBIDDEN)
        self._assert_status(self.plain_admin, "get", url, status.HTTP_403_FORBIDDEN)
        # Operations Manager has audit_log.view but not staff.view.
        self._assert_status(self.ops, "get", url, status.HTTP_403_FORBIDDEN)
        self._assert_status(self.owner, "get", url, status.HTTP_200_OK)

    def test_create_requires_staff_create(self):
        url = reverse("staff-list")
        body = {
            "email": "new.hire@bimaya.test",
            "password": PASSWORD,
            "roles": [StaffRole.CLAIMS_OFFICER.value],
        }
        self._assert_status(None, "post", url, status.HTTP_401_UNAUTHORIZED, body)
        self._assert_status(self.customer, "post", url, status.HTTP_403_FORBIDDEN, body)
        self._assert_status(self.ops, "post", url, status.HTTP_403_FORBIDDEN, body)
        self._assert_status(self.owner, "post", url, status.HTTP_201_CREATED, body)

    def test_roles_assign_requires_permission_assign(self):
        url = reverse("staff-roles", args=[self.target.id])
        body = {"roles": [StaffRole.CLAIMS_OFFICER.value]}
        self._assert_status(self.customer, "patch", url, status.HTTP_403_FORBIDDEN, body)
        self._assert_status(self.ops, "patch", url, status.HTTP_403_FORBIDDEN, body)
        self._assert_status(self.owner, "patch", url, status.HTTP_200_OK, body)

    def test_disable_requires_staff_deactivate(self):
        url = reverse("staff-disable", args=[self.target.id])
        self._assert_status(self.ops, "post", url, status.HTTP_403_FORBIDDEN)
        self._assert_status(self.owner, "post", url, status.HTTP_200_OK)

    def test_roles_catalog_requires_role_view(self):
        url = reverse("staff-roles-catalog")
        self._assert_status(None, "get", url, status.HTTP_401_UNAUTHORIZED)
        self._assert_status(self.customer, "get", url, status.HTTP_403_FORBIDDEN)
        self._assert_status(self.plain_admin, "get", url, status.HTTP_403_FORBIDDEN)
        self._assert_status(self.ops, "get", url, status.HTTP_403_FORBIDDEN)
        self._assert_status(self.owner, "get", url, status.HTTP_200_OK)

    def test_audit_requires_audit_log_view(self):
        url = reverse("staff-audit-log")
        self._assert_status(None, "get", url, status.HTTP_401_UNAUTHORIZED)
        self._assert_status(self.customer, "get", url, status.HTTP_403_FORBIDDEN)
        self._assert_status(self.plain_admin, "get", url, status.HTTP_403_FORBIDDEN)
        # Operations Manager holds audit_log.view.
        self._assert_status(self.ops, "get", url, status.HTTP_200_OK)
        self._assert_status(self.owner, "get", url, status.HTTP_200_OK)

    def test_detail_404_for_non_staff_user(self):
        url = reverse("staff-detail", args=[self.customer.id])
        self._assert_status(self.owner, "get", url, status.HTTP_404_NOT_FOUND)


class StaffCreateTests(StaffManagementTestBase):
    def test_create_staff_account_and_assignments(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse("staff-list"),
            {
                "email": "new.officer@bimaya.test",
                "full_name": "Nabin Officer",
                "password": PASSWORD,
                "roles": [
                    StaffRole.CLAIMS_OFFICER.value,
                    StaffRole.FINANCE_OFFICER.value,
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = User.objects.get(email="new.officer@bimaya.test")
        self.assertEqual(created.role, User.Role.ADMIN)
        self.assertTrue(created.is_verified)
        self.assertTrue(created.is_active)
        self.assertTrue(created.check_password(PASSWORD))

        assignments = StaffRoleAssignment.objects.filter(user=created)
        self.assertEqual(assignments.count(), 2)
        for assignment in assignments:
            self.assertEqual(assignment.granted_by, self.owner)

        # Response carries the resolved permissions of the assigned roles.
        self.assertEqual(
            {role["value"] for role in response.data["roles"]},
            {StaffRole.CLAIMS_OFFICER.value, StaffRole.FINANCE_OFFICER.value},
        )
        self.assertTrue(response.data["permissions"])

        self.assertEqual(
            AuditLogEntry.objects.filter(
                action="staff.create", entity_id=str(created.id)
            ).count(),
            1,
        )

    def test_create_sends_welcome_email_without_the_password(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse("staff-list"),
            {
                "email": "welcomed@bimaya.test",
                "full_name": "Welcomed Staff",
                "password": PASSWORD,
                "roles": [StaffRole.OPERATIONS_MANAGER.value],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Exactly one onboarding email, to the new member — carrying their role
        # but never the temporary password (the admin shares that out-of-band).
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["welcomed@bimaya.test"])
        self.assertIn(StaffRole.OPERATIONS_MANAGER.label, message.body)
        html = message.alternatives[0][0] if message.alternatives else ""
        self.assertNotIn(PASSWORD, message.body)
        self.assertNotIn(PASSWORD, html)
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse("staff-list"),
            {
                "email": self.target.email.upper(),  # case-insensitive clash
                "password": PASSWORD,
                "roles": [StaffRole.CLAIMS_OFFICER.value],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_requires_at_least_one_role(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            reverse("staff-list"),
            {"email": "no.role@bimaya.test", "password": PASSWORD, "roles": []},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StaffRolesTests(StaffManagementTestBase):
    def test_set_roles_diffs_assignments_and_audits(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            reverse("staff-roles", args=[self.target.id]),
            {
                "roles": [
                    StaffRole.CLAIMS_OFFICER.value,
                    StaffRole.FINANCE_OFFICER.value,
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roles = set(
            StaffRoleAssignment.objects.filter(user=self.target).values_list(
                "role", flat=True
            )
        )
        # CUSTOMER_SUPPORT removed; the two new roles added.
        self.assertEqual(
            roles,
            {StaffRole.CLAIMS_OFFICER.value, StaffRole.FINANCE_OFFICER.value},
        )
        for assignment in StaffRoleAssignment.objects.filter(user=self.target):
            self.assertEqual(assignment.granted_by, self.owner)
        self.assertTrue(
            AuditLogEntry.objects.filter(
                action="permission.assign", entity_id=str(self.target.id)
            ).exists()
        )

    def test_cannot_strip_last_system_owner(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            reverse("staff-roles", args=[self.owner.id]),
            {"roles": [StaffRole.CUSTOMER_SUPPORT.value]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            StaffRoleAssignment.objects.filter(
                user=self.owner, role=StaffRole.SYSTEM_OWNER.value
            ).exists()
        )

    def test_can_demote_owner_when_another_owner_exists(self):
        make_admin("owner2@bimaya.test", StaffRole.SYSTEM_OWNER.value)
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            reverse("staff-roles", args=[self.owner.id]),
            {"roles": [StaffRole.CUSTOMER_SUPPORT.value]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            StaffRoleAssignment.objects.filter(
                user=self.owner, role=StaffRole.SYSTEM_OWNER.value
            ).exists()
        )


class StaffLifecycleTests(StaffManagementTestBase):
    def test_disable_then_enable(self):
        self.client.force_authenticate(self.owner)
        disable = self.client.post(reverse("staff-disable", args=[self.target.id]))
        self.assertEqual(disable.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertTrue(
            AuditLogEntry.objects.filter(
                action="staff.deactivate", entity_id=str(self.target.id)
            ).exists()
        )

        enable = self.client.post(reverse("staff-enable", args=[self.target.id]))
        self.assertEqual(enable.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)
        self.assertTrue(
            AuditLogEntry.objects.filter(
                action="staff.activate", entity_id=str(self.target.id)
            ).exists()
        )

    def test_cannot_disable_self(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(reverse("staff-disable", args=[self.owner.id]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_active)

    def test_cannot_disable_last_system_owner(self):
        # A superuser (all permissions, not the sole owner) tries to disable the
        # only active System Owner — the lockout guard refuses.
        root = User.objects.create_superuser(email="root@bimaya.test", password=PASSWORD)
        self.client.force_authenticate(root)
        response = self.client.post(reverse("staff-disable", args=[self.owner.id]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_active)


class RolesCatalogTests(StaffManagementTestBase):
    def test_catalog_shape(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse("staff-roles-catalog"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["roles"]), len(StaffRole.choices))
        self.assertEqual(sorted(response.data["permissions"]), sorted(ALL_PERMS))
        owner_row = next(
            row
            for row in response.data["roles"]
            if row["value"] == StaffRole.SYSTEM_OWNER.value
        )
        self.assertEqual(owner_row["permission_count"], len(ALL_PERMS))
        for row in response.data["roles"]:
            self.assertTrue(row["permissions"], msg=f"{row['value']} has no perms")


class AuditLogTests(StaffManagementTestBase):
    def test_audit_list_is_paginated_and_readable(self):
        # Generate an entry through a real action, then read it back.
        self.client.force_authenticate(self.owner)
        self.client.post(reverse("staff-disable", args=[self.target.id]))

        response = self.client.get(reverse("staff-audit-log"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_audit_list_is_read_only(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(reverse("staff-audit-log"), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_audit_filters_by_action(self):
        self.client.force_authenticate(self.owner)
        self.client.post(reverse("staff-disable", args=[self.target.id]))
        self.client.post(reverse("staff-enable", args=[self.target.id]))
        response = self.client.get(
            reverse("staff-audit-log"), {"action": "staff.activate"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["results"])
        for row in response.data["results"]:
            self.assertEqual(row["action"], "staff.activate")
