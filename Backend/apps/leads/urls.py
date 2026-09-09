"""Provider lead routes, mounted at ``/api/v1/``."""

from django.urls import path

from .views import ContactLeadCreateView, ProviderLeadCreateView

urlpatterns = [
    path(
        "provider-leads/",
        ProviderLeadCreateView.as_view(),
        name="provider-lead-create",
    ),
    path(
        "contact-enquiries/",
        ContactLeadCreateView.as_view(),
        name="contact-lead-create",
    ),
]
