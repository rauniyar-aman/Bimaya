from rest_framework import serializers

from .models import Provider


class ProviderLightSerializer(serializers.ModelSerializer):
    """Minimal provider fields for embedding inside policy payloads."""

    class Meta:
        model = Provider
        fields = ("id", "company_name", "slug", "logo")


class ProviderPublicSerializer(serializers.ModelSerializer):
    """Public provider details shown on a policy."""

    class Meta:
        model = Provider
        fields = ("id", "company_name", "slug", "description", "logo", "website")


class ProviderProfileSerializer(serializers.ModelSerializer):
    """The provider's own editable profile (``/provider/profile/``).

    ``kyc_status`` and ``is_approved`` are decided by administrators and are
    therefore read-only here — a provider cannot approve itself.
    """

    class Meta:
        model = Provider
        fields = (
            "id",
            "company_name",
            "slug",
            "registration_number",
            "description",
            "logo",
            "website",
            "support_email",
            "support_phone",
            "kyc_status",
            "is_approved",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "kyc_status",
            "is_approved",
            "created_at",
            "updated_at",
        )
