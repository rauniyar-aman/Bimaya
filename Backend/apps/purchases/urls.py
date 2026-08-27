"""Purchase routes, mounted at ``/api/v1/``."""

from django.urls import path

from .views import (
    PolicyPurchaseCancelView,
    PolicyPurchaseDetailView,
    PolicyPurchaseListCreateView,
)

urlpatterns = [
    path("purchases/", PolicyPurchaseListCreateView.as_view(), name="purchase-list"),
    path("purchases/<int:pk>/", PolicyPurchaseDetailView.as_view(), name="purchase-detail"),
    path(
        "purchases/<int:pk>/cancel/",
        PolicyPurchaseCancelView.as_view(),
        name="purchase-cancel",
    ),
]
