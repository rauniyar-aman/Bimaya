"""The granular permission gate for internal-staff endpoints.

This sits *on top of* the coarse ``User.role == ADMIN`` check: only platform
administrators reach admin endpoints at all, and this class then requires the
specific ``module.action`` permission a view declares.
"""

from rest_framework.permissions import BasePermission

from .services import staff_permissions


class HasStaffPermission(BasePermission):
    """Require the ``required_permission`` a view declares.

    A view sets ``required_permission = Perm.X``. Access is granted when the
    user is a platform administrator *and* holds that permission through their
    assigned staff roles (or is a superuser).

    A view that declares no ``required_permission`` falls back to plain
    administrator access — so an endpoint that has not yet been mapped to a
    granular permission stays admin-only and never becomes accidentally public.
    """

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.is_platform_admin):
            return False
        required = getattr(view, "required_permission", None)
        if required is None:
            return True
        return required in staff_permissions(user)
