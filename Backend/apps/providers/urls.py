"""Provider profile routes, mounted at ``/api/v1/provider/``."""

from django.urls import path

from .views import ProviderProfileView

urlpatterns = [
    path("provider/profile/", ProviderProfileView.as_view(), name="provider-profile"),
]
