"""Admin-panel routes, mounted at ``/api/v1/admin/``."""

from django.urls import path

from .views import (
    AdminAnalyticsView,
    AdminKycDetailView,
    AdminKycDocumentView,
    AdminKycListView,
    AdminKycRejectView,
    AdminKycVerifyView,
    AdminPayoutListView,
    AdminPayoutReportView,
    AdminPolicyApproveView,
    AdminPolicyDeactivateView,
    AdminPolicyListView,
    AdminPolicyRejectView,
    AdminPolicyReportView,
    AdminProviderApproveView,
    AdminProviderDetailView,
    AdminProviderHistoryView,
    AdminProviderListView,
    AdminProviderMemberDetailView,
    AdminProviderMemberListCreateView,
    AdminProviderKycDocumentView,
    AdminProviderKycListView,
    AdminProviderKycRejectView,
    AdminProviderKycVerifyView,
    AdminProviderReportView,
    AdminProviderRevokeView,
    AdminProviderSetCommissionView,
    AdminPurchaseForwardView,
    AdminPurchaseListView,
    AdminPurchaseReportView,
    AdminUserDetailView,
    AdminUserHistoryView,
    AdminUserListView,
    AdminUserReactivateView,
    AdminUserReportView,
    AdminUserSuspendView,
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
        "providers/<int:pk>/history/",
        AdminProviderHistoryView.as_view(),
        name="admin-provider-history",
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
    path(
        "providers/<int:pk>/commission/",
        AdminProviderSetCommissionView.as_view(),
        name="admin-provider-commission",
    ),
    path(
        "providers/<int:pk>/members/",
        AdminProviderMemberListCreateView.as_view(),
        name="admin-provider-members",
    ),
    path(
        "providers/<int:pk>/members/<int:membership_pk>/",
        AdminProviderMemberDetailView.as_view(),
        name="admin-provider-member-detail",
    ),
    # Provider KYC documents
    path(
        "providers/<int:pk>/kyc/",
        AdminProviderKycListView.as_view(),
        name="admin-provider-kyc-list",
    ),
    path(
        "providers/<int:pk>/kyc/<int:document_pk>/document/",
        AdminProviderKycDocumentView.as_view(),
        name="admin-provider-kyc-document",
    ),
    path(
        "providers/<int:pk>/kyc/<int:document_pk>/verify/",
        AdminProviderKycVerifyView.as_view(),
        name="admin-provider-kyc-verify",
    ),
    path(
        "providers/<int:pk>/kyc/<int:document_pk>/reject/",
        AdminProviderKycRejectView.as_view(),
        name="admin-provider-kyc-reject",
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
    # Provider payouts
    path("payouts/", AdminPayoutListView.as_view(), name="admin-payout-list"),
    # Users
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("users/<int:pk>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path(
        "users/<int:pk>/history/",
        AdminUserHistoryView.as_view(),
        name="admin-user-history",
    ),
    path(
        "users/<int:pk>/suspend/",
        AdminUserSuspendView.as_view(),
        name="admin-user-suspend",
    ),
    path(
        "users/<int:pk>/reactivate/",
        AdminUserReactivateView.as_view(),
        name="admin-user-reactivate",
    ),
    # Policies
    path("policies/", AdminPolicyListView.as_view(), name="admin-policy-list"),
    path(
        "policies/<int:pk>/approve/",
        AdminPolicyApproveView.as_view(),
        name="admin-policy-approve",
    ),
    path(
        "policies/<int:pk>/reject/",
        AdminPolicyRejectView.as_view(),
        name="admin-policy-reject",
    ),
    path(
        "policies/<int:pk>/deactivate/",
        AdminPolicyDeactivateView.as_view(),
        name="admin-policy-deactivate",
    ),
    # Analytics
    path("analytics/", AdminAnalyticsView.as_view(), name="admin-analytics"),
    # Reports (CSV export)
    path(
        "reports/providers/",
        AdminProviderReportView.as_view(),
        name="admin-report-providers",
    ),
    path(
        "reports/users/",
        AdminUserReportView.as_view(),
        name="admin-report-users",
    ),
    path(
        "reports/policies/",
        AdminPolicyReportView.as_view(),
        name="admin-report-policies",
    ),
    path(
        "reports/purchases/",
        AdminPurchaseReportView.as_view(),
        name="admin-report-purchases",
    ),
    path(
        "reports/payouts/",
        AdminPayoutReportView.as_view(),
        name="admin-report-payouts",
    ),
]
