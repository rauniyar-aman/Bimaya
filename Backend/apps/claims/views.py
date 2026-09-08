"""Claim endpoints: the customer's own claims (``/api/v1/claims/``) and the
underwriting provider's claims queue (``/api/v1/provider/claims/``).

Structure mirrors :mod:`apps.purchases.views` — a shared mixin holding
``permission_classes``/``serializer_class``/``get_queryset``, concrete views
multiply-inheriting a DRF generic, and ``GenericAPIView`` custom actions that
resolve the object from the scoped queryset, guard the state, run a model
transition, then return the read serializer.
"""

import os

from django.db import transaction
from django.db.models import Q
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
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.permissions import (
    IsCustomer,
    IsOwnerOrPlatformAdmin,
    IsProvider,
    IsVerified,
)
from apps.notifications import services as notifications

from .exceptions import (
    ClaimNotDecidable,
    ClaimNotPayable,
    ClaimNotResubmittable,
    PayoutNotConfirmable,
)
from .models import Claim, ClaimDocument, ClaimMessage, ClaimPayout
from .serializers import (
    ClaimApproveSerializer,
    ClaimCreateSerializer,
    ClaimMessageCreateSerializer,
    ClaimPayoutConfirmSerializer,
    ClaimPayoutInitiateSerializer,
    ClaimRejectSerializer,
    ClaimRequestInfoSerializer,
    ClaimSerializer,
)

CLAIM_TAG = ["claims"]

# Relations every read of a claim needs (policy + provider + category context).
_CLAIM_RELATIONS = (
    "purchase",
    "purchase__policy",
    "purchase__policy__provider",
    "purchase__policy__category",
)


class ClaimBase:
    """Shared configuration for the customer's own-claim endpoints."""

    permission_classes = [IsCustomer, IsVerified]
    serializer_class = ClaimSerializer
    owner_field = "customer"

    def get_queryset(self):
        return (
            Claim.objects.for_customer(self.request.user)
            .select_related(*_CLAIM_RELATIONS)
            .prefetch_related("documents", "payouts", "messages")
        )


@extend_schema(tags=CLAIM_TAG, summary="List or file the signed-in customer's claims")
class ClaimListCreateView(ClaimBase, ListCreateAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ClaimCreateSerializer
        return ClaimSerializer

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        claim = serializer.instance
        notifications.notify_claim_status(claim, "SUBMITTED")
        notifications.notify_provider_new_claim(claim)
        output = ClaimSerializer(claim).data
        headers = self.get_success_headers(output)
        return Response(output, status=status.HTTP_201_CREATED, headers=headers)


@extend_schema(tags=CLAIM_TAG, summary="Retrieve one of the customer's own claims")
class ClaimDetailView(ClaimBase, RetrieveAPIView):
    permission_classes = [IsCustomer, IsVerified, IsOwnerOrPlatformAdmin]


@extend_schema(
    tags=CLAIM_TAG,
    summary="Resubmit a claim that was sent back for more information",
    request=None,
    responses=ClaimSerializer,
)
class ClaimResubmitView(ClaimBase, GenericAPIView):
    permission_classes = [IsCustomer, IsVerified, IsOwnerOrPlatformAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        claim = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, claim)
        if claim.status != Claim.Status.MORE_INFO:
            raise ClaimNotResubmittable()
        uploads = request.FILES.getlist("documents")
        if uploads:
            ClaimDocument.objects.bulk_create(
                [ClaimDocument(claim=claim, file=upload) for upload in uploads]
            )
        claim.resubmit()
        notifications.notify_provider_new_claim(claim)
        return Response(ClaimSerializer(claim).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=CLAIM_TAG,
    summary="Post a message to a claim thread (customer side)",
    request=ClaimMessageCreateSerializer,
    responses=ClaimSerializer,
)
class ClaimMessageCreateView(ClaimBase, GenericAPIView):
    """Customer posts a message to their claim's thread and the provider is
    notified. Allowed in any status the customer can see the claim in."""

    permission_classes = [IsCustomer, IsVerified, IsOwnerOrPlatformAdmin]
    serializer_class = ClaimMessageCreateSerializer

    def post(self, request, pk):
        claim = get_object_or_404(self.get_queryset(), pk=pk)
        self.check_object_permissions(request, claim)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ClaimMessage.objects.create(
            claim=claim,
            author=request.user,
            author_role=request.user.role,
            body=serializer.validated_data["body"],
        )
        notifications.notify_claim_message(claim, to="provider")
        fresh = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(ClaimSerializer(fresh).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=CLAIM_TAG,
    summary="Download a claim's supporting document",
    responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
)
class ClaimDocumentDownloadView(GenericAPIView):
    """Stream a claim's supporting document to the owner **or** the underwriting
    provider — never through a public media URL. These are medical/police/
    financial documents, more sensitive than the KYC ID scans, so access is
    authenticated and scoped by the queryset itself (a stranger 404s)."""

    permission_classes = [IsVerified]

    def get_queryset(self):
        user = self.request.user
        return Claim.objects.filter(
            Q(customer=user) | Q(purchase__policy__provider__user=user)
        )

    def get(self, request, pk, doc_pk):
        claim = get_object_or_404(self.get_queryset(), pk=pk)
        document = get_object_or_404(claim.documents, pk=doc_pk)
        filename = os.path.basename(document.file.name)
        return FileResponse(
            document.file.open("rb"), as_attachment=True, filename=filename
        )


class ProviderClaimBase:
    """Shared configuration for a provider working their claims queue.

    Scoped to claims against the signed-in provider's own policies — never
    another provider's — so ownership is enforced by the queryset itself.
    """

    permission_classes = [IsProvider, IsVerified]
    serializer_class = ClaimSerializer
    filterset_fields = ["status"]

    def provider_profile(self):
        return getattr(self.request.user, "provider_profile", None)

    def get_queryset(self):
        provider = self.provider_profile()
        if provider is None:
            return Claim.objects.none()
        return (
            Claim.objects.for_provider(provider)
            .select_related(*_CLAIM_RELATIONS)
            .prefetch_related("documents", "payouts", "messages")
        )

    def get_claim(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)


@extend_schema(tags=CLAIM_TAG, summary="List claims filed on the provider's policies")
class ProviderClaimListView(ProviderClaimBase, ListAPIView):
    pass


@extend_schema(tags=CLAIM_TAG, summary="Retrieve a claim on one of the provider's policies")
class ProviderClaimDetailView(ProviderClaimBase, RetrieveAPIView):
    pass


@extend_schema(
    tags=CLAIM_TAG,
    summary="Post a message to a claim thread (provider side)",
    request=ClaimMessageCreateSerializer,
    responses=ClaimSerializer,
)
class ProviderClaimMessageCreateView(ProviderClaimBase, GenericAPIView):
    """Provider posts a message to a claim thread on one of their policies and
    the customer is notified."""

    serializer_class = ClaimMessageCreateSerializer

    def post(self, request, pk):
        claim = self.get_claim(pk)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ClaimMessage.objects.create(
            claim=claim,
            author=request.user,
            author_role=request.user.role,
            body=serializer.validated_data["body"],
        )
        notifications.notify_claim_message(claim, to="customer")
        fresh = self.get_claim(pk)
        return Response(ClaimSerializer(fresh).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=CLAIM_TAG,
    summary="Start reviewing a submitted claim",
    request=None,
    responses=ClaimSerializer,
)
class ProviderClaimStartReviewView(ProviderClaimBase, GenericAPIView):
    def post(self, request, pk):
        claim = self.get_claim(pk)
        if claim.status != Claim.Status.SUBMITTED:
            raise ClaimNotDecidable()
        claim.start_review()
        notifications.notify_claim_status(claim, "UNDER_REVIEW")
        return Response(ClaimSerializer(claim).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=CLAIM_TAG,
    summary="Send a claim back to the customer for more information",
    request=ClaimRequestInfoSerializer,
    responses=ClaimSerializer,
)
class ProviderClaimRequestInfoView(ProviderClaimBase, GenericAPIView):
    serializer_class = ClaimRequestInfoSerializer

    def post(self, request, pk):
        claim = self.get_claim(pk)
        if claim.status != Claim.Status.UNDER_REVIEW:
            raise ClaimNotDecidable()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim.request_more_info(serializer.validated_data["note"])
        notifications.notify_claim_status(claim, "MORE_INFO")
        return Response(ClaimSerializer(claim).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=CLAIM_TAG,
    summary="Approve a claim for a payout amount",
    request=ClaimApproveSerializer,
    responses=ClaimSerializer,
)
class ProviderClaimApproveView(ProviderClaimBase, GenericAPIView):
    serializer_class = ClaimApproveSerializer

    def post(self, request, pk):
        claim = self.get_claim(pk)
        if claim.status != Claim.Status.UNDER_REVIEW:
            raise ClaimNotDecidable()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim.approve(
            serializer.validated_data["approved_amount"],
            serializer.validated_data.get("note", ""),
        )
        notifications.notify_claim_status(claim, "APPROVED")
        return Response(ClaimSerializer(claim).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=CLAIM_TAG,
    summary="Reject a claim",
    request=ClaimRejectSerializer,
    responses=ClaimSerializer,
)
class ProviderClaimRejectView(ProviderClaimBase, GenericAPIView):
    serializer_class = ClaimRejectSerializer

    def post(self, request, pk):
        claim = self.get_claim(pk)
        if claim.status != Claim.Status.UNDER_REVIEW:
            raise ClaimNotDecidable()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim.reject(serializer.validated_data["note"])
        notifications.notify_claim_status(claim, "REJECTED")
        return Response(ClaimSerializer(claim).data, status=status.HTTP_200_OK)


@extend_schema(
    tags=CLAIM_TAG,
    summary="Initiate a simulated payout for an approved claim",
    request=ClaimPayoutInitiateSerializer,
)
class ProviderClaimPayoutInitiateView(ProviderClaimBase, GenericAPIView):
    serializer_class = ClaimPayoutInitiateSerializer

    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        gateway = serializer.validated_data["gateway"]
        with transaction.atomic():
            claim = get_object_or_404(
                self.get_queryset().select_for_update(of=("self",)), pk=pk
            )
            if claim.status != Claim.Status.APPROVED:
                raise ClaimNotPayable()
            if claim.payouts.filter(
                status__in=(ClaimPayout.Status.INITIATED, ClaimPayout.Status.SUCCESS)
            ).exists():
                raise ClaimNotPayable()
            payout = ClaimPayout.objects.create(
                claim=claim, amount=claim.approved_amount, gateway=gateway
            )
        # A simulated gateway session — no external redirect, no real money.
        return Response(
            {
                "payout_id": payout.id,
                "gateway": payout.gateway,
                "amount": str(payout.amount),
                "reference": f"SIMPAYOUT-{payout.id}",
                "status": payout.status,
                "simulated": True,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=CLAIM_TAG,
    summary="Confirm a simulated payout and settle the claim",
    request=ClaimPayoutConfirmSerializer,
    responses=ClaimSerializer,
)
class ProviderClaimPayoutConfirmView(ProviderClaimBase, GenericAPIView):
    serializer_class = ClaimPayoutConfirmSerializer

    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            claim = get_object_or_404(
                self.get_queryset().select_for_update(of=("self",)), pk=pk
            )
            payout = (
                claim.payouts.select_for_update()
                .filter(status=ClaimPayout.Status.INITIATED)
                .order_by("-created_at")
                .first()
            )
            if payout is None:
                raise PayoutNotConfirmable()
            # Simulated confirmation → payout SUCCESS → claim SETTLED.
            payout.mark_success(f"SIMPAYOUT-{payout.id}")
        fresh = get_object_or_404(self.get_queryset(), pk=pk)
        notifications.notify_claim_status(fresh, "SETTLED")
        return Response(ClaimSerializer(fresh).data, status=status.HTTP_200_OK)
