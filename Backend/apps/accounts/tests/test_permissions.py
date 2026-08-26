"""Unit tests for the shared RBAC permission classes."""

from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.core.permissions import (
    IsCustomer,
    IsOwnerOrPlatformAdmin,
    IsPlatformAdmin,
    IsProvider,
    IsVerified,
    ReadOnly,
)

User = get_user_model()


class PermissionTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.customer = User.objects.create_user(
            email="customer@example.com", password="x", is_verified=True
        )
        self.provider = User.objects.create_user(
            email="provider@example.com", password="x", role=User.Role.PROVIDER
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="x"
        )

    def _request(self, user, method="get"):
        request = getattr(self.factory, method)("/")
        request.user = user
        return request

    def test_role_permissions_only_match_their_own_role(self):
        cases = [
            (IsCustomer(), self.customer, [self.provider, self.admin]),
            (IsProvider(), self.provider, [self.customer, self.admin]),
            (IsPlatformAdmin(), self.admin, [self.customer, self.provider]),
        ]
        for permission, allowed, denied in cases:
            with self.subTest(permission=type(permission).__name__):
                self.assertTrue(permission.has_permission(self._request(allowed), None))
                for user in denied:
                    self.assertFalse(
                        permission.has_permission(self._request(user), None)
                    )

    def test_anonymous_users_are_denied(self):
        anonymous = SimpleNamespace(is_authenticated=False)
        for permission in (IsCustomer(), IsProvider(), IsPlatformAdmin(), IsVerified()):
            with self.subTest(permission=type(permission).__name__):
                self.assertFalse(
                    permission.has_permission(self._request(anonymous), None)
                )

    def test_is_verified_requires_a_confirmed_account(self):
        permission = IsVerified()
        self.assertTrue(permission.has_permission(self._request(self.customer), None))
        self.assertFalse(permission.has_permission(self._request(self.provider), None))

    def test_read_only_blocks_writes(self):
        permission = ReadOnly()
        self.assertTrue(
            permission.has_permission(self._request(self.customer, "get"), None)
        )
        self.assertFalse(
            permission.has_permission(self._request(self.customer, "post"), None)
        )

    def test_owner_or_admin_object_permission(self):
        permission = IsOwnerOrPlatformAdmin()
        record = SimpleNamespace(user=self.customer)
        view = SimpleNamespace(owner_field="user")

        self.assertTrue(
            permission.has_object_permission(
                self._request(self.customer), view, record
            )
        )
        self.assertTrue(
            permission.has_object_permission(self._request(self.admin), view, record)
        )
        self.assertFalse(
            permission.has_object_permission(self._request(self.provider), view, record)
        )

    def test_owner_field_supports_nested_paths(self):
        permission = IsOwnerOrPlatformAdmin()
        record = SimpleNamespace(provider=SimpleNamespace(user=self.provider))
        view = SimpleNamespace(owner_field="provider.user")

        self.assertTrue(
            permission.has_object_permission(
                self._request(self.provider), view, record
            )
        )
        self.assertFalse(
            permission.has_object_permission(
                self._request(self.customer), view, record
            )
        )

    def test_missing_owner_path_denies_rather_than_errors(self):
        permission = IsOwnerOrPlatformAdmin()
        view = SimpleNamespace(owner_field="provider.user")

        self.assertFalse(
            permission.has_object_permission(
                self._request(self.customer), view, SimpleNamespace()
            )
        )
