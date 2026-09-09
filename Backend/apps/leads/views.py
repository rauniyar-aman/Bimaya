"""Public provider-onboarding enquiry endpoint (``/api/v1/provider-leads/``)."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import ContactLeadCreateSerializer, ProviderLeadCreateSerializer
from .services import notify_admin_of_lead

LEAD_TAG = ["leads"]


@extend_schema(
    tags=LEAD_TAG,
    summary="Submit a provider onboarding enquiry",
    description=(
        "Public form from the 'For insurance providers' page. Records the lead "
        "and notifies the admin, who reviews and onboards the provider manually. "
        "This does not create any account."
    ),
)
class ProviderLeadCreateView(CreateAPIView):
    serializer_class = ProviderLeadCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()
        notify_admin_of_lead(lead)
        return Response(
            {
                "detail": (
                    "Thanks — we have received your enquiry. Our team will "
                    "review it and get in touch soon."
                )
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    tags=LEAD_TAG,
    summary="Submit a contact enquiry",
    description=(
        "Public form from the 'Contact' page. Records a general enquiry and "
        "notifies the admin. This does not create any account."
    ),
)
class ContactLeadCreateView(CreateAPIView):
    serializer_class = ContactLeadCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lead = serializer.save()
        notify_admin_of_lead(lead)
        return Response(
            {
                "detail": (
                    "Thanks for reaching out — we have received your message "
                    "and will get back to you soon."
                )
            },
            status=status.HTTP_201_CREATED,
        )
