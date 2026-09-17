"""Customer purchase endpoints (``/api/v1/purchases/``)."""

from io import BytesIO

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
)
from rest_framework.response import Response

from apps.core.permissions import (
    IsCustomer,
    IsOwnerOrPlatformAdmin,
    IsVerified,
)
from apps.notifications import services as notifications
from apps.providers.access import HasProviderPermission, provider_for
from apps.providers.rbac import ProviderPerm
from apps.payments.models import Payment
from apps.staff.services import record_audit

from . import pdf
from .exceptions import (
    DocumentNotAvailable,
    PurchaseNotCancellable,
    PurchaseNotIssuable,
)
from .models import PolicyPurchase, ProviderPayout
from .serializers import (
    PolicyIssueSerializer,
    PolicyPurchaseCreateSerializer,
    PolicyPurchaseSerializer,
    ProviderPayoutSerializer,
    ProviderPurchaseSerializer,
)

PURCHASE_TAG = ["purchases"]


class PurchaseBase:
    """Shared helpers for the customer's own-purchase endpoints."""

    permission_classes = [IsCustomer, IsVerified]
    serializer_class = PolicyPurchaseSerializer
    owner_field = "customer"

    def get_queryset(self):
        return PolicyPurchase.objects.for_customer(self.request.user).select_related(
            "policy", "policy__provider", "policy__category"
        )


@extend_schema(tags=PURCHASE_TAG, summary="List or create own purchases")
class PolicyPurchaseListCreateView(PurchaseBase, ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == "POST":
            return PolicyPurchaseCreateSerializer
        return PolicyPurchaseSerializer

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        purchase = serializer.instance
        notifications.notify_purchase_created(purchase)
        record_audit(
            actor=request.user,
            action="purchase.create",
            module="purchase",
            entity_type="PolicyPurchase",
            entity_id=purchase.pk,
            changes={"policy": purchase.policy.name, "status": purchase.status},
            request=request,
        )
        output = PolicyPurchaseSerializer(purchase).data
        headers = self.get_success_headers(output)
        return Response(output, status=status.HTTP_201_CREATED, headers=headers)


@extend_schema(tags=PURCHASE_TAG, summary="Retrieve an own purchase")
class PolicyPurchaseDetailView(PurchaseBase, RetrieveAPIView):
    permission_classes = [IsCustomer, IsVerified, IsOwnerOrPlatformAdmin]


@extend_schema(
    tags=PURCHASE_TAG,
    summary="Cancel an own purchase",
    request=None,
    responses=PolicyPurchaseSerializer,
)
class PolicyPurchaseCancelView(PurchaseBase, GenericAPIView):
    permission_classes = [IsCustomer, IsVerified, IsOwnerOrPlatformAdmin]

    def post(self, request, pk):
        purchase = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, purchase)
        if purchase.status != PolicyPurchase.Status.PENDING_PAYMENT:
            raise PurchaseNotCancellable()
        purchase.status = PolicyPurchase.Status.CANCELLED
        purchase.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(purchase).data, status=status.HTTP_200_OK)


class PurchaseDocumentBase(PurchaseBase, GenericAPIView):
    """Base for the owner-only PDF downloads.

    Widens the queryset to prefetch ``kyc`` (the certificate reads holder
    details straight off it), and resolves + permission-checks the purchase.
    """

    permission_classes = [IsCustomer, IsVerified, IsOwnerOrPlatformAdmin]

    def get_queryset(self):
        return PolicyPurchase.objects.for_customer(self.request.user).select_related(
            "policy", "policy__provider", "policy__category", "kyc"
        )

    def get_purchase(self, request, pk):
        purchase = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, purchase)
        return purchase

    @staticmethod
    def _pdf_response(pdf_bytes, filename):
        return FileResponse(
            BytesIO(pdf_bytes),
            as_attachment=True,
            filename=filename,
            content_type="application/pdf",
        )


@extend_schema(
    tags=PURCHASE_TAG,
    summary="Download the policy certificate (PDF)",
    responses={200: OpenApiTypes.BINARY},
)
class PurchaseCertificateView(PurchaseDocumentBase):
    def get(self, request, pk):
        purchase = self.get_purchase(request, pk)
        if not purchase.policy_number:
            raise DocumentNotAvailable()
        return self._pdf_response(
            pdf.render_certificate(purchase),
            f"Bimaya-Policy-{purchase.policy_number}.pdf",
        )


@extend_schema(
    tags=PURCHASE_TAG,
    summary="Download the payment receipt (PDF)",
    responses={200: OpenApiTypes.BINARY},
)
class PurchaseReceiptView(PurchaseDocumentBase):
    def get(self, request, pk):
        purchase = self.get_purchase(request, pk)
        payment = (
            purchase.payments.filter(status=Payment.Status.SUCCESS)
            .order_by("-paid_at")
            .first()
        )
        if payment is None:
            raise DocumentNotAvailable()
        return self._pdf_response(
            pdf.render_receipt(payment),
            f"Bimaya-Receipt-{payment.gateway_transaction_id or payment.id}.pdf",
        )


class ProviderIssuanceBase:
    """Shared helpers for a provider working their issuance queue.

    Scoped to purchases of the acting user's provider organisation — never any
    other provider's — so ownership is enforced by the queryset itself. Access
    is gated by :class:`~apps.providers.access.HasProviderPermission`; each
    concrete view declares the granular permission it needs.
    """

    permission_classes = [HasProviderPermission]
    required_permission = ProviderPerm.ISSUANCE_VIEW
    serializer_class = PolicyPurchaseSerializer

    def get_provider(self):
        return provider_for(self.request.user)

    def get_queryset(self):
        provider = self.get_provider()
        if provider is None:
            return PolicyPurchase.objects.none()
        return PolicyPurchase.objects.filter(
            policy__provider=provider
        ).select_related("policy", "policy__provider", "policy__category", "kyc")


@extend_schema(tags=PURCHASE_TAG, summary="List purchases awaiting issuance")
class ProviderIssuanceListView(ProviderIssuanceBase, ListAPIView):
    required_permission = ProviderPerm.ISSUANCE_VIEW

    def get_queryset(self):
        return super().get_queryset().filter(status=PolicyPurchase.Status.FORWARDED)


@extend_schema(tags=PURCHASE_TAG, summary="List all purchases on the provider's policies")
class ProviderPurchaseListView(ProviderIssuanceBase, ListAPIView):
    """Read-only sales/history list across every purchase of the provider's own
    policies — the full funnel, not just the issuance queue — filterable by
    status and searchable by policy name or number."""

    required_permission = ProviderPerm.PURCHASE_VIEW
    serializer_class = ProviderPurchaseSerializer
    filterset_fields = ["status"]
    search_fields = ["policy__name", "policy_number"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return super().get_queryset().select_related("customer").order_by("-created_at")


@extend_schema(tags=PURCHASE_TAG, summary="List the provider's commission payouts")
class ProviderPayoutListView(ProviderIssuanceBase, ListAPIView):
    """Read-only payout ledger for the acting provider: the commission split on
    each issued sale of their policies, and whether Bimaya has paid it out yet.
    Scoped to the provider's own payouts by the queryset, so no cross-provider
    leakage. Filterable by settlement status, searchable by policy name/number."""

    required_permission = ProviderPerm.PAYOUT_VIEW
    serializer_class = ProviderPayoutSerializer
    filterset_fields = ["status"]
    search_fields = ["purchase__policy__name", "purchase__policy_number"]
    ordering = ["-created_at"]

    def get_queryset(self):
        provider = self.get_provider()
        if provider is None:
            return ProviderPayout.objects.none()
        return (
            ProviderPayout.objects.filter(provider=provider)
            .select_related("purchase", "purchase__policy")
            .order_by("-created_at")
        )


@extend_schema(
    tags=PURCHASE_TAG,
    summary="Issue a forwarded purchase",
    request=PolicyIssueSerializer,
    responses=PolicyPurchaseSerializer,
)
class ProviderIssueView(ProviderIssuanceBase, GenericAPIView):
    required_permission = ProviderPerm.ISSUANCE_ISSUE
    serializer_class = PolicyIssueSerializer

    def post(self, request, pk):
        purchase = get_object_or_404(self.get_queryset(), pk=pk)
        if purchase.status != PolicyPurchase.Status.FORWARDED:
            raise PurchaseNotIssuable()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase.issue(serializer.validated_data["policy_number"])
        notifications.notify_policy_issued(purchase)
        record_audit(
            actor=request.user,
            action=ProviderPerm.ISSUANCE_ISSUE,
            module="issuance",
            entity_type="PolicyPurchase",
            entity_id=purchase.pk,
            changes={
                "status": [PolicyPurchase.Status.FORWARDED, purchase.status],
                "policy_number": [None, purchase.policy_number],
            },
            request=request,
        )
        return Response(
            PolicyPurchaseSerializer(purchase).data, status=status.HTTP_200_OK
        )
