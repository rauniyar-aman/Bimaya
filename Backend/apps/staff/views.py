"""Staff-management REST APIs (``/api/v1/admin/staff|roles|audit``).

The in-app console for internal-staff administration, built on the RBAC engine
in :mod:`apps.staff`. A System Owner creates staff accounts, assigns their coded
roles, and enables/disables them; the roles/permission matrix and the audit
trail are read-only here (the matrix is *code* — :mod:`apps.staff.rbac`).

Access is gated by :class:`~apps.staff.permissions.HasStaffPermission` exactly as
the rest of the admin panel is: the caller must be a platform administrator
holding the granular ``required_permission`` each view declares. Every
state-changing action is recorded to the audit log
(:func:`apps.staff.services.record_audit`).
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.response import Response

from .exceptions import StaffNotDisableable
from .models import AuditLogEntry, StaffRoleAssignment
from .permissions import HasStaffPermission
from .rbac import ALL_PERMS, ROLE_PERMISSIONS, Perm, StaffRole
from .serializers import (
    AuditLogEntrySerializer,
    StaffCreateSerializer,
    StaffMemberSerializer,
    StaffRolesSerializer,
)
from .services import (
    record_audit,
    send_staff_welcome_email,
    staff_permissions,
    staff_role_values,
)

User = get_user_model()

STAFF_TAG = ["staff"]

# Map of coded role value → human label, for building people-list rows.
_ROLE_LABELS = dict(StaffRole.choices)


class StaffBase:
    """Shared gate and helpers for the staff-management endpoints.

    Sets the same access policy every admin endpoint uses — a platform
    administrator holding the view's granular ``required_permission`` — and adds
    helpers for resolving staff accounts and shaping their people-list rows.
    """

    permission_classes = [HasStaffPermission]
    required_permission = None

    @staticmethod
    def staff_queryset():
        """Every internal-staff account (a platform ``ADMIN`` user)."""
        return User.objects.filter(role=User.Role.ADMIN)

    def get_staff(self, pk):
        """Resolve one staff account, or 404 for a non-staff id."""
        return get_object_or_404(self.staff_queryset(), pk=pk)

    @staticmethod
    def _staff_row(user):
        """A people-list row: the account plus its roles and resolved perms."""
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
            "roles": [
                {"value": value, "label": _ROLE_LABELS.get(value, value)}
                for value in sorted(staff_role_values(user))
            ],
            "permissions": sorted(staff_permissions(user)),
        }

    @staticmethod
    def _is_last_active_system_owner(user):
        """True when ``user`` is the only remaining *active* System Owner.

        Used to refuse actions — disabling the account, or stripping its
        System Owner role — that would leave nobody able to administer staff.
        """
        owner = StaffRole.SYSTEM_OWNER.value
        if not user.is_active or owner not in staff_role_values(user):
            return False
        others_exist = (
            StaffRoleAssignment.objects.filter(role=owner, user__is_active=True)
            .exclude(user=user)
            .exists()
        )
        return not others_exist


class StaffListCreateView(StaffBase, GenericAPIView):
    """List internal-staff accounts, or create one with a temporary password."""

    serializer_class = StaffCreateSerializer
    filterset_fields = ["is_active"]
    search_fields = ["email", "full_name"]

    def get_queryset(self):
        return self.staff_queryset().order_by("-date_joined")

    def initial(self, request, *args, **kwargs):
        # GET reads staff (staff.view); POST creates staff (staff.create). The
        # permission is checked in super().initial(), so decide it first.
        self.required_permission = (
            Perm.STAFF_CREATE if request.method == "POST" else Perm.STAFF_VIEW
        )
        return super().initial(request, *args, **kwargs)

    @extend_schema(
        tags=STAFF_TAG,
        summary="List internal-staff accounts",
        responses=StaffMemberSerializer(many=True),
    )
    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        rows = [self._staff_row(user) for user in page]
        return self.get_paginated_response(
            StaffMemberSerializer(rows, many=True).data
        )

    @extend_schema(
        tags=STAFF_TAG,
        summary="Create an internal-staff account",
        request=StaffCreateSerializer,
        responses=StaffMemberSerializer,
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        roles = list(dict.fromkeys(data["roles"]))  # dedupe, keep order
        with transaction.atomic():
            user = User.objects.create_user(
                email=data["email"],
                password=data["password"],
                full_name=data["full_name"],
                role=User.Role.ADMIN,
                is_verified=True,
            )
            for role in roles:
                StaffRoleAssignment.objects.create(
                    user=user, role=role, granted_by=request.user
                )
        record_audit(
            actor=request.user,
            action=Perm.STAFF_CREATE,
            module="staff",
            entity_type="User",
            entity_id=user.pk,
            changes={"email": [None, user.email], "roles": [[], roles]},
            request=request,
        )
        # Best-effort onboarding email — outside the transaction so a mail
        # outage can't roll back the account (send_branded_email never raises).
        send_staff_welcome_email(
            user, role_labels=[_ROLE_LABELS.get(role, role) for role in roles]
        )
        return Response(
            StaffMemberSerializer(self._staff_row(user)).data,
            status=status.HTTP_201_CREATED,
        )


class StaffDetailView(StaffBase, GenericAPIView):
    """Read one staff account with its roles and resolved permissions."""

    required_permission = Perm.STAFF_VIEW
    serializer_class = StaffMemberSerializer

    @extend_schema(tags=STAFF_TAG, summary="Retrieve a staff account")
    def get(self, request, pk):
        user = self.get_staff(pk)
        return Response(StaffMemberSerializer(self._staff_row(user)).data)


class StaffRolesView(StaffBase, GenericAPIView):
    """Replace a staff account's set of coded roles."""

    required_permission = Perm.PERMISSION_ASSIGN
    serializer_class = StaffRolesSerializer

    @extend_schema(
        tags=STAFF_TAG,
        summary="Set a staff account's roles",
        request=StaffRolesSerializer,
        responses=StaffMemberSerializer,
    )
    def patch(self, request, pk):
        user = self.get_staff(pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_roles = list(dict.fromkeys(serializer.validated_data["roles"]))
        old_roles = sorted(staff_role_values(user))
        # Refuse to strip the last active System Owner's owner role — that would
        # leave nobody able to administer staff (same lockout the disable guard
        # prevents).
        if (
            StaffRole.SYSTEM_OWNER.value not in new_roles
            and self._is_last_active_system_owner(user)
        ):
            raise ValidationError(
                {"roles": ["The last active System Owner must keep that role."]}
            )
        with transaction.atomic():
            StaffRoleAssignment.objects.filter(user=user).exclude(
                role__in=new_roles
            ).delete()
            for role in new_roles:
                StaffRoleAssignment.objects.get_or_create(
                    user=user, role=role, defaults={"granted_by": request.user}
                )
        record_audit(
            actor=request.user,
            action=Perm.PERMISSION_ASSIGN,
            module="staff",
            entity_type="User",
            entity_id=user.pk,
            changes={"roles": [old_roles, sorted(new_roles)]},
            request=request,
        )
        return Response(StaffMemberSerializer(self._staff_row(user)).data)


class StaffDisableView(StaffBase, GenericAPIView):
    """Disable a staff account so it can no longer sign in."""

    required_permission = Perm.STAFF_DEACTIVATE
    serializer_class = StaffMemberSerializer

    @extend_schema(
        tags=STAFF_TAG,
        summary="Disable a staff account",
        request=None,
        responses=StaffMemberSerializer,
    )
    def post(self, request, pk):
        user = self.get_staff(pk)
        if user == request.user:
            raise StaffNotDisableable("You cannot disable your own account.")
        if self._is_last_active_system_owner(user):
            raise StaffNotDisableable(
                "The last active System Owner cannot be disabled."
            )
        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])
            record_audit(
                actor=request.user,
                action=Perm.STAFF_DEACTIVATE,
                module="staff",
                entity_type="User",
                entity_id=user.pk,
                changes={"is_active": [True, False]},
                request=request,
            )
        return Response(StaffMemberSerializer(self._staff_row(user)).data)


class StaffEnableView(StaffBase, GenericAPIView):
    """Re-enable a disabled staff account."""

    required_permission = Perm.STAFF_ACTIVATE
    serializer_class = StaffMemberSerializer

    @extend_schema(
        tags=STAFF_TAG,
        summary="Enable a staff account",
        request=None,
        responses=StaffMemberSerializer,
    )
    def post(self, request, pk):
        user = self.get_staff(pk)
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
            record_audit(
                actor=request.user,
                action=Perm.STAFF_ACTIVATE,
                module="staff",
                entity_type="User",
                entity_id=user.pk,
                changes={"is_active": [False, True]},
                request=request,
            )
        return Response(StaffMemberSerializer(self._staff_row(user)).data)


class RolesCatalogView(StaffBase, GenericAPIView):
    """The read-only roles → permissions matrix (from code, not the database)."""

    required_permission = Perm.ROLE_VIEW

    @extend_schema(
        tags=STAFF_TAG,
        summary="List roles and their permissions",
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        roles = [
            {
                "value": value,
                "label": label,
                "permissions": sorted(ROLE_PERMISSIONS.get(value, frozenset())),
                "permission_count": len(ROLE_PERMISSIONS.get(value, frozenset())),
            }
            for value, label in StaffRole.choices
        ]
        return Response({"roles": roles, "permissions": sorted(ALL_PERMS)})


@extend_schema(tags=STAFF_TAG, summary="List audit-log entries")
class AuditLogListView(StaffBase, ListAPIView):
    """The append-only staff audit trail, paginated and filterable."""

    required_permission = Perm.AUDIT_LOG_VIEW
    serializer_class = AuditLogEntrySerializer
    filterset_fields = ["action", "module", "actor"]
    search_fields = ["action", "entity_type", "entity_id", "actor__email"]

    def get_queryset(self):
        return AuditLogEntry.objects.select_related("actor")
