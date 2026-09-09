from rest_framework import serializers

from apps.documents.models import CustomerKyc
from apps.policies.models import Policy
from apps.policies.serializers import PolicyListSerializer

from .models import PolicyPurchase, ProviderPayout


class KycSummarySerializer(serializers.ModelSerializer):
    """Compact KYC shape embedded in a purchase, so the frontend can show the
    insured party and KYC status without a second request."""

    class Meta:
        model = CustomerKyc
        fields = ("id", "is_self", "full_name", "document_type", "status")
        read_only_fields = fields


class PolicyPurchaseCreateSerializer(serializers.ModelSerializer):
    """Create shape for a customer buying a policy.

    ``policy`` must be public — a draft, pending or inactive-provider policy
    cannot be purchased. A ``kyc`` record covering the insured party is required
    before payment: for a self purchase it must be the customer's own (``is_self``)
    KYC; for someone else it must be a beneficiary (``is_self=False``) record.
    """

    policy = serializers.PrimaryKeyRelatedField(queryset=Policy.objects.all())
    kyc = serializers.PrimaryKeyRelatedField(queryset=CustomerKyc.objects.all())

    class Meta:
        model = PolicyPurchase
        fields = (
            "id",
            "policy",
            "kyc",
            "insured_is_self",
            "nominee_name",
            "nominee_relationship",
            "nominee_contact",
        )

    def validate_policy(self, policy):
        if not policy.is_public:
            raise serializers.ValidationError("This policy is not available for purchase.")
        return policy

    def validate_kyc(self, kyc):
        request = self.context["request"]
        if kyc.customer_id != request.user.id:
            raise serializers.ValidationError("This KYC record does not belong to you.")
        return kyc

    def validate(self, attrs):
        kyc = attrs["kyc"]
        insured_is_self = attrs.get("insured_is_self", True)
        if insured_is_self and not kyc.is_self:
            raise serializers.ValidationError(
                {"kyc": "Buying for yourself must use your own KYC."}
            )
        if not insured_is_self and kyc.is_self:
            raise serializers.ValidationError(
                {"kyc": "Buying for someone else needs a separate KYC for them."}
            )
        return attrs


class PolicyIssueSerializer(serializers.Serializer):
    """Input for a provider issuing a forwarded purchase — just the number."""

    policy_number = serializers.CharField(max_length=30)

    def validate_policy_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("A policy number is required.")
        if PolicyPurchase.objects.filter(policy_number=value).exists():
            raise serializers.ValidationError("This policy number is already in use.")
        return value


class PolicyPurchaseSerializer(serializers.ModelSerializer):
    """Full read shape for a purchase, with the policy nested so the frontend
    doesn't need a second request."""

    policy = PolicyListSerializer(read_only=True)
    kyc = KycSummarySerializer(read_only=True)

    class Meta:
        model = PolicyPurchase
        fields = (
            "id",
            "policy",
            "kyc",
            "insured_is_self",
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


class ProviderPurchaseSerializer(PolicyPurchaseSerializer):
    """Purchase row for the provider's sales/history table.

    The base purchase shape (policy + insured KYC nested) plus the buying
    customer's name so a provider can see who bought their policy. Only the name
    is exposed — no email or other contact PII, unlike the admin serializer.
    """

    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta(PolicyPurchaseSerializer.Meta):
        fields = PolicyPurchaseSerializer.Meta.fields + ("customer_name",)
        read_only_fields = fields


class ProviderPayoutSerializer(serializers.ModelSerializer):
    """A provider's own payout row: the commission split on one issued sale, and
    whether Bimaya has settled it yet.

    Scoped to the acting provider, so the provider name is implicit and left out.
    Amounts serialize as strings (DRF's default for ``DecimalField``); the
    frontend formats them.
    """

    policy_name = serializers.CharField(source="purchase.policy.name", read_only=True)
    policy_number = serializers.CharField(
        source="purchase.policy_number", read_only=True
    )

    class Meta:
        model = ProviderPayout
        fields = (
            "id",
            "policy_name",
            "policy_number",
            "gross_amount",
            "commission_rate",
            "commission_amount",
            "net_amount",
            "status",
            "paid_at",
            "created_at",
        )
        read_only_fields = fields
