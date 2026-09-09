from rest_framework import serializers

from .models import ProviderLead


class ProviderLeadCreateSerializer(serializers.ModelSerializer):
    """Public provider-onboarding enquiry shape. Only these fields are
    client-supplied; ``status`` is decided by administrators and ``kind``
    defaults to ``PROVIDER``.

    ``company_name`` is blank-able on the model (so contact enquiries can share
    the table) but is required here — an onboarding enquiry must name a company.
    """

    company_name = serializers.CharField(max_length=150)

    class Meta:
        model = ProviderLead
        fields = ("id", "company_name", "contact_name", "email", "phone", "message")
        read_only_fields = ("id",)


class ContactLeadCreateSerializer(serializers.ModelSerializer):
    """Public contact-page enquiry shape. Has no company; persisted with
    ``kind=CONTACT`` so admins can tell it apart from onboarding requests."""

    class Meta:
        model = ProviderLead
        fields = ("id", "contact_name", "email", "phone", "message")
        read_only_fields = ("id",)

    def create(self, validated_data):
        validated_data["kind"] = ProviderLead.Kind.CONTACT
        return super().create(validated_data)
