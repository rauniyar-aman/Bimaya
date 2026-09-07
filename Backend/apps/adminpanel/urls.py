"""Admin-panel routes, mounted at ``/api/v1/admin/``."""

from django.urls import path

from .views import (
    AdminAnalyticsView,
    AdminKycDetailView,
    AdminKycDocumentView,
    AdminKycListView,
    AdminKycRejectView,
    AdminKycVerifyView,
    AdminPolicyListView,
    AdminProviderApproveView,
    AdminProviderDetailView,
    AdminProviderListView,
    AdminProviderRevokeView,
    AdminPurchaseForwardView,
    AdminPurchaseListView,
    AdminUserDetailView,
    AdminUserListView,
)

urlpatterns = [
    # Providers
    path("providers/", AdminProviderListView.as_view(), name="admin-provider-list"),
    path(
        "providers/<int:pk>/",
        AdminProviderDetailView.as_view(),
        name="admin-provider-detail",
    ),
    path(
        "providers/<int:pk>/approve/",
        AdminProviderApproveView.as_view(),
        name="admin-provider-approve",
    ),
    path(
        "providers/<int:pk>/revoke/",
        AdminProviderRevokeView.as_view(),
        name="admin-provider-revoke",
    ),
    # KYC
    path("kyc/", AdminKycListView.as_view(), name="admin-kyc-list"),
    path("kyc/<int:pk>/", AdminKycDetailView.as_view(), name="admin-kyc-detail"),
    path(
        "kyc/<int:pk>/document/front/",
        AdminKycDocumentView.as_view(side="front"),
        name="admin-kyc-document-front",
    ),
    path(
        "kyc/<int:pk>/document/back/",
        AdminKycDocumentView.as_view(side="back"),
        name="admin-kyc-document-back",
    ),
    path("kyc/<int:pk>/verify/", AdminKycVerifyView.as_view(), name="admin-kyc-verify"),
    path("kyc/<int:pk>/reject/", AdminKycRejectView.as_view(), name="admin-kyc-reject"),
    # Purchases
    path("purchases/", AdminPurchaseListView.as_view(), name="admin-purchase-list"),
    path(
        "purchases/<int:pk>/verify-and-forward/",
        AdminPurchaseForwardView.as_view(),
        name="admin-purchase-forward",
    ),
    # Users
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    # Policies
    path("policies/", AdminPolicyListView.as_view(), name="admin-policy-list"),
    # Analytics
    path("analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
]
