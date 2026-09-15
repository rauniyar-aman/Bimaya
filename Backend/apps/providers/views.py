"""Provider-facing API endpoints (``/api/v1/provider/``).

The provider portal's own backend: a company manages its **own** profile, team,
analytics and KYC documents here. Every endpoint is gated by
:class:`~apps.providers.access.HasProviderPermission` — the caller must be a
verified provider account that resolves to a provider organisation and holds the
granular ``required_permission`` the view declares (owners hold everything; added
members hold only what their role grants, per :mod:`apps.providers.rbac`).

The acting organisation is always resolved from the signed-in user
(:func:`~apps.providers.access.provider_for`), never a URL id, so a provider can
only ever read and manage its own data. Platform administrators manage any
provider's team through the parallel admin-panel endpoints. State-changing
actions are recorded to the shared audit log
(:func:`apps.staff.services.record_audit`, modules ``provider.staff`` /
``provider.kyc``); there is no provider-facing audit screen (the log is not
organisation-scoped — platform-admin visibility only).
"""

import os

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.documents.models import ProviderKyc
from apps.documents.serializers import (
    ProviderKycSerializer,
    ProviderKycUploadSerializer,
)
from apps.staff.services import record_audit

from .access import HasProviderPermission, provider_for
from .analytics import build_provider_analytics
from .exceptions import (
    ProviderKycNotDeletable,
    ProviderMemberNotDisableable,
    ProviderProfileNotFound,
)
from .models import ProviderMembership
from .rbac import (
    ALL_PROVIDER_PERMS,
    OWNER,
    PROVIDER_ROLE_PERMISSIONS,
    ProviderPerm,
    ProviderRole,
    permissions_for,
)
from .serializers import (
    ProviderMemberCreateSerializer,
    ProviderMemberRoleSerializer,
    ProviderMemberSerializer,
    ProviderProfileSerializer,
)

User = get_user_model()

PROVIDER_TAG = ["provider"]

# Coded role value → human label, for building member-list rows. Includes the
# implicit OWNER sentinel alongside the five assignable roles.
_ROLE_LABELS = {OWNER: "Owner", **dict(ProviderRole.choices)}


@extend_schema(tags=PROVIDER_TAG, summary="Own provider profile")
class ProviderProfileView(GenericAPIView):
    """Retrieve or upsert the acting user's provider company profile.

    ``GET`` is the members' bootstrap read: it returns the organisation's profile
    (including ``my_role`` / ``my_permissions``) to any member, or 404
    (``provider_profile_missing``) when the owner has not created one yet — the
    frontend uses that to show the setup form. ``PUT``/``PATCH`` needs
    ``company.edit`` (owner and Company Admin): it creates the profile on first
    save and updates it thereafter, with the owning user taken from the request.
    """

    serializer_class = ProviderProfileSerializer
    permission_classes = [HasProviderPermission]
    # A not-yet-onboarded owner (no profile row, hence no resolvable role) may
    # still reach this endpoint — to create the profile, or receive the 404 the
    # setup form keys off.
    allow_onboarding = True

    def initial(self, request, *args, **kwargs):
        # Reading is open to any member; writing the company profile needs
        # company.edit. The permission is checked in super().initial(), so decide
        # it first.
        self.required_permission = (
            None if request.method == "GET" else ProviderPerm.COMPANY_EDIT
        )
        return super().initial(request, *args, **kwargs)

    def get_object(self):
        return provider_for(self.request.user)

    def get(self, request):
        provider = self.get_object()
        if provider is None:
            raise ProviderProfileNotFound()
        return Response(self.get_serializer(provider).data)

    def put(self, request):
        return self._upsert(request, partial=False)

    def patch(self, request):
        return self._upsert(request, partial=True)

    def _upsert(self, request, partial):
        provider = self.get_object()
        is_create = provider is None
        serializer = self.get_serializer(
            provider, data=request.data, partial=partial and not is_create
        )
        serializer.is_valid(raise_exception=True)
        # The owning account is set once, when the profile is first created. On an
        # update we must NOT reassign it — a Company Admin (who also holds
        # ``company.edit``) editing the profile would otherwise become the owner.
        if is_create:
            serializer.save(user=request.user)
        else:
            serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if is_create else status.HTTP_200_OK,
        )


@extend_schema(
    tags=["analytics"],
    summary="Own provider analytics",
    responses=OpenApiTypes.OBJECT,
)
class ProviderAnalyticsView(GenericAPIView):
    """Analytics scoped to the signed-in provider's own policies.

    Totals, status breakdowns and a recent monthly trend, all filtered to the
    provider's book of business. Needs ``analytics.view`` (owner, Company Admin,
    Policy Manager, Sales, Finance). 404 (``provider_profile_missing``) when the
    provider has not created a profile yet, mirroring the profile endpoint.
    """

    permission_classes = [HasProviderPermission]
    required_permission = ProviderPerm.ANALYTICS_VIEW
    allow_onboarding = True

    def get(self, request):
        provider = provider_for(request.user)
        if provider is None:
            raise ProviderProfileNotFound()
        return Response(build_provider_analytics(provider))


# --- Team (self-service member management) ----------------------------------


class ProviderMemberBase(GenericAPIView):
    """Shared gate and helpers for a provider managing *its own* team.

    The acting organisation is resolved from the signed-in user
    (:func:`provider_for`) — never a URL id — so a provider can only ever see and
    manage its own members. The owner (``Provider.user``) is surfaced as a
    synthetic row (``membership_id`` null, role ``OWNER``); everyone else is a
    :class:`~apps.providers.models.ProviderMembership`. Memberships are always
    resolved scoped to the caller's organisation, so an id from another company
    404s. Staff endpoints do not set ``allow_onboarding`` — a provider must have a
    profile (and therefore a resolvable role) before it can manage a team.
    """

    permission_classes = [HasProviderPermission]
    required_permission = None

    def get_org(self):
        # The gate guarantees a resolvable organisation before any handler runs.
        return provider_for(self.request.user)

    def get_membership(self, provider):
        return get_object_or_404(
            provider.memberships.select_related("user"), pk=self.kwargs["pk"]
        )

    @staticmethod
    def _role_ref(value):
        return {"value": value, "label": _ROLE_LABELS.get(value, value)}

    @classmethod
    def _owner_row(cls, provider):
        owner = provider.user
        return {
            "user_id": owner.id,
            "membership_id": None,
            "email": owner.email,
            "full_name": owner.full_name,
            "role": cls._role_ref(OWNER),
            "is_active": owner.is_active,
            "date_joined": owner.date_joined,
            "permissions": sorted(permissions_for([OWNER])),
        }

    @classmethod
    def _membership_row(cls, membership):
        user = membership.user
        return {
            "user_id": user.id,
            "membership_id": membership.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": cls._role_ref(membership.role),
            "is_active": user.is_active,
            "date_joined": user.date_joined,
            "permissions": sorted(permissions_for([membership.role])),
        }

    def _member_rows(self, provider):
        rows = [self._owner_row(provider)]
        rows.extend(
            self._membership_row(membership)
            for membership in provider.memberships.select_related("user").all()
        )
        return rows


class ProviderMemberListCreateView(ProviderMemberBase):
    """List your organisation's team, or add a member to it."""

    serializer_class = ProviderMemberCreateSerializer

    def initial(self, request, *args, **kwargs):
        # Reading the team needs staff.view; adding a member needs staff.manage.
        # The permission is checked in super().initial(), so decide it first.
        self.required_permission = (
            ProviderPerm.STAFF_MANAGE
            if request.method == "POST"
            else ProviderPerm.STAFF_VIEW
        )
        return super().initial(request, *args, **kwargs)

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="List your organisation's team",
        responses=ProviderMemberSerializer(many=True),
    )
    def get(self, request):
        provider = self.get_org()
        rows = self._member_rows(provider)
        return Response(ProviderMemberSerializer(rows, many=True).data)

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="Add a member to your organisation",
        request=ProviderMemberCreateSerializer,
        responses=ProviderMemberSerializer,
    )
    def post(self, request):
        provider = self.get_org()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            user = User.objects.create_user(
                email=data["email"],
                password=data["password"],
                full_name=data["full_name"],
                role=User.Role.PROVIDER,
                is_verified=True,
            )
            membership = ProviderMembership.objects.create(
                provider=provider, user=user, role=data["role"]
            )
        record_audit(
            actor=request.user,
            action=ProviderPerm.STAFF_MANAGE,
            module="provider.staff",
            entity_type="ProviderMembership",
            entity_id=membership.pk,
            changes={
                "added_member": [None, user.email],
                "role": [None, data["role"]],
            },
            request=request,
        )
        return Response(
            ProviderMemberSerializer(self._membership_row(membership)).data,
            status=status.HTTP_201_CREATED,
        )


class ProviderMemberDetailView(ProviderMemberBase):
    """Read one team member with their role and resolved permissions."""

    required_permission = ProviderPerm.STAFF_VIEW
    serializer_class = ProviderMemberSerializer

    @extend_schema(tags=PROVIDER_TAG, summary="Retrieve a team member")
    def get(self, request, pk):
        provider = self.get_org()
        membership = self.get_membership(provider)
        return Response(
            ProviderMemberSerializer(self._membership_row(membership)).data
        )


class ProviderMemberRoleView(ProviderMemberBase):
    """Change an existing member's assignable role."""

    required_permission = ProviderPerm.STAFF_MANAGE
    serializer_class = ProviderMemberRoleSerializer

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="Change a member's role",
        request=ProviderMemberRoleSerializer,
        responses=ProviderMemberSerializer,
    )
    def patch(self, request, pk):
        provider = self.get_org()
        membership = self.get_membership(provider)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]
        old_role = membership.role
        if old_role != new_role:
            membership.role = new_role
            membership.save(update_fields=["role", "updated_at"])
            record_audit(
                actor=request.user,
                action=ProviderPerm.STAFF_MANAGE,
                module="provider.staff",
                entity_type="ProviderMembership",
                entity_id=membership.pk,
                changes={"role": [old_role, new_role]},
                request=request,
            )
        return Response(
            ProviderMemberSerializer(self._membership_row(membership)).data
        )


class ProviderMemberDisableView(ProviderMemberBase):
    """Disable a team member so they can no longer sign in."""

    required_permission = ProviderPerm.STAFF_MANAGE
    serializer_class = ProviderMemberSerializer

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="Disable a team member",
        request=None,
        responses=ProviderMemberSerializer,
    )
    def post(self, request, pk):
        provider = self.get_org()
        membership = self.get_membership(provider)
        user = membership.user
        # The owner is never a membership row, so cannot be targeted here. Guard
        # only against a Company Admin disabling their own account.
        if user == request.user:
            raise ProviderMemberNotDisableable(
                "You cannot disable your own account."
            )
        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])
            record_audit(
                actor=request.user,
                action=ProviderPerm.STAFF_MANAGE,
                module="provider.staff",
                entity_type="ProviderMembership",
                entity_id=membership.pk,
                changes={"is_active": [True, False]},
                request=request,
            )
        return Response(
            ProviderMemberSerializer(self._membership_row(membership)).data
        )


class ProviderMemberEnableView(ProviderMemberBase):
    """Re-enable a disabled team member."""

    required_permission = ProviderPerm.STAFF_MANAGE
    serializer_class = ProviderMemberSerializer

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="Enable a team member",
        request=None,
        responses=ProviderMemberSerializer,
    )
    def post(self, request, pk):
        provider = self.get_org()
        membership = self.get_membership(provider)
        user = membership.user
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
            record_audit(
                actor=request.user,
                action=ProviderPerm.STAFF_MANAGE,
                module="provider.staff",
                entity_type="ProviderMembership",
                entity_id=membership.pk,
                changes={"is_active": [False, True]},
                request=request,
            )
        return Response(
            ProviderMemberSerializer(self._membership_row(membership)).data
        )


class ProviderRolesCatalogView(ProviderMemberBase):
    """The read-only assignable-roles → permissions matrix (from code).

    Powers the role picker in the provider portal. Gated by ``staff.view`` — the
    same permission that lets a member see the team. The implicit ``OWNER`` role
    is not listed (it is not assignable); every entry here can be handed to a
    member.
    """

    required_permission = ProviderPerm.STAFF_VIEW

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="List assignable roles and their permissions",
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        roles = [
            {
                "value": value,
                "label": label,
                "permissions": sorted(
                    PROVIDER_ROLE_PERMISSIONS.get(value, frozenset())
                ),
                "permission_count": len(
                    PROVIDER_ROLE_PERMISSIONS.get(value, frozenset())
                ),
            }
            for value, label in ProviderRole.choices
        ]
        return Response({"roles": roles, "permissions": sorted(ALL_PROVIDER_PERMS)})


# --- KYC documents ----------------------------------------------------------


class ProviderKycBase(GenericAPIView):
    """Shared gate and org-scoping for a provider's own KYC documents.

    Documents are always resolved scoped to the caller's organisation, so an id
    from another company 404s. The files themselves are confidential company
    paperwork under the git-ignored ``MEDIA_ROOT`` and are streamed only through
    the authenticated download endpoint below — never a raw media URL.
    """

    permission_classes = [HasProviderPermission]
    serializer_class = ProviderKycSerializer
    required_permission = ProviderPerm.PROVIDER_KYC_VIEW

    def get_org(self):
        return provider_for(self.request.user)

    def get_document(self, provider):
        return get_object_or_404(
            ProviderKyc.objects.filter(provider=provider), pk=self.kwargs["pk"]
        )


class ProviderKycListCreateView(ProviderKycBase):
    """List your organisation's KYC documents, or upload a new one."""

    parser_classes = [MultiPartParser, FormParser]

    def initial(self, request, *args, **kwargs):
        # Listing needs provider_kyc.view; uploading needs provider_kyc.upload.
        self.required_permission = (
            ProviderPerm.PROVIDER_KYC_UPLOAD
            if request.method == "POST"
            else ProviderPerm.PROVIDER_KYC_VIEW
        )
        return super().initial(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProviderKycUploadSerializer
        return ProviderKycSerializer

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="List your organisation's KYC documents",
        responses=ProviderKycSerializer(many=True),
    )
    def get(self, request):
        provider = self.get_org()
        documents = provider.kyc_documents.select_related("uploaded_by").order_by(
            "-created_at"
        )
        return Response(ProviderKycSerializer(documents, many=True).data)

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="Upload a KYC document",
        request=ProviderKycUploadSerializer,
        responses=ProviderKycSerializer,
    )
    def post(self, request):
        provider = self.get_org()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save(
            provider=provider,
            uploaded_by=request.user,
            status=ProviderKyc.Status.PENDING,
        )
        record_audit(
            actor=request.user,
            action=ProviderPerm.PROVIDER_KYC_UPLOAD,
            module="provider.kyc",
            entity_type="ProviderKyc",
            entity_id=document.pk,
            changes={"document_type": [None, document.document_type]},
            request=request,
        )
        return Response(
            ProviderKycSerializer(document).data, status=status.HTTP_201_CREATED
        )


class ProviderKycDeleteView(ProviderKycBase):
    """Remove one of your organisation's KYC documents while still pending."""

    required_permission = ProviderPerm.PROVIDER_KYC_UPLOAD

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="Remove a pending KYC document",
        request=None,
        responses={204: None},
    )
    def delete(self, request, pk):
        provider = self.get_org()
        document = self.get_document(provider)
        # Once an administrator has verified or rejected a document it is part of
        # the review trail and is no longer the provider's to remove.
        if document.status != ProviderKyc.Status.PENDING:
            raise ProviderKycNotDeletable()
        entity_id = document.pk
        document_type = document.document_type
        document.file.delete(save=False)
        document.delete()
        record_audit(
            actor=request.user,
            action=ProviderPerm.PROVIDER_KYC_UPLOAD,
            module="provider.kyc",
            entity_type="ProviderKyc",
            entity_id=entity_id,
            changes={"deleted_document": [document_type, None]},
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProviderKycDownloadView(ProviderKycBase):
    """Stream one of your organisation's KYC document files.

    Confidential company paperwork is only ever served through this
    authenticated, org-scoped endpoint (``provider_kyc.view``) — never a raw
    media URL. Served as an attachment.
    """

    required_permission = ProviderPerm.PROVIDER_KYC_VIEW

    @extend_schema(
        tags=PROVIDER_TAG,
        summary="Download a KYC document file",
        responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request, pk):
        provider = self.get_org()
        document = self.get_document(provider)
        if not document.file:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=os.path.basename(document.file.name),
        )
