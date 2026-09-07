"""Purchase routes, mounted at ``/api/v1/``."""

from django.urls import path

from .views import (
    PolicyPurchaseCancelView,
    PolicyPurchaseDetailView,
    PolicyPurchaseListCreateView,
    ProviderIssuanceListView,
    ProviderIssueView,
)

urlpatterns = [
    path("purchases/", PolicyPurchaseListCreateView.as_view(), name="purchase-list"),
    path("purchases/<int:pk>/", PolicyPurchaseDetailView.as_view(), name="purchase-detail"),
    path(
        "purchases/<int:pk>/cancel/",
        PolicyPurchaseCancelView.as_view(),
        name="purchase-cancel",
    ),
    # Provider issuance queue (declared distinctly from the customer routes).
    path(
        "provider/issuance/",
        ProviderIssuanceListView.as_view(),
        name="provider-issuance-list",
    ),
    path(
        "provider/issuance/<int:pk>/issue/",
        ProviderIssueView.as_view(),
        name="provider-issuance-issue",
    ),
]
