"""Marketplace routes, mounted at ``/api/v1/``."""

from django.urls import path

from .views import (
    CategoryDetailView,
    CategoryListView,
    PolicyCompareView,
    PolicyDetailView,
    PolicyListView,
    ProviderPolicyDetailView,
    ProviderPolicyListCreateView,
    ProviderPolicySubmitView,
)

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("categories/<slug:slug>/", CategoryDetailView.as_view(), name="category-detail"),
    # Provider self-service (declared before the public <slug> policy route).
    path(
        "provider/policies/",
        ProviderPolicyListCreateView.as_view(),
        name="provider-policy-list",
    ),
    path(
        "provider/policies/<int:pk>/",
        ProviderPolicyDetailView.as_view(),
        name="provider-policy-detail",
    ),
    path(
        "provider/policies/<int:pk>/submit/",
        ProviderPolicySubmitView.as_view(),
        name="provider-policy-submit",
    ),
    path("policies/", PolicyListView.as_view(), name="policy-list"),
    # `compare` must precede the slug route so it is not read as a slug.
    path("policies/compare/", PolicyCompareView.as_view(), name="policy-compare"),
    path("policies/<slug:slug>/", PolicyDetailView.as_view(), name="policy-detail"),
]
