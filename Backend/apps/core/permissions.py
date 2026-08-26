"""Reusable permission classes for role-based access control.

These lean on the convenience properties defined on ``accounts.User``
(``is_customer`` / ``is_provider`` / ``is_platform_admin``) so this module stays
free of app-level imports.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsVerified(BasePermission):
    """Authenticated users who have completed OTP verification."""

    message = "Please verify your account before continuing."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_verified)


class IsCustomer(BasePermission):
    """Only customers (people buying insurance)."""

    message = "Only customer accounts can perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_customer)


class IsProvider(BasePermission):
    """Only insurance providers (companies listing policies)."""

    message = "Only insurance provider accounts can perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_provider)


class IsPlatformAdmin(BasePermission):
    """Only Bimaya administrators."""

    message = "Administrator access is required."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_platform_admin)


class ReadOnly(BasePermission):
    """Allow safe (non-mutating) methods only."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsOwnerOrPlatformAdmin(BasePermission):
    """Object-level: the owner of a record, or an administrator.

    Views set ``owner_field`` to the attribute path holding the owning user;
    it defaults to ``user``. Nested paths are supported, e.g. ``"policy.provider.user"``.
    """

    message = "You do not have access to this record."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_platform_admin or user.is_staff:
            return True

        owner = obj
        for part in getattr(view, "owner_field", "user").split("."):
            owner = getattr(owner, part, None)
            if owner is None:
                return False
        return owner == user
