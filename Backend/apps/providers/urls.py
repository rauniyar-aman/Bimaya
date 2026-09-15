"""Provider portal routes, mounted at ``/api/v1/provider/``.

The company's own backend: profile, analytics, self-service team management and
KYC documents. Organisation scope is always derived from the signed-in user, so
none of these routes carry a provider id.
"""

from django.urls import path

from .views import (
    ProviderAnalyticsView,
    ProviderKycDeleteView,
    ProviderKycDownloadView,
    ProviderKycListCreateView,
    ProviderMemberDetailView,
    ProviderMemberDisableView,
    ProviderMemberEnableView,
    ProviderMemberListCreateView,
    ProviderMemberRoleView,
    ProviderProfileView,
    ProviderRolesCatalogView,
)

urlpatterns = [
    path("provider/profile/", ProviderProfileView.as_view(), name="provider-profile"),
    path(
        "provider/analytics/",
        ProviderAnalyticsView.as_view(),
        name="provider-analytics",
    ),
    # Self-service team management (owner / Company Admin).
    path(
        "provider/members/",
        ProviderMemberListCreateView.as_view(),
        name="provider-member-list",
    ),
    path(
        "provider/members/<int:pk>/",
        ProviderMemberDetailView.as_view(),
        name="provider-member-detail",
    ),
    path(
        "provider/members/<int:pk>/role/",
        ProviderMemberRoleView.as_view(),
        name="provider-member-role",
    ),
    path(
        "provider/members/<int:pk>/disable/",
        ProviderMemberDisableView.as_view(),
        name="provider-member-disable",
    ),
    path(
        "provider/members/<int:pk>/enable/",
        ProviderMemberEnableView.as_view(),
        name="provider-member-enable",
    ),
    path(
        "provider/roles/",
        ProviderRolesCatalogView.as_view(),
        name="provider-roles",
    ),
    # KYC documents.
    path(
        "provider/kyc-documents/",
        ProviderKycListCreateView.as_view(),
        name="provider-kyc-list",
    ),
    path(
        "provider/kyc-documents/<int:pk>/",
        ProviderKycDeleteView.as_view(),
        name="provider-kyc-delete",
    ),
    path(
        "provider/kyc-documents/<int:pk>/download/",
        ProviderKycDownloadView.as_view(),
        name="provider-kyc-download",
    ),
]
