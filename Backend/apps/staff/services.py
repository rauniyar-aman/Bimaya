"""Resolving a staff member's permissions, and recording the audit trail.

Following the codebase convention (see :mod:`apps.notifications.services`),
there are no signals — audit entries are written by explicit ``record_audit``
calls from the action views that perform sensitive operations.
"""

from apps.core.email import send_branded_email

from .models import AuditLogEntry, StaffRoleAssignment
from .rbac import ALL_PERMS, permissions_for


def staff_role_values(user):
    """The coded staff-role strings assigned to ``user`` (may be empty)."""
    if not (user and user.is_authenticated):
        return []
    return list(
        StaffRoleAssignment.objects.filter(user=user)
        .values_list("role", flat=True)
        .distinct()
    )


def staff_permissions(user):
    """The set of granular permissions ``user`` holds.

    Empty for anyone who is not a signed-in platform administrator. A superuser
    implicitly holds everything (Django's own escape hatch), which also keeps
    the initial ``createsuperuser`` account working before any role is seeded.
    Otherwise it is the union of the permissions granted by the user's assigned
    staff roles.
    """
    if not (user and user.is_authenticated and user.is_platform_admin):
        return set()
    if user.is_superuser:
        return set(ALL_PERMS)
    return permissions_for(staff_role_values(user))


def _humanize_list(items):
    """Join labels for prose: ``"A"``, ``"A and B"``, or ``"A, B and C"``."""
    items = [item for item in items if item]
    if len(items) <= 1:
        return items[0] if items else ""
    return ", ".join(items[:-1]) + " and " + items[-1]


def send_staff_welcome_email(user, *, role_labels=None):
    """Tell a newly-created staff member their console account is ready.

    A transactional onboarding email, sent directly like the OTP emails in
    :mod:`apps.accounts.services` (not through the in-app notification fan-out):
    it confirms the account, names the roles granted, and links to sign-in. The
    temporary password is set by the administrator and shared out-of-band, so it
    is never emailed. Best-effort delivery — :func:`send_branded_email` never
    raises, so a mail outage can't break staff creation.
    """
    paragraphs = [
        "An account has been created for you on the Bimaya staff console. "
        f"You can sign in with this email address: {user.email}.",
    ]
    labels = [label for label in (role_labels or []) if label]
    if labels:
        noun = "role" if len(labels) == 1 else "roles"
        paragraphs.append(
            f"You've been given the {_humanize_list(labels)} {noun}, which set "
            "what you can do in the console."
        )
    paragraphs.append(
        "Use the temporary password your administrator shared with you to sign "
        "in, then change it from your account settings."
    )
    send_branded_email(
        subject="Your Bimaya staff account is ready",
        to=user.email,
        heading="Your Bimaya staff account is ready",
        paragraphs=paragraphs,
        cta=("Sign in", "/login"),
    )


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record_audit(
    *,
    actor,
    action,
    module="",
    entity_type="",
    entity_id="",
    changes=None,
    reason="",
    request=None,
):
    """Write one :class:`~apps.staff.models.AuditLogEntry`.

    Best-effort: a logging failure must never break the business action it is
    recording, so any error is swallowed. ``entity_id`` is coerced to a string
    (ids are often ints). Returns the created entry, or ``None`` on failure.
    """
    try:
        return AuditLogEntry.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            actor_role=getattr(actor, "role", "") or "",
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id="" if entity_id in (None, "") else str(entity_id),
            changes=changes or {},
            reason=reason or "",
            ip_address=_client_ip(request),
        )
    except Exception:  # noqa: BLE001 — auditing is best-effort, never fatal
        return None
