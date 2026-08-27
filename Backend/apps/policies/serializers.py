from rest_framework import serializers

from apps.providers.serializers import ProviderLightSerializer, ProviderPublicSerializer

from .models import InsuranceCategory, Policy


class CategoryLightSerializer(serializers.ModelSerializer):
    """Minimal category fields for embedding inside policy payloads."""

    class Meta:
        model = InsuranceCategory
        fields = ("id", "name", "slug", "icon")


class CategorySerializer(serializers.ModelSerializer):
    """A category plus how many publicly visible policies it holds."""

    policy_count = serializers.SerializerMethodField()

    class Meta:
        model = InsuranceCategory
        fields = ("id", "name", "slug", "description", "icon", "order", "policy_count")

    def get_policy_count(self, obj) -> int:
        return Policy.objects.public().filter(category=obj).count()


class PolicyListSerializer(serializers.ModelSerializer):
    """Compact shape for policy cards and search results."""

    category = CategoryLightSerializer(read_only=True)
    provider = ProviderLightSerializer(read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "slug",
            "summary",
            "premium",
            "premium_frequency",
            "coverage_amount",
            "term_months",
            "is_featured",
            "category",
            "provider",
        )


class PolicyDetailSerializer(serializers.ModelSerializer):
    """Full policy detail for the public detail page."""

    category = CategoryLightSerializer(read_only=True)
    provider = ProviderPublicSerializer(read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "slug",
            "summary",
            "description",
            "premium",
            "premium_frequency",
            "coverage_amount",
            "term_months",
            "min_age",
            "max_age",
            "features",
            "add_ons",
            "terms",
            "is_featured",
            "category",
            "provider",
            "created_at",
        )


class PolicyCompareSerializer(serializers.ModelSerializer):
    """Normalised fields for a side-by-side comparison table."""

    category = CategoryLightSerializer(read_only=True)
    provider = ProviderLightSerializer(read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "slug",
            "summary",
            "premium",
            "premium_frequency",
            "coverage_amount",
            "term_months",
            "min_age",
            "max_age",
            "features",
            "add_ons",
            "category",
            "provider",
        )


class ProviderPolicyWriteSerializer(serializers.ModelSerializer):
    """Create/update shape for a provider managing their own policies.

    ``status`` is read-only: providers submit for review but cannot approve
    their own listings. The owning ``provider`` is taken from the request, never
    the request body.
    """

    category = serializers.PrimaryKeyRelatedField(
        queryset=InsuranceCategory.objects.filter(is_active=True)
    )
    category_detail = CategoryLightSerializer(source="category", read_only=True)

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "slug",
            "summary",
            "description",
            "category",
            "category_detail",
            "premium",
            "premium_frequency",
            "coverage_amount",
            "term_months",
            "min_age",
            "max_age",
            "features",
            "add_ons",
            "terms",
            "status",
            "is_featured",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "slug",
            "status",
            "is_featured",
            "created_at",
            "updated_at",
        )

    def validate_features(self, value):
        return self._as_string_list(value, "Features")

    def validate_add_ons(self, value):
        return self._as_string_list(value, "Add-ons")

    @staticmethod
    def _as_string_list(value, label):
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError(f"{label} must be a list of text items.")
        return value
