"""Payment routes, mounted at ``/api/v1/``."""

from django.urls import path

from .views import PaymentCallbackView, PaymentInitiateView

urlpatterns = [
    path("payments/initiate/", PaymentInitiateView.as_view(), name="payment-initiate"),
    path(
        "payments/<str:gateway>/callback/",
        PaymentCallbackView.as_view(),
        name="payment-callback",
    ),
]
