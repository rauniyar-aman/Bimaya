"""Customer purchase endpoints (``/api/v1/purchases/``)."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.response import Response

from apps.core.permissions import IsCustomer, IsOwnerOrPlatformAdmin, IsVerified

from .exceptions import PurchaseNotCancellable
from .models import PolicyPurchase
from .serializers import PolicyPurchaseCreateSerializer, PolicyPurchaseSerializer

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
