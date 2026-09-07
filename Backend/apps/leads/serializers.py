from rest_framework import serializers

from .models import ProviderLead


class ProviderLeadCreateSerializer(serializers.ModelSerializer):
    """Public enquiry shape. Only these fields are client-supplied; ``status``
    is decided by administrators."""

    class Meta:
        model = ProviderLead
        fields = ("id", "company_name", "contact_name", "email", "phone", "message")
        read_only_fields = ("id",)
