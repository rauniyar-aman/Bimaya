from django.contrib.auth import get_user_model
from rest_framework import serializers

from .access import provider_permissions, role_for
from .models import Provider
from .rbac import ProviderRole

User = get_user_model()

# A provider's company logo is capped server-side; the browser's own check is
# only a convenience. Mirrors the customer avatar cap in ``apps.accounts``.
LOGO_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


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

    ``kyc_status``, ``is_approved`` and ``commission_rate`` are decided by
    administrators and are therefore read-only here — a provider cannot approve
    itself or set its own commission. ``public_id`` is the human-readable
    organisation identifier (``PRV-00142``). ``my_role`` and ``my_permissions``
    describe the acting user's role in this organisation and the granular
    permissions it grants, so the frontend can hide or disable the actions their
    role does not allow.
    """

    public_id = serializers.CharField(read_only=True)
    logo = serializers.ImageField(required=False, allow_null=True)
    my_role = serializers.SerializerMethodField()
    my_permissions = serializers.SerializerMethodField()

    class Meta:
        model = Provider
        fields = (
            "id",
            "public_id",
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
            "commission_rate",
            "my_role",
            "my_permissions",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "public_id",
            "slug",
            "kyc_status",
            "is_approved",
            "commission_rate",
            "my_role",
            "my_permissions",
            "created_at",
            "updated_at",
        )

    def get_my_role(self, obj) -> str | None:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return role_for(user, obj)

    def validate_logo(self, image):
        if image is not None and image.size > LOGO_MAX_BYTES:
            raise serializers.ValidationError(
                "That image is over 5 MB. Please choose a smaller file."
            )
        return image

    def get_my_permissions(self, obj) -> list[str]:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return sorted(provider_permissions(user, obj))


class ProviderRoleRefSerializer(serializers.Serializer):
    """A member's role as ``{value, label}`` for display in the team table."""

    value = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)


class ProviderMemberSerializer(serializers.Serializer):
    """One person in the acting user's provider organisation.

    A uniform people-list row shaped in the view (:meth:`~apps.providers.views.
    ProviderMemberBase._member_rows`): the owner (``membership_id`` null, role
    ``OWNER``) and each added member with their assignable role, so the provider
    portal renders the whole team from one shape. ``permissions`` is what the
    role grants, so the UI can show each member's reach.
    """

    user_id = serializers.IntegerField(read_only=True)
    membership_id = serializers.IntegerField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True, allow_blank=True)
    role = ProviderRoleRefSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    permissions = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )


class ProviderMemberCreateSerializer(serializers.Serializer):
    """A provider Owner / Company Admin adds a member to their own organisation.

    Creates a verified provider-role account with a temporary password and links
    it to the caller's organisation; the person signs in with the normal login +
    OTP. Only the assignable roles are accepted — the owner is set at onboarding.
    """

    email = serializers.EmailField()
    full_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    password = serializers.CharField(
        write_only=True, min_length=8, trim_whitespace=False
    )
    role = serializers.ChoiceField(choices=ProviderRole.choices)

    def validate_email(self, value):
        value = value.strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class ProviderMemberRoleSerializer(serializers.Serializer):
    """Change an existing member's assignable role."""

    role = serializers.ChoiceField(choices=ProviderRole.choices)
