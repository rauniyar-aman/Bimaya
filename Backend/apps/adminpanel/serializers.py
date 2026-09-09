"""Admin-panel read/write serializers.

These are thin admin-facing shapes. Where an existing serializer already models
the right read shape (policies, purchases), the views reuse it; the serializers
here cover the admin-only lists (providers, KYC review, users) and the small
action inputs (reject-with-note).
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.documents.models import CustomerKyc
from apps.policies.serializers import PolicyListSerializer
from apps.providers.models import Provider, ProviderRole
from apps.purchases.models import ProviderPayout
from apps.purchases.serializers import PolicyPurchaseSerializer

User = get_user_model()


class AdminProviderSerializer(serializers.ModelSerializer):
    """Provider row for the admin approvals table, with the owning account."""

    owner_email = serializers.EmailField(source="user.email", read_only=True)
    owner_name = serializers.CharField(source="user.full_name", read_only=True)
    policy_count = serializers.IntegerField(read_only=True)

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
            "commission_rate",
            "owner_email",
            "owner_name",
            "policy_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AdminProviderCommissionSerializer(serializers.Serializer):
    """Admin input to set a provider's platform commission rate (percent)."""

    commission_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=0, max_value=100
    )


class AdminKycSerializer(serializers.ModelSerializer):
    """Full KYC record for admin review.

    Document images are referenced by the authenticated download endpoints
    (``/admin/kyc/<pk>/document/front|back/``), never as raw media URLs — these
    are PII. Only the availability flags are exposed here.
    """

    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    has_front = serializers.SerializerMethodField()
    has_back = serializers.SerializerMethodField()

    class Meta:
        model = CustomerKyc
        fields = (
            "id",
            "customer_email",
            "is_self",
            "full_name",
            "email",
            "phone",
            "date_of_birth",
            "marital_status",
            "family_details",
            "temporary_address",
            "permanent_address",
            "document_type",
            "document_number",
            "has_front",
            "has_back",
            "status",
            "review_note",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_has_front(self, obj) -> bool:
        return bool(obj.document_front)

    def get_has_back(self, obj) -> bool:
        return bool(obj.document_back)


class AdminUserSerializer(serializers.ModelSerializer):
    """User row for the admin users table."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "is_active",
            "is_verified",
            "date_joined",
        )
        read_only_fields = fields


class AdminUserDetailSerializer(AdminUserSerializer):
    """A single user with activity counts."""

    purchase_count = serializers.IntegerField(read_only=True)
    claim_count = serializers.IntegerField(read_only=True)

    class Meta(AdminUserSerializer.Meta):
        fields = AdminUserSerializer.Meta.fields + (
            "purchase_count",
            "claim_count",
        )
        read_only_fields = fields


class RejectNoteSerializer(serializers.Serializer):
    """Input for a reject-with-reason action (KYC)."""

    note = serializers.CharField()

    def validate_note(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Give the customer a reason.")
        return value


class AdminPurchaseSerializer(PolicyPurchaseSerializer):
    """Purchase row for the admin verification table.

    The customer-facing purchase shape (policy + insured KYC nested) plus the
    buying customer, so an administrator verifying a payment can see who paid
    without a second request.
    """

    customer_email = serializers.EmailField(source="customer.email", read_only=True)
    customer_name = serializers.CharField(source="customer.full_name", read_only=True)

    class Meta(PolicyPurchaseSerializer.Meta):
        fields = PolicyPurchaseSerializer.Meta.fields + (
            "customer_email",
            "customer_name",
        )
        read_only_fields = fields


class AdminPayoutSerializer(serializers.ModelSerializer):
    """Provider payout row for the admin payouts table."""

    provider_name = serializers.CharField(
        source="provider.company_name", read_only=True
    )
    policy_name = serializers.CharField(source="purchase.policy.name", read_only=True)
    policy_number = serializers.CharField(
        source="purchase.policy_number", read_only=True
    )

    class Meta:
        model = ProviderPayout
        fields = (
            "id",
            "provider_name",
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


class AdminPolicySerializer(PolicyListSerializer):
    """Policy row for the admin all-policies table.

    The public card shape plus ``status`` so an administrator can see and drive
    each policy through review from the branded ``/admin`` UI.
    """

    class Meta(PolicyListSerializer.Meta):
        fields = PolicyListSerializer.Meta.fields + ("status", "created_at")
        read_only_fields = fields


# Roles an admin may assign to an added member — the owner is set at onboarding
# (it is ``Provider.user``) and is never created through the members API.
MEMBER_ROLE_CHOICES = (
    (ProviderRole.STAFF.value, ProviderRole.STAFF.label),
    (ProviderRole.VIEWER.value, ProviderRole.VIEWER.label),
)


class ProviderMemberSerializer(serializers.Serializer):
    """One person in a provider organisation — the owner or an added member.

    A uniform people-list row: the owner (``membership_id`` null, role
    ``OWNER``) and each staff/viewer membership, so the admin UI can render the
    whole team from a single shape.
    """

    user_id = serializers.IntegerField(read_only=True)
    membership_id = serializers.IntegerField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True, allow_blank=True)
    role = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)


class ProviderMemberCreateSerializer(serializers.Serializer):
    """Admin input to add a staff/viewer to a provider organisation.

    Creates a verified provider-role account with a temporary password and links
    it to the organisation; the person signs in with the normal login + OTP.
    Only staff/viewer roles are accepted — owners are set at onboarding.
    """

    email = serializers.EmailField()
    full_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    password = serializers.CharField(
        write_only=True, min_length=8, trim_whitespace=False
    )
    role = serializers.ChoiceField(choices=MEMBER_ROLE_CHOICES)

    def validate_email(self, value):
        value = value.strip()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class ProviderMemberRoleSerializer(serializers.Serializer):
    """Admin input to change an existing member's role (staff ↔ viewer)."""

    role = serializers.ChoiceField(choices=MEMBER_ROLE_CHOICES)
