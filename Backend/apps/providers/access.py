"""Resolving a user's provider organisation and their role within it, plus the
membership-aware permission shared by the provider APIs.

The organisation owner is ``Provider.user``; extra staff and viewers are
:class:`~apps.providers.models.ProviderMembership` rows. These helpers hide that
split so callers can simply ask "which provider is this user, and what may they
do here".
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Provider, ProviderMembership, ProviderRole

# Roles allowed to perform write actions by default — everyone except viewers.
WRITE_ROLES = (ProviderRole.OWNER, ProviderRole.STAFF)


def provider_for(user):
    """The provider organisation this user owns or belongs to, or ``None``."""
    if not (user and user.is_authenticated):
        return None
    owned = Provider.objects.filter(user=user).first()
    if owned is not None:
        return owned
    membership = (
        ProviderMembership.objects.filter(user=user)
        .select_related("provider")
        .first()
    )
    return membership.provider if membership is not None else None


def role_for(user, provider):
    """This user's role in ``provider`` as a string, or ``None``.

    Returns ``"OWNER"`` when the user owns the provider, otherwise the
    membership role (``"STAFF"`` / ``"VIEWER"``), or ``None`` when the user is
    not part of the organisation.
    """
    if not (user and user.is_authenticated) or provider is None:
        return None
    if provider.user_id == user.id:
        return ProviderRole.OWNER.value
    membership = provider.memberships.filter(user=user).first()
    return membership.role if membership is not None else None


class IsProviderTeamMember(BasePermission):
    """Gate the provider APIs by organisation membership and role.

    Any authenticated, verified provider user may read (safe methods). Writes
    are limited to the roles in ``view.write_roles`` (default: owner + staff, so
    viewers are read-only). A provider still completing onboarding — no profile
    yet, hence no role — is let through on writes so the view can raise its own,
    more specific "profile required" error; only an explicit viewer is blocked.
    """

    message = "Your role does not allow this action."

    def has_permission(self, request, view):
        user = request.user
        if not (
            user and user.is_authenticated and user.is_provider and user.is_verified
        ):
            return False
        if request.method in SAFE_METHODS:
            return True
        role = role_for(user, provider_for(user))
        if role is None:
            return True
        allowed = getattr(view, "write_roles", WRITE_ROLES)
        return role in allowed
