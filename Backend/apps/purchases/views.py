"""Customer purchase endpoints (``/api/v1/purchases/``)."""

from django.shortcuts import get_object_or_404
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

from .exceptions import PurchaseNotCancellable, PurchaseNotIssuable
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
        return Response(
            PolicyPurchaseSerializer(purchase).data, status=status.HTTP_200_OK
        )
