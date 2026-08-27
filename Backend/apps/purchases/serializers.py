from rest_framework import serializers

from apps.policies.models import Policy
from apps.policies.serializers import PolicyListSerializer

from .models import PolicyPurchase


class PolicyPurchaseCreateSerializer(serializers.ModelSerializer):
    """Create shape for a customer buying a policy.

    ``policy`` must be public — a draft, pending or inactive-provider policy
    cannot be purchased.
    """

    policy = serializers.PrimaryKeyRelatedField(queryset=Policy.objects.all())

    class Meta:
        model = PolicyPurchase
        fields = ("id", "policy", "nominee_name", "nominee_relationship", "nominee_contact")

    def validate_policy(self, policy):
        if not policy.is_public:
            raise serializers.ValidationError("This policy is not available for purchase.")
        return policy


class PolicyPurchaseSerializer(serializers.ModelSerializer):
    """Full read shape for a purchase, with the policy nested so the frontend
    doesn't need a second request."""

    policy = PolicyListSerializer(read_only=True)

    class Meta:
        model = PolicyPurchase
        fields = (
            "id",
            "policy",
            "nominee_name",
            "nominee_relationship",
            "nominee_contact",
            "status",
            "policy_number",
            "start_date",
            "end_date",
            "renewal_reminder_sent",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields
