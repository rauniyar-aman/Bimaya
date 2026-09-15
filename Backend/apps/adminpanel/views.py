"""Admin-panel REST APIs (``/api/v1/admin/...``).

A branded in-app admin area is built on these; the Django admin remains as the
low-level fallback. Access is gated by
:class:`~apps.staff.permissions.HasStaffPermission` — the caller must be a
platform administrator holding the granular ``required_permission`` each view
declares. Sensitive, state-changing actions are recorded to the audit log
(:func:`apps.staff.services.record_audit`). Actions that
change state reuse the same model methods the Django admin uses
(``CustomerKyc.mark_verified``/``mark_rejected``, ``PolicyPurchase.forward_to_provider``)
and dispatch notifications through :mod:`apps.notifications.services`.
"""

import os

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from apps.documents.models import CustomerKyc, ProviderKyc
from apps.documents.serializers import CustomerKycSerializer, ProviderKycSerializer
from apps.notifications import services as notifications
from apps.policies.models import Policy
from apps.providers.models import Provider, ProviderMembership
from apps.providers.rbac import OWNER
from apps.purchases.models import PolicyPurchase, ProviderPayout
from apps.staff.permissions import HasStaffPermission
from apps.staff.rbac import Perm
from apps.staff.services import record_audit

from .analytics import build_admin_analytics
from .exceptions import (
    PolicyNotActionable,
    PurchaseNotForwardable,
    UserNotSuspendable,
)
from .reports import csv_response, local_date, money, yes_no
from .serializers import (
    AdminKycSerializer,
    AdminPayoutSerializer,
    AdminPolicySerializer,
    AdminProviderCommissionSerializer,
    AdminProviderSerializer,
    AdminPurchaseSerializer,
    AdminUserDetailSerializer,
    AdminUserSerializer,
    ProviderMemberCreateSerializer,
    ProviderMemberRoleSerializer,
    ProviderMemberSerializer,
    RejectNoteSerializer,
)

User = get_user_model()

ADMIN_TAG = ["admin"]


class AdminBase:
    """Shared configuration for every admin-panel endpoint.

    Access is gated by :class:`~apps.staff.permissions.HasStaffPermission`:
    the caller must be a platform administrator *and* hold the granular
    ``required_permission`` the view declares. A view that declares none stays
    administrator-only (never accidentally public).
    """

    permission_classes = [HasStaffPermission]
    required_permission = None


class CsvExportMixin:
    """Turn an admin list view into a full CSV download.

    Reuses the list view's queryset, filters and search (through
    ``filter_queryset``) so an export always matches what the table shows, but
    skips pagination — a report covers every matching row. Subclasses set
    ``report_basename`` and ``report_columns``, a list of ``(header, value)``
    pairs where ``value`` is a callable taking the row object.
    """

    report_basename = "export"
    report_columns = []

    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        header = [column[0] for column in self.report_columns]
        rows = (
            [value(obj) for _, value in self.report_columns] for obj in queryset
        )
        return csv_response(self.report_basename, header, rows)


# --- Providers --------------------------------------------------------------


@extend_schema(tags=ADMIN_TAG, summary="List providers")
class AdminProviderListView(AdminBase, ListAPIView):
    required_permission = Perm.PROVIDER_VIEW
    serializer_class = AdminProviderSerializer
    filterset_fields = ["is_approved", "kyc_status"]
    search_fields = ["company_name", "user__email"]

    def get_queryset(self):
        return (
            Provider.objects.select_related("user")
            .annotate(policy_count=Count("policies"))
            .order_by("company_name")
        )


@extend_schema(tags=ADMIN_TAG, summary="Retrieve a provider")
class AdminProviderDetailView(AdminBase, RetrieveAPIView):
    required_permission = Perm.PROVIDER_VIEW
    serializer_class = AdminProviderSerializer

    def get_queryset(self):
        return Provider.objects.select_related("user").annotate(
            policy_count=Count("policies")
        )


@extend_schema(
    tags=ADMIN_TAG,
    summary="Approve a provider",
    request=None,
    responses=AdminProviderSerializer,
)
class AdminProviderApproveView(AdminBase, GenericAPIView):
    required_permission = Perm.PROVIDER_APPROVE
    serializer_class = AdminProviderSerializer

    def post(self, request, pk):
        provider = get_object_or_404(Provider, pk=pk)
        if not provider.is_approved:
            provider.is_approved = True
            provider.save(update_fields=["is_approved", "updated_at"])
            notifications.notify_provider_approved(provider)
            record_audit(
                actor=request.user,
                action=Perm.PROVIDER_APPROVE,
                module="provider",
                entity_type="Provider",
                entity_id=provider.pk,
                changes={"is_approved": [False, True]},
                request=request,
            )
        return Response(self._serialize(provider), status=status.HTTP_200_OK)

    @staticmethod
    def _serialize(provider):
        provider = (
            Provider.objects.select_related("user")
            .annotate(policy_count=Count("policies"))
            .get(pk=provider.pk)
        )
        return AdminProviderSerializer(provider).data


@extend_schema(
    tags=ADMIN_TAG,
    summary="Revoke a provider's approval",
    request=None,
    responses=AdminProviderSerializer,
)
class AdminProviderRevokeView(AdminBase, GenericAPIView):
    required_permission = Perm.PROVIDER_SUSPEND
    serializer_class = AdminProviderSerializer

    def post(self, request, pk):
        provider = get_object_or_404(Provider, pk=pk)
        if provider.is_approved:
            provider.is_approved = False
            provider.save(update_fields=["is_approved", "updated_at"])
            record_audit(
                actor=request.user,
                action=Perm.PROVIDER_SUSPEND,
                module="provider",
                entity_type="Provider",
                entity_id=provider.pk,
                changes={"is_approved": [True, False]},
                request=request,
            )
        return Response(
            AdminProviderApproveView._serialize(provider), status=status.HTTP_200_OK
        )


@extend_schema(
    tags=ADMIN_TAG,
    summary="Set a provider's commission rate",
    request=AdminProviderCommissionSerializer,
    responses=AdminProviderSerializer,
)
class AdminProviderSetCommissionView(AdminBase, GenericAPIView):
    """Set the platform commission percent charged on this provider's sales.

    Only the rate applied to *future* issuances changes; existing payouts keep
    the rate snapshotted when they were created.
    """

    required_permission = Perm.COMMISSION_MANAGE
    serializer_class = AdminProviderCommissionSerializer

    def post(self, request, pk):
        provider = get_object_or_404(Provider, pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous = provider.commission_rate
        provider.commission_rate = serializer.validated_data["commission_rate"]
        provider.save(update_fields=["commission_rate", "updated_at"])
        record_audit(
            actor=request.user,
            action=Perm.COMMISSION_MANAGE,
            module="commission",
            entity_type="Provider",
            entity_id=provider.pk,
            changes={"commission_rate": [str(previous), str(provider.commission_rate)]},
            request=request,
        )
        return Response(
            AdminProviderApproveView._serialize(provider), status=status.HTTP_200_OK
        )


# --- Provider team members --------------------------------------------------


class AdminProviderMemberBase(AdminBase):
    """Shared helpers for managing a provider organisation's staff and viewers.

    The organisation owner is ``Provider.user`` (role ``OWNER``) and is not a
    membership row; everyone else is a
    :class:`~apps.providers.models.ProviderMembership`. Memberships are always
    resolved scoped to their provider, so an id from another organisation 404s.
    """

    def get_provider(self):
        return get_object_or_404(
            Provider.objects.select_related("user"), pk=self.kwargs["pk"]
        )

    def get_membership(self, provider):
        return get_object_or_404(
            provider.memberships.select_related("user"),
            pk=self.kwargs["membership_pk"],
        )

    @staticmethod
    def _membership_row(membership):
        user = membership.user
        return {
            "user_id": user.id,
            "membership_id": membership.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": membership.role,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
        }

    def _member_rows(self, provider):
        owner = provider.user
        rows = [
            {
                "user_id": owner.id,
                "membership_id": None,
                "email": owner.email,
                "full_name": owner.full_name,
                "role": OWNER,
                "is_active": owner.is_active,
                "date_joined": owner.date_joined,
            }
        ]
        rows.extend(
            self._membership_row(membership)
            for membership in provider.memberships.select_related("user").all()
        )
        return rows


class AdminProviderMemberListCreateView(AdminProviderMemberBase, GenericAPIView):
    """List a provider organisation's team, or add a staff/viewer to it."""

    required_permission = Perm.PROVIDER_EDIT
    serializer_class = ProviderMemberCreateSerializer

    @extend_schema(
        tags=ADMIN_TAG,
        summary="List a provider's team members",
        responses=ProviderMemberSerializer(many=True),
    )
    def get(self, request, pk):
        provider = self.get_provider()
        rows = self._member_rows(provider)
        return Response(ProviderMemberSerializer(rows, many=True).data)

    @extend_schema(
        tags=ADMIN_TAG,
        summary="Add a staff/viewer to a provider",
        request=ProviderMemberCreateSerializer,
        responses=ProviderMemberSerializer,
    )
    def post(self, request, pk):
        provider = self.get_provider()
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
            action=Perm.PROVIDER_EDIT,
            module="provider",
            entity_type="ProviderMembership",
            entity_id=membership.pk,
            changes={"added_member": [None, user.email], "role": [None, data["role"]]},
            request=request,
        )
        return Response(
            ProviderMemberSerializer(self._membership_row(membership)).data,
            status=status.HTTP_201_CREATED,
        )


class AdminProviderMemberDetailView(AdminProviderMemberBase, GenericAPIView):
    """Change a member's role, or remove them from the organisation."""

    required_permission = Perm.PROVIDER_EDIT
    serializer_class = ProviderMemberRoleSerializer

    @extend_schema(
        tags=ADMIN_TAG,
        summary="Change a member's role",
        request=ProviderMemberRoleSerializer,
        responses=ProviderMemberSerializer,
    )
    def patch(self, request, pk, membership_pk):
        provider = self.get_provider()
        membership = self.get_membership(provider)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_role = serializer.validated_data["role"]
        if membership.role != new_role:
            membership.role = new_role
            membership.save(update_fields=["role", "updated_at"])
        return Response(
            ProviderMemberSerializer(self._membership_row(membership)).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=ADMIN_TAG,
        summary="Remove a member from the organisation",
        request=None,
        responses={204: None},
    )
    def delete(self, request, pk, membership_pk):
        provider = self.get_provider()
        membership = self.get_membership(provider)
        user = membership.user
        membership.delete()
        # The account existed only to staff this organisation; deactivate it so
        # it can no longer sign in. It is not deleted, which preserves the rows
        # it authored (e.g. claim-thread messages).
        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


# --- Provider KYC documents -------------------------------------------------


class AdminProviderKycBase(AdminBase):
    """Shared gate and scoping for reviewing a provider's KYC documents.

    Backs :data:`~apps.staff.rbac.Perm.PROVIDER_KYC_REVIEW`. Documents are always
    resolved scoped to the provider named in the URL, so a document id from
    another organisation 404s. The files are confidential company paperwork under
    the git-ignored ``MEDIA_ROOT`` and are served only through the authenticated
    download endpoint below — never a raw media URL.
    """

    required_permission = Perm.PROVIDER_KYC_REVIEW

    def get_provider(self):
        return get_object_or_404(Provider, pk=self.kwargs["pk"])

    def get_document(self):
        return get_object_or_404(
            ProviderKyc.objects.select_related("provider", "uploaded_by"),
            pk=self.kwargs["document_pk"],
            provider_id=self.kwargs["pk"],
        )


@extend_schema(tags=ADMIN_TAG, summary="List a provider's KYC documents")
class AdminProviderKycListView(AdminProviderKycBase, GenericAPIView):
    serializer_class = ProviderKycSerializer

    def get(self, request, pk):
        provider = self.get_provider()
        documents = provider.kyc_documents.select_related("uploaded_by").order_by(
            "-created_at"
        )
        return Response(ProviderKycSerializer(documents, many=True).data)


class AdminProviderKycDocumentView(AdminProviderKycBase, GenericAPIView):
    """Stream a provider KYC document file to an administrator.

    Confidential company paperwork, served only through this authenticated,
    admin-gated endpoint — never a raw media URL. The access is recorded.
    """

    @extend_schema(
        tags=ADMIN_TAG,
        summary="Download a provider KYC document file",
        responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request, pk, document_pk):
        document = self.get_document()
        if not document.file:
            return Response(status=status.HTTP_404_NOT_FOUND)
        record_audit(
            actor=request.user,
            action=Perm.PROVIDER_KYC_REVIEW,
            module="provider.kyc",
            entity_type="ProviderKyc",
            entity_id=document.pk,
            changes={"downloaded": document.document_type},
            request=request,
        )
        return FileResponse(
            document.file.open("rb"),
            as_attachment=True,
            filename=os.path.basename(document.file.name),
        )


@extend_schema(
    tags=ADMIN_TAG,
    summary="Verify a provider KYC document",
    request=None,
    responses=ProviderKycSerializer,
)
class AdminProviderKycVerifyView(AdminProviderKycBase, GenericAPIView):
    serializer_class = ProviderKycSerializer

    def post(self, request, pk, document_pk):
        document = self.get_document()
        document.mark_verified(reviewer=request.user)
        record_audit(
            actor=request.user,
            action=Perm.PROVIDER_KYC_REVIEW,
            module="provider.kyc",
            entity_type="ProviderKyc",
            entity_id=document.pk,
            changes={"status": [None, document.status]},
            request=request,
        )
        return Response(ProviderKycSerializer(document).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Reject a provider KYC document",
    request=RejectNoteSerializer,
    responses=ProviderKycSerializer,
)
class AdminProviderKycRejectView(AdminProviderKycBase, GenericAPIView):
    serializer_class = RejectNoteSerializer

    def post(self, request, pk, document_pk):
        document = self.get_document()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document.mark_rejected(serializer.validated_data["note"], reviewer=request.user)
        record_audit(
            actor=request.user,
            action=Perm.PROVIDER_KYC_REVIEW,
            module="provider.kyc",
            entity_type="ProviderKyc",
            entity_id=document.pk,
            changes={"status": [None, document.status]},
            reason=serializer.validated_data["note"],
            request=request,
        )
        return Response(ProviderKycSerializer(document).data, status=status.HTTP_200_OK)


# --- Customer KYC -----------------------------------------------------------


class AdminKycBase(AdminBase):
    # Sensitive by default: reading KYC needs the KYC view permission. The
    # decision endpoints below narrow this to approve/reject.
    required_permission = Perm.KYC_VIEW

    def get_queryset(self):
        return CustomerKyc.objects.select_related("customer").order_by("-created_at")


@extend_schema(tags=ADMIN_TAG, summary="List KYC records")
class AdminKycListView(AdminKycBase, ListAPIView):
    serializer_class = AdminKycSerializer
    filterset_fields = ["status", "is_self"]
    search_fields = ["full_name", "customer__email", "document_number"]


@extend_schema(tags=ADMIN_TAG, summary="Retrieve a KYC record")
class AdminKycDetailView(AdminKycBase, RetrieveAPIView):
    serializer_class = AdminKycSerializer


class AdminKycDocumentView(AdminKycBase, GenericAPIView):
    """Stream a KYC document image to an administrator.

    KYC images are PII kept under the git-ignored ``MEDIA_ROOT`` and are only
    ever served through this authenticated, admin-gated endpoint — never a raw
    media URL. ``side`` is ``front`` or ``back``.
    """

    required_permission = Perm.KYC_DOCUMENT_VIEW
    side = "front"

    @extend_schema(
        tags=ADMIN_TAG,
        summary="Download a KYC document image",
        responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request, pk):
        kyc = get_object_or_404(self.get_queryset(), pk=pk)
        image = kyc.document_front if self.side == "front" else kyc.document_back
        if not image:
            return Response(status=status.HTTP_404_NOT_FOUND)
        # Viewing identity documents is PII access — record who looked at what.
        record_audit(
            actor=request.user,
            action=Perm.KYC_DOCUMENT_VIEW,
            module="kyc",
            entity_type="CustomerKyc",
            entity_id=kyc.pk,
            changes={"side": self.side},
            request=request,
        )
        return FileResponse(image.open("rb"))


@extend_schema(
    tags=ADMIN_TAG,
    summary="Verify a KYC record",
    request=None,
    responses=CustomerKycSerializer,
)
class AdminKycVerifyView(AdminKycBase, GenericAPIView):
    required_permission = Perm.KYC_APPROVE
    serializer_class = CustomerKycSerializer

    def post(self, request, pk):
        kyc = get_object_or_404(CustomerKyc, pk=pk)
        kyc.mark_verified()
        notifications.notify_kyc_verified(kyc)
        record_audit(
            actor=request.user,
            action=Perm.KYC_APPROVE,
            module="kyc",
            entity_type="CustomerKyc",
            entity_id=kyc.pk,
            changes={"status": [None, kyc.status]},
            request=request,
        )
        return Response(CustomerKycSerializer(kyc).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Reject a KYC record",
    request=RejectNoteSerializer,
    responses=CustomerKycSerializer,
)
class AdminKycRejectView(AdminKycBase, GenericAPIView):
    required_permission = Perm.KYC_REJECT
    serializer_class = RejectNoteSerializer

    def post(self, request, pk):
        kyc = get_object_or_404(CustomerKyc, pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kyc.mark_rejected(serializer.validated_data["note"])
        notifications.notify_kyc_rejected(kyc)
        record_audit(
            actor=request.user,
            action=Perm.KYC_REJECT,
            module="kyc",
            entity_type="CustomerKyc",
            entity_id=kyc.pk,
            changes={"status": [None, kyc.status]},
            reason=serializer.validated_data["note"],
            request=request,
        )
        return Response(CustomerKycSerializer(kyc).data, status=status.HTTP_200_OK)


# --- Purchases --------------------------------------------------------------


class AdminPurchaseBase(AdminBase):
    serializer_class = AdminPurchaseSerializer

    def get_queryset(self):
        return PolicyPurchase.objects.select_related(
            "customer", "policy", "policy__provider", "policy__category", "kyc"
        ).order_by("-created_at")


@extend_schema(tags=ADMIN_TAG, summary="List purchases")
class AdminPurchaseListView(AdminPurchaseBase, ListAPIView):
    required_permission = Perm.PURCHASE_VIEW
    filterset_fields = ["status"]
    search_fields = ["customer__email", "policy__name", "policy_number"]


@extend_schema(
    tags=ADMIN_TAG,
    summary="Verify KYC + payment and forward to the provider",
    request=None,
    responses=AdminPurchaseSerializer,
)
class AdminPurchaseForwardView(AdminPurchaseBase, GenericAPIView):
    required_permission = Perm.PURCHASE_MANAGE

    def post(self, request, pk):
        purchase = get_object_or_404(self.get_queryset(), pk=pk)
        if purchase.status != PolicyPurchase.Status.PAID:
            raise PurchaseNotForwardable()
        if purchase.kyc is None or not purchase.kyc.is_verified:
            raise PurchaseNotForwardable(
                "The customer's KYC must be verified before forwarding."
            )
        purchase.forward_to_provider()
        notifications.notify_purchase_forwarded(purchase)
        record_audit(
            actor=request.user,
            action=Perm.PURCHASE_MANAGE,
            module="purchase",
            entity_type="PolicyPurchase",
            entity_id=purchase.pk,
            changes={"status": [PolicyPurchase.Status.PAID, purchase.status]},
            request=request,
        )
        return Response(
            AdminPurchaseSerializer(purchase).data, status=status.HTTP_200_OK
        )


# --- Provider payouts -------------------------------------------------------


@extend_schema(tags=ADMIN_TAG, summary="List provider payouts")
class AdminPayoutListView(AdminBase, ListAPIView):
    required_permission = Perm.SETTLEMENT_VIEW
    serializer_class = AdminPayoutSerializer
    filterset_fields = ["status", "provider"]
    search_fields = [
        "provider__company_name",
        "purchase__policy__name",
        "purchase__policy_number",
    ]

    def get_queryset(self):
        return ProviderPayout.objects.select_related(
            "provider", "purchase", "purchase__policy"
        ).order_by("-created_at")


# --- Users ------------------------------------------------------------------


@extend_schema(tags=ADMIN_TAG, summary="List users")
class AdminUserListView(AdminBase, ListAPIView):
    required_permission = Perm.CUSTOMER_VIEW
    serializer_class = AdminUserSerializer
    filterset_fields = ["role", "is_verified", "is_active"]
    search_fields = ["email", "full_name", "phone"]

    def get_queryset(self):
        return User.objects.all().order_by("-date_joined")


@extend_schema(tags=ADMIN_TAG, summary="Retrieve a user with activity counts")
class AdminUserDetailView(AdminBase, RetrieveAPIView):
    required_permission = Perm.CUSTOMER_VIEW
    serializer_class = AdminUserDetailSerializer

    def get_queryset(self):
        return User.objects.annotate(
            purchase_count=Count("policy_purchases", distinct=True),
            claim_count=Count("claims", distinct=True),
        )


@extend_schema(
    tags=ADMIN_TAG,
    summary="Suspend a user",
    request=None,
    responses=AdminUserSerializer,
)
class AdminUserSuspendView(AdminBase, GenericAPIView):
    """Deactivate a user's account so they can no longer sign in.

    An administrator cannot suspend their own account or another
    administrator, which keeps at least one admin able to sign in.
    """

    required_permission = Perm.CUSTOMER_SUSPEND
    serializer_class = AdminUserSerializer

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            raise UserNotSuspendable("You cannot suspend your own account.")
        if user.is_platform_admin:
            raise UserNotSuspendable("Administrator accounts cannot be suspended here.")
        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active"])
            record_audit(
                actor=request.user,
                action=Perm.CUSTOMER_SUSPEND,
                module="customer",
                entity_type="User",
                entity_id=user.pk,
                changes={"is_active": [True, False]},
                request=request,
            )
        return Response(AdminUserSerializer(user).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Reactivate a user",
    request=None,
    responses=AdminUserSerializer,
)
class AdminUserReactivateView(AdminBase, GenericAPIView):
    required_permission = Perm.CUSTOMER_RESTORE
    serializer_class = AdminUserSerializer

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
            record_audit(
                actor=request.user,
                action=Perm.CUSTOMER_RESTORE,
                module="customer",
                entity_type="User",
                entity_id=user.pk,
                changes={"is_active": [False, True]},
                request=request,
            )
        return Response(AdminUserSerializer(user).data, status=status.HTTP_200_OK)


# --- Policies ---------------------------------------------------------------


@extend_schema(tags=ADMIN_TAG, summary="List all policies")
class AdminPolicyListView(AdminBase, ListAPIView):
    required_permission = Perm.POLICY_VIEW
    serializer_class = AdminPolicySerializer
    filterset_fields = ["status", "provider", "category", "is_featured"]
    search_fields = ["name", "provider__company_name"]

    def get_queryset(self):
        return Policy.objects.select_related("provider", "category").order_by(
            "-created_at"
        )


class AdminPolicyActionBase(AdminBase, GenericAPIView):
    """Base for the admin policy status actions.

    Each subclass runs a guarded :class:`~apps.policies.models.Policy`
    transition and notifies the owning provider. The response is the same
    ``AdminPolicySerializer`` the list uses, so the frontend can patch the row
    in place.
    """

    serializer_class = AdminPolicySerializer

    def get_queryset(self):
        return Policy.objects.select_related("provider", "provider__user", "category")

    def _serialized(self, policy):
        return Response(
            AdminPolicySerializer(policy).data, status=status.HTTP_200_OK
        )


@extend_schema(
    tags=ADMIN_TAG,
    summary="Approve a policy",
    request=None,
    responses=AdminPolicySerializer,
)
class AdminPolicyApproveView(AdminPolicyActionBase):
    required_permission = Perm.POLICY_APPROVE

    def post(self, request, pk):
        policy = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            policy.approve()
        except ValueError as error:
            raise PolicyNotActionable(str(error))
        notifications.notify_policy_approved(policy)
        record_audit(
            actor=request.user,
            action=Perm.POLICY_APPROVE,
            module="policy",
            entity_type="Policy",
            entity_id=policy.pk,
            changes={"status": [None, policy.status]},
            request=request,
        )
        return self._serialized(policy)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Send a policy back for changes",
    request=None,
    responses=AdminPolicySerializer,
)
class AdminPolicyRejectView(AdminPolicyActionBase):
    required_permission = Perm.POLICY_REJECT

    def post(self, request, pk):
        policy = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            policy.send_back()
        except ValueError as error:
            raise PolicyNotActionable(str(error))
        notifications.notify_policy_rejected(policy)
        record_audit(
            actor=request.user,
            action=Perm.POLICY_REJECT,
            module="policy",
            entity_type="Policy",
            entity_id=policy.pk,
            changes={"status": [None, policy.status]},
            request=request,
        )
        return self._serialized(policy)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Deactivate a policy",
    request=None,
    responses=AdminPolicySerializer,
)
class AdminPolicyDeactivateView(AdminPolicyActionBase):
    required_permission = Perm.POLICY_SUSPEND

    def post(self, request, pk):
        policy = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            policy.deactivate()
        except ValueError as error:
            raise PolicyNotActionable(str(error))
        notifications.notify_policy_deactivated(policy)
        record_audit(
            actor=request.user,
            action=Perm.POLICY_SUSPEND,
            module="policy",
            entity_type="Policy",
            entity_id=policy.pk,
            changes={"status": [None, policy.status]},
            request=request,
        )
        return self._serialized(policy)


# --- Reports (CSV export) ---------------------------------------------------


@extend_schema(
    tags=ADMIN_TAG,
    summary="Export providers as CSV",
    responses={200: OpenApiTypes.BINARY},
)
class AdminProviderReportView(CsvExportMixin, AdminProviderListView):
    report_basename = "bimaya-providers"
    report_columns = [
        ("ID", lambda p: p.id),
        ("Company", lambda p: p.company_name),
        ("Registration no.", lambda p: p.registration_number),
        ("Owner name", lambda p: p.user.full_name),
        ("Owner email", lambda p: p.user.email),
        ("KYC status", lambda p: p.get_kyc_status_display()),
        ("Approved", lambda p: yes_no(p.is_approved)),
        ("Policies", lambda p: p.policy_count),
        ("Joined", lambda p: local_date(p.created_at)),
    ]


@extend_schema(
    tags=ADMIN_TAG,
    summary="Export users as CSV",
    responses={200: OpenApiTypes.BINARY},
)
class AdminUserReportView(CsvExportMixin, AdminUserListView):
    report_basename = "bimaya-users"
    report_columns = [
        ("ID", lambda u: u.id),
        ("Email", lambda u: u.email),
        ("Name", lambda u: u.full_name),
        ("Phone", lambda u: u.phone),
        ("Role", lambda u: u.get_role_display()),
        ("Active", lambda u: yes_no(u.is_active)),
        ("Verified", lambda u: yes_no(u.is_verified)),
        ("Joined", lambda u: local_date(u.date_joined)),
    ]


@extend_schema(
    tags=ADMIN_TAG,
    summary="Export policies as CSV",
    responses={200: OpenApiTypes.BINARY},
)
class AdminPolicyReportView(CsvExportMixin, AdminPolicyListView):
    report_basename = "bimaya-policies"
    report_columns = [
        ("ID", lambda p: p.id),
        ("Policy", lambda p: p.name),
        ("Provider", lambda p: p.provider.company_name),
        ("Category", lambda p: p.category.name),
        ("Premium (NPR)", lambda p: money(p.premium)),
        ("Frequency", lambda p: p.get_premium_frequency_display()),
        ("Coverage (NPR)", lambda p: money(p.coverage_amount)),
        ("Status", lambda p: p.get_status_display()),
        ("Created", lambda p: local_date(p.created_at)),
    ]


@extend_schema(
    tags=ADMIN_TAG,
    summary="Export purchases as CSV",
    responses={200: OpenApiTypes.BINARY},
)
class AdminPurchaseReportView(CsvExportMixin, AdminPurchaseListView):
    report_basename = "bimaya-purchases"
    report_columns = [
        ("ID", lambda p: p.id),
        ("Policy number", lambda p: p.policy_number or ""),
        ("Policy", lambda p: p.policy.name),
        ("Insurer", lambda p: p.policy.provider.company_name),
        ("Customer", lambda p: p.customer.full_name),
        ("Customer email", lambda p: p.customer.email),
        ("Premium (NPR)", lambda p: money(p.policy.premium)),
        ("Status", lambda p: p.get_status_display()),
        ("Purchased", lambda p: local_date(p.created_at)),
        ("Start", lambda p: local_date(p.start_date)),
        ("End", lambda p: local_date(p.end_date)),
    ]


@extend_schema(
    tags=ADMIN_TAG,
    summary="Export provider payouts as CSV",
    responses={200: OpenApiTypes.BINARY},
)
class AdminPayoutReportView(CsvExportMixin, AdminPayoutListView):
    report_basename = "bimaya-payouts"
    report_columns = [
        ("ID", lambda p: p.id),
        ("Provider", lambda p: p.provider.company_name),
        ("Policy", lambda p: p.purchase.policy.name),
        ("Policy number", lambda p: p.purchase.policy_number or ""),
        ("Gross (NPR)", lambda p: money(p.gross_amount)),
        ("Commission %", lambda p: money(p.commission_rate)),
        ("Commission (NPR)", lambda p: money(p.commission_amount)),
        ("Net payable (NPR)", lambda p: money(p.net_amount)),
        ("Status", lambda p: p.get_status_display()),
        ("Paid", lambda p: local_date(p.paid_at)),
        ("Created", lambda p: local_date(p.created_at)),
    ]


# --- Analytics --------------------------------------------------------------


@extend_schema(
    tags=["analytics"],
    summary="Platform analytics",
    responses=OpenApiTypes.OBJECT,
)
class AdminAnalyticsView(AdminBase, GenericAPIView):
    """Platform-wide totals, breakdowns and a recent trend for the dashboard."""

    required_permission = Perm.DASHBOARD_VIEW

    def get(self, request):
        return Response(build_admin_analytics())
