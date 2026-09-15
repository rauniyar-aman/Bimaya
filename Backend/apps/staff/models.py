"""Persistent RBAC state: who holds which staff role, and the audit trail.

The role→permission *policy* lives in :mod:`apps.staff.rbac` (code). These two
tables hold only what must be data:

* :class:`StaffRoleAssignment` — the assignment of a coded role to a staff user,
  mirroring the provider-side :class:`apps.providers.models.ProviderMembership`.
* :class:`AuditLogEntry` — an append-only record of security-sensitive staff
  actions (spec §17). Never updated or deleted through the app.
"""

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel

from .rbac import StaffRole


class StaffRoleAssignment(TimeStampedModel):
    """Grants one coded :class:`~apps.staff.rbac.StaffRole` to a staff user.

    A user may hold several roles; their permissions are the union (see
    :func:`apps.staff.services.staff_permissions`). Assignments are managed by a
    System Owner — never self-service. Only platform ``ADMIN`` accounts are ever
    assigned a staff role.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_roles",
    )
    role = models.CharField(max_length=40, choices=StaffRole.choices)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_roles_granted",
        help_text="The staff member who assigned this role.",
    )

    class Meta(TimeStampedModel.Meta):
        ordering = ["user__email", "role"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"], name="unique_staff_user_role"
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.get_role_display()}"


class AuditLogEntry(TimeStampedModel):
    """An immutable record of a security-sensitive staff action (spec §17).

    Captures the actor, the role they held at the time, the permission/action
    used, the entity affected and any before/after values, so decisions like KYC
    approvals, provider approvals and financial changes are always traceable.
    The actor FK is nullable and ``SET_NULL`` so deactivating a staff account
    never erases the history they authored.
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    actor_role = models.CharField(
        max_length=40,
        blank=True,
        help_text="The actor's platform role snapshotted at action time.",
    )
    action = models.CharField(
        max_length=64, help_text="The permission/action used, e.g. 'kyc.approve'."
    )
    module = models.CharField(max_length=40, blank=True)
    entity_type = models.CharField(max_length=64, blank=True)
    entity_id = models.CharField(max_length=64, blank=True)
    changes = models.JSONField(
        default=dict, blank=True, help_text="Old/new values where relevant."
    )
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ["-created_at"]
        verbose_name = "audit log entry"
        verbose_name_plural = "audit log entries"
        indexes = [
            models.Index(fields=["action"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        who = self.actor.email if self.actor else "(deleted)"
        return f"{who} · {self.action} · {self.entity_type}#{self.entity_id}"
