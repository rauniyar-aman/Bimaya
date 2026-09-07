"""Provider lead routes, mounted at ``/api/v1/``."""

from django.urls import path

from .views import ProviderLeadCreateView

urlpatterns = [
    path(
        "provider-leads/",
        ProviderLeadCreateView.as_view(),
        name="provider-lead-create",
    ),
]
