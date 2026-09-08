from rest_framework import serializers

from .access import role_for
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
    therefore read-only here — a provider cannot approve itself. ``my_role`` is
    the acting user's role in this organisation (``OWNER``/``STAFF``/``VIEWER``),
    so the frontend can hide or disable actions their role does not allow.
    """

    my_role = serializers.SerializerMethodField()

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
            "my_role",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "kyc_status",
            "is_approved",
            "my_role",
            "created_at",
            "updated_at",
        )

    def get_my_role(self, obj) -> str | None:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return role_for(user, obj)
