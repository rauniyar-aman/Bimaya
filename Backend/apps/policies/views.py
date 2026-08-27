"""Marketplace policy & category API endpoints (``/api/v1/``).

Public reads (categories, policy list/detail/compare) are open to everyone.
Provider endpoints let a signed-in provider manage their own listings; approval
to make a policy public happens in the Django admin, never here.
"""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.permissions import IsOwnerOrPlatformAdmin, IsProvider, IsVerified
from apps.providers.models import Provider

from .exceptions import PolicyNotSubmittable, ProviderProfileRequired
from .filters import PolicyFilter
from .models import InsuranceCategory, Policy
from .serializers import (
    CategorySerializer,
    PolicyCompareSerializer,
    PolicyDetailSerializer,
    PolicyListSerializer,
    ProviderPolicyWriteSerializer,
)

CATALOG_TAG = ["catalog"]
PROVIDER_TAG = ["provider"]

MAX_COMPARE = 4


# ---------------------------------------------------------------------------
# Public catalog
# ---------------------------------------------------------------------------


@extend_schema(tags=CATALOG_TAG, summary="List insurance categories", auth=[])
class CategoryListView(ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = []
    queryset = InsuranceCategory.objects.filter(is_active=True)


@extend_schema(tags=CATALOG_TAG, summary="Retrieve a category", auth=[])
class CategoryDetailView(RetrieveAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    queryset = InsuranceCategory.objects.filter(is_active=True)


@extend_schema(tags=CATALOG_TAG, summary="List public policies", auth=[])
class PolicyListView(ListAPIView):
    serializer_class = PolicyListSerializer
    permission_classes = [AllowAny]
    filterset_class = PolicyFilter
    search_fields = ["name", "summary", "description", "provider__company_name"]
    ordering_fields = ["premium", "coverage_amount", "created_at"]

    def get_queryset(self):
        return Policy.objects.public().select_related("provider", "category")


@extend_schema(tags=CATALOG_TAG, summary="Retrieve a public policy", auth=[])
class PolicyDetailView(RetrieveAPIView):
    serializer_class = PolicyDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return Policy.objects.public().select_related("provider", "category")


@extend_schema(
    tags=CATALOG_TAG,
    summary="Compare public policies",
    description="Returns up to four public policies side by side, in the order requested.",
    auth=[],
    parameters=[
        OpenApiParameter(
            name="ids",
            description="Comma-separated policy ids, e.g. `1,2,3` (max 4).",
            required=True,
            type=str,
        )
    ],
)
class PolicyCompareView(ListAPIView):
    serializer_class = PolicyCompareSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = []

    def get_queryset(self):
        raw = self.request.query_params.get("ids", "")
        ids = []
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and int(part) not in ids:
                ids.append(int(part))
        ids = ids[:MAX_COMPARE]
        if not ids:
            return Policy.objects.none()

        policies = Policy.objects.public().select_related("provider", "category").filter(
            id__in=ids
        )
        rank = {pid: index for index, pid in enumerate(ids)}
        return sorted(policies, key=lambda policy: rank.get(policy.id, len(ids)))


# ---------------------------------------------------------------------------
# Provider self-service
# ---------------------------------------------------------------------------


class ProviderPolicyBase:
    """Shared helpers for the provider's own-policy endpoints."""

    permission_classes = [IsProvider, IsVerified]
    serializer_class = ProviderPolicyWriteSerializer

    def provider_profile(self):
        try:
            return self.request.user.provider_profile
        except Provider.DoesNotExist:
            return None

    def get_queryset(self):
        provider = self.provider_profile()
        if provider is None:
            return Policy.objects.none()
        return Policy.objects.filter(provider=provider).select_related(
            "provider", "category"
        )


@extend_schema(tags=PROVIDER_TAG, summary="List or create own policies")
class ProviderPolicyListCreateView(ProviderPolicyBase, ListCreateAPIView):
    filter_backends = []

    def perform_create(self, serializer):
        provider = self.provider_profile()
        if provider is None:
            raise ProviderProfileRequired()
        serializer.save(provider=provider, status=Policy.Status.DRAFT)


@extend_schema(tags=PROVIDER_TAG, summary="Retrieve, update or delete an own policy")
class ProviderPolicyDetailView(ProviderPolicyBase, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsProvider, IsVerified, IsOwnerOrPlatformAdmin]
    owner_field = "provider.user"

    def perform_update(self, serializer):
        was_approved = serializer.instance.status == Policy.Status.APPROVED
        policy = serializer.save()
        # Any change to a live policy sends it back for re-review.
        if was_approved:
            policy.status = Policy.Status.PENDING
            policy.save(update_fields=["status", "updated_at"])


@extend_schema(
    tags=PROVIDER_TAG,
    summary="Submit an own policy for review",
    request=None,
    responses=ProviderPolicyWriteSerializer,
)
class ProviderPolicySubmitView(ProviderPolicyBase, GenericAPIView):
    permission_classes = [IsProvider, IsVerified, IsOwnerOrPlatformAdmin]
    owner_field = "provider.user"

    def post(self, request, pk):
        policy = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, policy)
        if policy.status not in (Policy.Status.DRAFT, Policy.Status.INACTIVE):
            raise PolicyNotSubmittable()
        policy.status = Policy.Status.PENDING
        policy.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(policy).data, status=status.HTTP_200_OK)
