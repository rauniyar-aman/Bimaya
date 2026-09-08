"""Assistant request/response serializers."""

from rest_framework import serializers

from apps.policies.serializers import PolicyListSerializer


class RecommendationRequestSerializer(serializers.Serializer):
    """Optional criteria a customer can supply to get ranked policy picks."""

    category = serializers.CharField(
        required=False, allow_blank=True, help_text="Category slug or id."
    )
    budget_max = serializers.DecimalField(
        required=False, max_digits=12, decimal_places=2, min_value=0
    )
    age = serializers.IntegerField(required=False, min_value=0, max_value=120)
    coverage_min = serializers.DecimalField(
        required=False, max_digits=14, decimal_places=2, min_value=0
    )
    term_max = serializers.IntegerField(required=False, min_value=1)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=12)


class RecommendedPolicySerializer(PolicyListSerializer):
    """A policy card plus why it was recommended."""

    match_score = serializers.IntegerField(read_only=True)
    reasons = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )

    class Meta(PolicyListSerializer.Meta):
        fields = PolicyListSerializer.Meta.fields + ("match_score", "reasons")
        read_only_fields = fields


class ChatTurnSerializer(serializers.Serializer):
    """One prior turn in the conversation."""

    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField(trim_whitespace=True)


class ChatRequestSerializer(serializers.Serializer):
    """A single question plus optional prior turns for context."""

    message = serializers.CharField(trim_whitespace=True, max_length=2000)
    history = ChatTurnSerializer(many=True, required=False)

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError("Please enter a question.")
        return value
