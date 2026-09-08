"""Claim routes, mounted at ``/api/v1/`` by :mod:`bimaya.urls`."""

from django.urls import path

from .views import (
    ClaimDetailView,
    ClaimDocumentDownloadView,
    ClaimListCreateView,
    ClaimMessageCreateView,
    ClaimResubmitView,
    ProviderClaimApproveView,
    ProviderClaimDetailView,
    ProviderClaimListView,
    ProviderClaimMessageCreateView,
    ProviderClaimPayoutConfirmView,
    ProviderClaimPayoutInitiateView,
    ProviderClaimRejectView,
    ProviderClaimRequestInfoView,
    ProviderClaimStartReviewView,
)

urlpatterns = [
    # Customer — own claims.
    path("claims/", ClaimListCreateView.as_view(), name="claim-list"),
    path("claims/<int:pk>/", ClaimDetailView.as_view(), name="claim-detail"),
    path("claims/<int:pk>/resubmit/", ClaimResubmitView.as_view(), name="claim-resubmit"),
    path(
        "claims/<int:pk>/messages/",
        ClaimMessageCreateView.as_view(),
        name="claim-message",
    ),
    path(
        "claims/<int:pk>/documents/<int:doc_pk>/",
        ClaimDocumentDownloadView.as_view(),
        name="claim-document",
    ),
    # Provider — claims queue on their own policies.
    path("provider/claims/", ProviderClaimListView.as_view(), name="provider-claim-list"),
    path(
        "provider/claims/<int:pk>/",
        ProviderClaimDetailView.as_view(),
        name="provider-claim-detail",
    ),
    path(
        "provider/claims/<int:pk>/messages/",
        ProviderClaimMessageCreateView.as_view(),
        name="provider-claim-message",
    ),
    path(
        "provider/claims/<int:pk>/start-review/",
        ProviderClaimStartReviewView.as_view(),
        name="provider-claim-start-review",
    ),
    path(
        "provider/claims/<int:pk>/request-info/",
        ProviderClaimRequestInfoView.as_view(),
        name="provider-claim-request-info",
    ),
    path(
        "provider/claims/<int:pk>/approve/",
        ProviderClaimApproveView.as_view(),
        name="provider-claim-approve",
    ),
    path(
        "provider/claims/<int:pk>/reject/",
        ProviderClaimRejectView.as_view(),
        name="provider-claim-reject",
    ),
    path(
        "provider/claims/<int:pk>/payout/initiate/",
        ProviderClaimPayoutInitiateView.as_view(),
        name="provider-claim-payout-initiate",
    ),
    path(
        "provider/claims/<int:pk>/payout/confirm/",
        ProviderClaimPayoutConfirmView.as_view(),
        name="provider-claim-payout-confirm",
    ),
]
