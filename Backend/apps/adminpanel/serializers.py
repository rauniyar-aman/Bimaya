"""Admin-panel read/write serializers.

These are thin admin-facing shapes. Where an existing serializer already models
the right read shape (policies, purchases), the views reuse it; the serializers
here cover the admin-only lists (providers, KYC review, users) and the small
action inputs (reject-with-note).
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.documents.models import CustomerKyc
from apps.providers.models import Provider
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
            "owner_email",
            "owner_name",
            "policy_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


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
