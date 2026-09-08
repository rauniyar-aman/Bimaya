"""Admin-panel REST APIs (``/api/v1/admin/...``).

A branded in-app admin area is built on these; the Django admin remains as the
low-level fallback. Every view requires :class:`IsPlatformAdmin`. Actions that
change state reuse the same model methods the Django admin uses
(``CustomerKyc.mark_verified``/``mark_rejected``, ``PolicyPurchase.forward_to_provider``)
and dispatch notifications through :mod:`apps.notifications.services`.
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from apps.core.permissions import IsPlatformAdmin
from apps.documents.models import CustomerKyc
from apps.documents.serializers import CustomerKycSerializer
from apps.notifications import services as notifications
from apps.policies.models import Policy
from apps.providers.models import Provider
from apps.purchases.models import PolicyPurchase

from .analytics import build_admin_analytics
from .exceptions import (
    PolicyNotActionable,
    PurchaseNotForwardable,
    UserNotSuspendable,
)
from .serializers import (
    AdminKycSerializer,
    AdminPolicySerializer,
    AdminProviderSerializer,
    AdminPurchaseSerializer,
    AdminUserDetailSerializer,
    AdminUserSerializer,
    RejectNoteSerializer,
)

User = get_user_model()

ADMIN_TAG = ["admin"]


class AdminBase:
    """Shared configuration for every admin-panel endpoint."""

    permission_classes = [IsPlatformAdmin]


# --- Providers --------------------------------------------------------------


@extend_schema(tags=ADMIN_TAG, summary="List providers")
class AdminProviderListView(AdminBase, ListAPIView):
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
    serializer_class = AdminProviderSerializer

    def post(self, request, pk):
        provider = get_object_or_404(Provider, pk=pk)
        if not provider.is_approved:
            provider.is_approved = True
            provider.save(update_fields=["is_approved", "updated_at"])
            notifications.notify_provider_approved(provider)
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
    serializer_class = AdminProviderSerializer

    def post(self, request, pk):
        provider = get_object_or_404(Provider, pk=pk)
        if provider.is_approved:
            provider.is_approved = False
            provider.save(update_fields=["is_approved", "updated_at"])
        return Response(
            AdminProviderApproveView._serialize(provider), status=status.HTTP_200_OK
        )


# --- KYC --------------------------------------------------------------------


class AdminKycBase(AdminBase):
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
        return FileResponse(image.open("rb"))


@extend_schema(
    tags=ADMIN_TAG,
    summary="Verify a KYC record",
    request=None,
    responses=CustomerKycSerializer,
)
class AdminKycVerifyView(AdminKycBase, GenericAPIView):
    serializer_class = CustomerKycSerializer

    def post(self, request, pk):
        kyc = get_object_or_404(CustomerKyc, pk=pk)
        kyc.mark_verified()
        notifications.notify_kyc_verified(kyc)
        return Response(CustomerKycSerializer(kyc).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Reject a KYC record",
    request=RejectNoteSerializer,
    responses=CustomerKycSerializer,
)
class AdminKycRejectView(AdminKycBase, GenericAPIView):
    serializer_class = RejectNoteSerializer

    def post(self, request, pk):
        kyc = get_object_or_404(CustomerKyc, pk=pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kyc.mark_rejected(serializer.validated_data["note"])
        notifications.notify_kyc_rejected(kyc)
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
    filterset_fields = ["status"]
    search_fields = ["customer__email", "policy__name", "policy_number"]


@extend_schema(
    tags=ADMIN_TAG,
    summary="Verify KYC + payment and forward to the provider",
    request=None,
    responses=AdminPurchaseSerializer,
)
class AdminPurchaseForwardView(AdminPurchaseBase, GenericAPIView):
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
        return Response(
            AdminPurchaseSerializer(purchase).data, status=status.HTTP_200_OK
        )


# --- Users ------------------------------------------------------------------


@extend_schema(tags=ADMIN_TAG, summary="List users")
class AdminUserListView(AdminBase, ListAPIView):
    serializer_class = AdminUserSerializer
    filterset_fields = ["role", "is_verified", "is_active"]
    search_fields = ["email", "full_name", "phone"]

    def get_queryset(self):
        return User.objects.all().order_by("-date_joined")


@extend_schema(tags=ADMIN_TAG, summary="Retrieve a user with activity counts")
class AdminUserDetailView(AdminBase, RetrieveAPIView):
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
        return Response(AdminUserSerializer(user).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Reactivate a user",
    request=None,
    responses=AdminUserSerializer,
)
class AdminUserReactivateView(AdminBase, GenericAPIView):
    serializer_class = AdminUserSerializer

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        return Response(AdminUserSerializer(user).data, status=status.HTTP_200_OK)


# --- Policies ---------------------------------------------------------------


@extend_schema(tags=ADMIN_TAG, summary="List all policies")
class AdminPolicyListView(AdminBase, ListAPIView):
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
    def post(self, request, pk):
        policy = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            policy.approve()
        except ValueError as error:
            raise PolicyNotActionable(str(error))
        notifications.notify_policy_approved(policy)
        return self._serialized(policy)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Send a policy back for changes",
    request=None,
    responses=AdminPolicySerializer,
)
class AdminPolicyRejectView(AdminPolicyActionBase):
    def post(self, request, pk):
        policy = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            policy.send_back()
        except ValueError as error:
            raise PolicyNotActionable(str(error))
        notifications.notify_policy_rejected(policy)
        return self._serialized(policy)


@extend_schema(
    tags=ADMIN_TAG,
    summary="Deactivate a policy",
    request=None,
    responses=AdminPolicySerializer,
)
class AdminPolicyDeactivateView(AdminPolicyActionBase):
    def post(self, request, pk):
        policy = get_object_or_404(self.get_queryset(), pk=pk)
        try:
            policy.deactivate()
        except ValueError as error:
            raise PolicyNotActionable(str(error))
        notifications.notify_policy_deactivated(policy)
        return self._serialized(policy)


# --- Analytics --------------------------------------------------------------


@extend_schema(
    tags=["analytics"],
    summary="Platform analytics",
    responses=OpenApiTypes.OBJECT,
)
class AdminAnalyticsView(AdminBase, GenericAPIView):
    """Platform-wide totals, breakdowns and a recent trend for the dashboard."""

    def get(self, request):
        return Response(build_admin_analytics())
