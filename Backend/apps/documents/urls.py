"""Customer KYC routes, mounted at ``/api/v1/``."""

from django.urls import path

from .views import BeneficiaryKycCreateView, SelfKycView

urlpatterns = [
    path("kyc/self/", SelfKycView.as_view(), name="kyc-self"),
    path("kyc/beneficiary/", BeneficiaryKycCreateView.as_view(), name="kyc-beneficiary"),
]
