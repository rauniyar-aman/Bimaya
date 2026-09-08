from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from apps.policies.serializers import PolicyListSerializer
from apps.purchases.models import PolicyPurchase

from .models import Claim, ClaimDocument, ClaimMessage, ClaimPayout

# Statuses in which a claim is still "open" — a purchase may not have a second
# claim opened while one of these is in flight.
OPEN_CLAIM_STATUSES = (
    Claim.Status.SUBMITTED,
    Claim.Status.UNDER_REVIEW,
    Claim.Status.MORE_INFO,
    Claim.Status.APPROVED,
)


class ClaimDocumentSerializer(serializers.ModelSerializer):
    """A supporting file on a claim.

    The file itself is fetched through the authenticated download endpoint
    (``claims/<pk>/documents/<id>/``), not a raw media URL — these are sensitive
    medical/financial documents.
    """

    class Meta:
        model = ClaimDocument
        fields = ("id", "caption", "created_at")
        read_only_fields = fields


class ClaimMessageSerializer(serializers.ModelSerializer):
    """A single message in the claim thread."""

    class Meta:
        model = ClaimMessage
        fields = ("id", "author_role", "body", "created_at")
        read_only_fields = fields


class ClaimMessageCreateSerializer(serializers.Serializer):
    """Input for posting a message to a claim thread."""

    body = serializers.CharField()

    def validate_body(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Write a message before sending.")
        return value


class ClaimPurchaseSummarySerializer(serializers.ModelSerializer):
    """Compact purchase shape embedded in a claim — the policy it is against."""

    policy = PolicyListSerializer(read_only=True)

    class Meta:
        model = PolicyPurchase
        fields = ("id", "policy", "policy_number", "status")
        read_only_fields = fields


class ClaimPayoutSummarySerializer(serializers.ModelSerializer):
    """Read shape for a (simulated) payout attached to a claim."""

    class Meta:
        model = ClaimPayout
        fields = (
            "id",
            "gateway",
            "amount",
            "status",
            "gateway_reference",
            "paid_at",
            "created_at",
        )
        read_only_fields = fields


class ClaimSerializer(serializers.ModelSerializer):
    """Full read shape for a claim, with purchase + documents + payouts nested."""

    purchase = ClaimPurchaseSummarySerializer(read_only=True)
    documents = ClaimDocumentSerializer(many=True, read_only=True)
    payouts = ClaimPayoutSummarySerializer(many=True, read_only=True)
    messages = ClaimMessageSerializer(many=True, read_only=True)

    class Meta:
        model = Claim
        fields = (
            "id",
            "purchase",
            "status",
            "incident_date",
            "incident_location",
            "description",
            "claimed_amount",
            "approved_amount",
            "review_note",
            "documents",
            "payouts",
            "messages",
            "decided_at",
            "settled_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ClaimCreateSerializer(serializers.ModelSerializer):
    """Create shape (multipart) for a customer filing a claim.

    ``purchase`` must be the customer's own and ``ACTIVE``, and must not already
    have an open claim. One or more supporting ``documents`` are required — the
    repeated multipart ``documents`` parts bind to the ``ListField``.
    """

    purchase = serializers.PrimaryKeyRelatedField(queryset=PolicyPurchase.objects.all())
    documents = serializers.ListField(
        child=serializers.FileField(), allow_empty=False, write_only=True
    )

    class Meta:
        model = Claim
        fields = (
            "id",
            "purchase",
            "incident_date",
            "incident_location",
            "description",
            "claimed_amount",
            "documents",
        )

    def validate_purchase(self, purchase):
        request = self.context["request"]
        if purchase.customer_id != request.user.id:
            raise serializers.ValidationError("This policy does not belong to you.")
        if purchase.status != PolicyPurchase.Status.ACTIVE:
            raise serializers.ValidationError(
                "You can only file a claim against an active policy."
            )
        if purchase.claims.filter(status__in=OPEN_CLAIM_STATUSES).exists():
            raise serializers.ValidationError(
                "You already have an open claim on this policy."
            )
        return purchase

    def validate_claimed_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "The claimed amount must be greater than zero."
            )
        return value

    def validate(self, attrs):
        purchase = attrs["purchase"]
        incident_date = attrs["incident_date"]
        if incident_date > timezone.localdate():
            raise serializers.ValidationError(
                {"incident_date": "The incident date cannot be in the future."}
            )
        if purchase.start_date and incident_date < purchase.start_date:
            raise serializers.ValidationError(
                {"incident_date": "The incident date is before your cover started."}
            )
        return attrs

    def create(self, validated_data):
        documents = validated_data.pop("documents")
        claim = Claim.objects.create(**validated_data)
        ClaimDocument.objects.bulk_create(
            [ClaimDocument(claim=claim, file=upload) for upload in documents]
        )
        return claim


class ClaimRequestInfoSerializer(serializers.Serializer):
    """Input for a provider asking the customer for more information."""

    note = serializers.CharField()

    def validate_note(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Tell the customer what else you need.")
        return value


class ClaimApproveSerializer(serializers.Serializer):
    """Input for a provider approving a claim for a payout amount."""

    approved_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ClaimRejectSerializer(serializers.Serializer):
    """Input for a provider rejecting a claim."""

    note = serializers.CharField()

    def validate_note(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(
                "Give the customer a reason for the rejection."
            )
        return value


class ClaimPayoutInitiateSerializer(serializers.Serializer):
    """Input for starting a simulated payout — just the gateway."""

    gateway = serializers.ChoiceField(choices=ClaimPayout.Gateway.choices)


class ClaimPayoutConfirmSerializer(serializers.Serializer):
    """Input for confirming a simulated payout (the id is optional/for clarity)."""

    payout_id = serializers.IntegerField(required=False)
