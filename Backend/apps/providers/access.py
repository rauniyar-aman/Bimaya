"""Resolving a user's provider organisation and their role within it, plus the
granular permission gate shared by the provider APIs.

The organisation owner is ``Provider.user``; added staff are
:class:`~apps.providers.models.ProviderMembership` rows. These helpers hide that
split so callers can simply ask "which provider is this user, what role do they
hold, and what may they do here". The role→permission policy is *code*
(:mod:`apps.providers.rbac`); this module only resolves and enforces it.
"""

from rest_framework.permissions import BasePermission

from .models import Provider, ProviderMembership
from .rbac import OWNER, permissions_for


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
    """This user's role in ``provider``, or ``None``.

    Returns the :data:`~apps.providers.rbac.OWNER` sentinel when the user owns
    the provider, otherwise the membership role (one of the assignable
    :class:`~apps.providers.rbac.ProviderRole` values), or ``None`` when the user
    is not part of the organisation.
    """
    if not (user and user.is_authenticated) or provider is None:
        return None
    if provider.user_id == user.id:
        return OWNER
    membership = provider.memberships.filter(user=user).first()
    return membership.role if membership is not None else None


def provider_permissions(user, provider=None):
    """The set of provider permissions ``user`` holds in their organisation.

    Owners and Company Admins hold everything; added members hold only what their
    role grants. Empty for anyone outside the organisation. ``provider`` may be
    passed to avoid re-resolving it.
    """
    if provider is None:
        provider = provider_for(user)
    role = role_for(user, provider)
    if role is None:
        return set()
    return set(permissions_for([role]))


class HasProviderPermission(BasePermission):
    """Gate the provider APIs by organisation membership and granular role.

    Mirrors :class:`apps.staff.permissions.HasStaffPermission` but
    organisation-scoped: the caller must be an authenticated, verified provider
    account that resolves to a provider organisation, and must hold the view's
    ``required_permission`` within it. Owners hold every permission; added members
    hold only what their role grants (:mod:`apps.providers.rbac`).

    Views declare a static ``required_permission``; a method-dependent view sets
    it in ``initial()`` before calling ``super().initial()`` (see
    :class:`~apps.providers.views.ProviderProfileView`). A view may set
    ``allow_onboarding = True`` to let a verified provider with no organisation
    yet through, so it can run its own onboarding / create-or-404 flow.
    """

    message = "Your role does not allow this action."

    def has_permission(self, request, view):
        user = request.user
        if not (
            user and user.is_authenticated and user.is_provider and user.is_verified
        ):
            return False
        provider = provider_for(user)
        if provider is None:
            # Not yet onboarded (no profile, hence no role). Only endpoints that
            # opt in — the profile upsert and analytics — let this through to
            # raise their own, more specific "profile required" response.
            return bool(getattr(view, "allow_onboarding", False))
        required = getattr(view, "required_permission", None)
        if required is None:
            return True
        return required in provider_permissions(user, provider)
