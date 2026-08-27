from rest_framework import serializers

from apps.purchases.models import PolicyPurchase

from .models import Payment


class PaymentInitiateSerializer(serializers.Serializer):
    """Input for ``POST /payments/initiate/``."""

    policy_purchase_id = serializers.PrimaryKeyRelatedField(
        source="policy_purchase", queryset=PolicyPurchase.objects.all()
    )
    gateway = serializers.ChoiceField(choices=Payment.Gateway.choices)

    def validate_policy_purchase_id(self, purchase):
        request = self.context["request"]
        if purchase.customer_id != request.user.id:
            raise serializers.ValidationError("This purchase does not belong to you.")
        if purchase.status != PolicyPurchase.Status.PENDING_PAYMENT:
            raise serializers.ValidationError("This purchase is not awaiting payment.")
        return purchase
