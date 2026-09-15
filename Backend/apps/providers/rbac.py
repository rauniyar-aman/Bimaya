"""The Bimaya provider-organisation RBAC catalog — roles and granular permissions.

Mirrors :mod:`apps.staff.rbac` but is *organisation-scoped*: the policy here
governs what a member may do **within their own insurance company**, resolved
per provider in :mod:`apps.providers.access`. Like the staff catalog this is
*code*, not data — the roles, the ``module.action`` permissions and the
role→permission matrix all live here so the security policy is reviewable in
version control and cannot be edited at runtime into an unsafe state. Only the
*assignment* of a role to a person is stored
(:class:`apps.providers.models.ProviderMembership`); the organisation owner is
``Provider.user`` and is never a stored membership row.

The guiding rule is least privilege — a role is granted only the permissions its
job needs. ``OWNER`` and ``COMPANY_ADMIN`` are the only roles holding everything.
"""

from django.db import models

# The implicit owner "role". Not a :class:`ProviderMembership` choice — the owner
# is ``Provider.user`` — but role resolution returns this sentinel so callers can
# treat the owner uniformly. Owners always hold every provider permission.
OWNER = "OWNER"


class ProviderRole(models.TextChoices):
    """The assignable roles within a provider organisation.

    The owner (``Provider.user``) is implicit and not listed here; these five are
    what a company Owner / Company Admin can assign to added members. Distinct
    from :class:`apps.staff.rbac.StaffRole` (internal Bimaya staff) — every holder
    here is a ``PROVIDER`` user scoped to one insurance company.
    """

    COMPANY_ADMIN = "COMPANY_ADMIN", "Company Admin"
    POLICY_MANAGER = "POLICY_MANAGER", "Policy Manager"
    CLAIMS_OFFICER = "CLAIMS_OFFICER", "Claims Officer"
    SALES_MANAGER = "SALES_MANAGER", "Sales / Relationship Manager"
    FINANCE_VIEWER = "FINANCE_VIEWER", "Finance Viewer"


class ProviderPerm:
    """The granular ``module.action`` permission catalog for provider orgs.

    String constants, grouped by module, so views and the matrix below refer to
    them symbolically (``ProviderPerm.POLICY_CREATE``) rather than by raw string.
    """

    # Company profile
    COMPANY_EDIT = "company.edit"

    # Staff & access (managing the organisation's own team)
    STAFF_VIEW = "staff.view"
    STAFF_MANAGE = "staff.manage"

    # Policies
    POLICY_VIEW = "policy.view"
    POLICY_CREATE = "policy.create"
    POLICY_EDIT = "policy.edit"
    POLICY_DELETE = "policy.delete"
    POLICY_SUBMIT = "policy.submit"
    POLICY_DEACTIVATE = "policy.deactivate"

    # Issuance queue
    ISSUANCE_VIEW = "issuance.view"
    ISSUANCE_ISSUE = "issuance.issue"

    # Claims
    CLAIM_VIEW = "claim.view"
    CLAIM_REVIEW = "claim.review"
    CLAIM_DECIDE = "claim.decide"
    CLAIM_PAYOUT = "claim.payout"
    CLAIM_MESSAGE = "claim.message"

    # Sales / finance reads
    PURCHASE_VIEW = "purchase.view"
    PAYOUT_VIEW = "payout.view"
    ANALYTICS_VIEW = "analytics.view"

    # Provider KYC documents
    PROVIDER_KYC_VIEW = "provider_kyc.view"
    PROVIDER_KYC_UPLOAD = "provider_kyc.upload"

    @classmethod
    def all(cls):
        """Every permission string in the catalog."""
        return frozenset(
            value
            for key, value in vars(cls).items()
            if key.isupper() and isinstance(value, str)
        )


# Every provider permission — the owner and Company Admin hold all of them.
ALL_PROVIDER_PERMS = ProviderPerm.all()


# Role → permission sets. Least privilege: each role gets only what its job
# needs. OWNER (sentinel above) and COMPANY_ADMIN resolve to the full set; the
# others are scoped by function — a Policy Manager never sees claims or payouts,
# a Claims Officer only works claims, Sales sees purchases, Finance is read-only.
PROVIDER_ROLE_PERMISSIONS = {
    ProviderRole.COMPANY_ADMIN.value: ALL_PROVIDER_PERMS,
    ProviderRole.POLICY_MANAGER.value: frozenset(
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
        }
    ),
    ProviderRole.CLAIMS_OFFICER.value: frozenset(
        {
            ProviderPerm.CLAIM_VIEW,
            ProviderPerm.CLAIM_REVIEW,
            ProviderPerm.CLAIM_DECIDE,
            ProviderPerm.CLAIM_PAYOUT,
            ProviderPerm.CLAIM_MESSAGE,
        }
    ),
    ProviderRole.SALES_MANAGER.value: frozenset(
        {
            ProviderPerm.POLICY_VIEW,
            ProviderPerm.PURCHASE_VIEW,
            ProviderPerm.ANALYTICS_VIEW,
        }
    ),
    ProviderRole.FINANCE_VIEWER.value: frozenset(
        {
            ProviderPerm.POLICY_VIEW,
            ProviderPerm.PURCHASE_VIEW,
            ProviderPerm.PAYOUT_VIEW,
            ProviderPerm.ANALYTICS_VIEW,
        }
    ),
}


def permissions_for(role_values):
    """The union of provider permissions granted by the given role values.

    The :data:`OWNER` sentinel and ``COMPANY_ADMIN`` both resolve to every
    permission; unknown roles contribute nothing.
    """
    granted = set()
    for role in role_values:
        if role == OWNER:
            granted |= ALL_PROVIDER_PERMS
        else:
            granted |= PROVIDER_ROLE_PERMISSIONS.get(role, frozenset())
    return granted
