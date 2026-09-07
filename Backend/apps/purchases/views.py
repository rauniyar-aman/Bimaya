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
    IsProvider,
    IsVerified,
)
from apps.notifications import services as notifications
from apps.payments.models import Payment

from . import pdf
from .exceptions import (
    DocumentNotAvailable,
    PurchaseNotCancellable,
    PurchaseNotIssuable,
)
from .models import PolicyPurchase
from .serializers import (
    PolicyIssueSerializer,
    PolicyPurchaseCreateSerializer,
    PolicyPurchaseSerializer,
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
        notifications.notify_purchase_created(serializer.instance)
        output = PolicyPurchaseSerializer(serializer.instance).data
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

    Scoped to purchases of the signed-in provider's own policies — never any
    other provider's — so ownership is enforced by the queryset itself.
    """

    permission_classes = [IsProvider, IsVerified]
    serializer_class = PolicyPurchaseSerializer

    def provider_profile(self):
        return getattr(self.request.user, "provider_profile", None)

    def get_queryset(self):
        provider = self.provider_profile()
        if provider is None:
            return PolicyPurchase.objects.none()
        return PolicyPurchase.objects.filter(
            policy__provider=provider
        ).select_related("policy", "policy__provider", "policy__category", "kyc")


@extend_schema(tags=PURCHASE_TAG, summary="List purchases awaiting issuance")
class ProviderIssuanceListView(ProviderIssuanceBase, ListAPIView):
    def get_queryset(self):
        return super().get_queryset().filter(status=PolicyPurchase.Status.FORWARDED)


@extend_schema(
    tags=PURCHASE_TAG,
    summary="Issue a forwarded purchase",
    request=PolicyIssueSerializer,
    responses=PolicyPurchaseSerializer,
)
class ProviderIssueView(ProviderIssuanceBase, GenericAPIView):
    serializer_class = PolicyIssueSerializer

    def post(self, request, pk):
        purchase = get_object_or_404(self.get_queryset(), pk=pk)
        if purchase.status != PolicyPurchase.Status.FORWARDED:
            raise PurchaseNotIssuable()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase.issue(serializer.validated_data["policy_number"])
        notifications.notify_policy_issued(purchase)
        return Response(
            PolicyPurchaseSerializer(purchase).data, status=status.HTTP_200_OK
        )
