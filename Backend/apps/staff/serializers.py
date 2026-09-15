"""Staff-management serializers (``/api/v1/admin/staff|roles|audit``).

Thin admin-facing shapes for the in-app staff console: listing and creating
staff accounts, assigning their coded roles, and reading the audit trail. The
role→permission *policy* is code (:mod:`apps.staff.rbac`); these serializers only
move assignments and audit rows in and out.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import AuditLogEntry
from .rbac import StaffRole

User = get_user_model()


def _role_list_field():
    """A required, non-empty list of coded staff-role values."""
    return serializers.ListField(
        child=serializers.ChoiceField(choices=StaffRole.choices),
        allow_empty=False,
    )


class StaffRoleRefSerializer(serializers.Serializer):
    """A coded staff role rendered as ``{value, label}`` for the UI."""

    value = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)


class StaffMemberSerializer(serializers.Serializer):
    """One internal-staff account with its roles and resolved permissions.

    Built from a hand-assembled dict (see
    :meth:`apps.staff.views.StaffBase._staff_row`) so the roles and the union of
    permissions they grant can be attached without extra queries per row.
    """

    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True, allow_blank=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    roles = StaffRoleRefSerializer(many=True, read_only=True)
    permissions = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )


class StaffCreateSerializer(serializers.Serializer):
    """Admin input to create an internal-staff account.

    Creates a verified platform-admin account with a temporary password and
    assigns one or more coded roles; the person then signs in with the normal
    login + OTP and changes the password. Mirrors provider-member creation.
    """

    email = serializers.EmailField()
    full_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    password = serializers.CharField(
        write_only=True, min_length=8, trim_whitespace=False
    )
    roles = _role_list_field()

    def validate_email(self, value):
        value = value.strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class StaffRolesSerializer(serializers.Serializer):
    """Admin input to replace a staff member's set of coded roles."""

    roles = _role_list_field()


class AuditLogEntrySerializer(serializers.ModelSerializer):
    """A single append-only audit-trail record, read-only."""

    actor_email = serializers.EmailField(
        source="actor.email", read_only=True, allow_null=True
    )

    class Meta:
        model = AuditLogEntry
        fields = (
            "id",
            "actor_email",
            "actor_role",
            "action",
            "module",
            "entity_type",
            "entity_id",
            "changes",
            "reason",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields
