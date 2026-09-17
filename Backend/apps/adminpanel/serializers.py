"""Admin-panel read/write serializers.

These are thin admin-facing shapes. Where an existing serializer already models
the right read shape (policies, purchases), the views reuse it; the serializers
here cover the admin-only lists (providers, KYC review, users) and the small
action inputs (reject-with-note).
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework import serializers

from apps.claims.models import Claim
from apps.documents.models import CustomerKyc
from apps.documents.serializers import ProviderKycSerializer
from apps.policies.models import Policy
from apps.policies.serializers import PolicyListSerializer
from apps.providers.models import Provider, ProviderRole
from apps.providers.rbac import OWNER
from apps.purchases.models import PolicyPurchase, ProviderPayout
from apps.purchases.serializers import PolicyPurchaseSerializer

User = get_user_model()


class AdminProviderSerializer(serializers.ModelSerializer):
    """Provider row for the admin approvals table, with the owning account.

    ``public_id`` is the human-readable organisation identifier (``PRV-00142``),
    derived from the primary key.
    """

    public_id = serializers.CharField(read_only=True)
    owner_email = serializers.EmailField(source="user.email", read_only=True)
    owner_name = serializers.CharField(source="user.full_name", read_only=True)
    policy_count = serializers.IntegerField(read_only=True)

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
            "owner_email",
            "owner_name",
            "policy_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class _ProviderPolicyRowSerializer(serializers.ModelSerializer):
    """Compact policy row for a provider's detail page."""

    class Meta:
        model = Policy
        fields = (
            "id",
            "name",
            "slug",
            "status",
            "premium",
            "premium_frequency",
            "coverage_amount",
            "created_at",
        )
        read_only_fields = fields


class AdminProviderDetailSerializer(AdminProviderSerializer):
    """A single provider with its team, KYC, recent policies and summary counts.

    The list view keeps the lean :class:`AdminProviderSerializer`; this is the
    detail shape. The full blow-by-blow (every event, in order) lives in the
    history timeline, so the nested lists here stay bounded snapshots.
    """

    memberships = serializers.SerializerMethodField()
    kyc_documents = serializers.SerializerMethodField()
    recent_policies = serializers.SerializerMethodField()
    active_policies = serializers.SerializerMethodField()
    purchase_count = serializers.SerializerMethodField()
    payout_net_total = serializers.SerializerMethodField()
    pending_claims = serializers.SerializerMethodField()

    class Meta(AdminProviderSerializer.Meta):
        fields = AdminProviderSerializer.Meta.fields + (
            "memberships",
            "kyc_documents",
            "recent_policies",
            "active_policies",
            "purchase_count",
            "payout_net_total",
            "pending_claims",
        )
        read_only_fields = fields

    def get_memberships(self, obj):
        # Mirrors AdminProviderMemberListCreateView's member list: the owner
        # (Provider.user, implicit OWNER role, no membership row) followed by
        # each added membership, as one uniform people list.
        owner = obj.user
        rows = [
            {
                "user_id": owner.id,
                "membership_id": None,
                "email": owner.email,
                "full_name": owner.full_name,
                "role": OWNER,
                "is_active": owner.is_active,
                "date_joined": owner.date_joined,
            }
        ]
        rows.extend(
            {
                "user_id": member.user.id,
                "membership_id": member.id,
                "email": member.user.email,
                "full_name": member.user.full_name,
                "role": member.role,
                "is_active": member.user.is_active,
                "date_joined": member.user.date_joined,
            }
            for member in obj.memberships.select_related("user").all()
        )
        return ProviderMemberSerializer(rows, many=True).data

    def get_kyc_documents(self, obj):
        documents = obj.kyc_documents.select_related("uploaded_by").order_by(
            "-created_at"
        )
        return ProviderKycSerializer(documents, many=True).data

    def get_recent_policies(self, obj):
        policies = obj.policies.order_by("-created_at")[:10]
        return _ProviderPolicyRowSerializer(policies, many=True).data

    def get_active_policies(self, obj) -> int:
        return obj.policies.filter(status=Policy.Status.APPROVED).count()

    def get_purchase_count(self, obj) -> int:
        return PolicyPurchase.objects.filter(policy__provider=obj).count()

    def get_payout_net_total(self, obj) -> str:
        total = obj.payouts.aggregate(total=Sum("net_amount"))["total"] or Decimal("0")
        return str(total.quantize(Decimal("0.00")))

    def get_pending_claims(self, obj) -> int:
        open_states = (
            Claim.Status.SUBMITTED,
            Claim.Status.UNDER_REVIEW,
            Claim.Status.MORE_INFO,
        )
        return Claim.objects.for_provider(obj).filter(status__in=open_states).count()


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


class _UserKycRowSerializer(serializers.ModelSerializer):
    """Compact KYC row for a user's detail page."""

    class Meta:
        model = CustomerKyc
        fields = (
            "id",
            "is_self",
            "document_type",
            "full_name",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class _UserPurchaseRowSerializer(serializers.ModelSerializer):
    """Compact purchase row for a user's detail page."""

    policy_name = serializers.CharField(source="policy.name", read_only=True)

    class Meta:
        model = PolicyPurchase
        fields = (
            "id",
            "policy_name",
            "status",
            "policy_number",
            "start_date",
            "end_date",
            "created_at",
        )
        read_only_fields = fields


class _UserClaimRowSerializer(serializers.ModelSerializer):
    """Compact claim row for a user's detail page."""

    policy_name = serializers.CharField(source="purchase.policy.name", read_only=True)

    class Meta:
        model = Claim
        fields = (
            "id",
            "policy_name",
            "status",
            "claimed_amount",
            "approved_amount",
            "created_at",
            "decided_at",
            "settled_at",
        )
        read_only_fields = fields


class AdminUserDetailSerializer(AdminUserSerializer):
    """A single user with activity counts and their recent records.

    The full blow-by-blow (every event, in order) lives in the history timeline;
    these nested lists are bounded snapshots for the detail page's cards.
    """

    purchase_count = serializers.IntegerField(read_only=True)
    claim_count = serializers.IntegerField(read_only=True)
    avatar = serializers.SerializerMethodField()
    last_login = serializers.DateTimeField(read_only=True)
    kyc_records = serializers.SerializerMethodField()
    recent_purchases = serializers.SerializerMethodField()
    recent_claims = serializers.SerializerMethodField()

    class Meta(AdminUserSerializer.Meta):
        fields = AdminUserSerializer.Meta.fields + (
            "avatar",
            "last_login",
            "purchase_count",
            "claim_count",
            "kyc_records",
            "recent_purchases",
            "recent_claims",
        )
        read_only_fields = fields

    def get_avatar(self, obj) -> str | None:
        return obj.avatar.url if obj.avatar else None

    def get_kyc_records(self, obj):
        records = obj.kyc_records.all().order_by("-created_at")[:10]
        return _UserKycRowSerializer(records, many=True).data

    def get_recent_purchases(self, obj):
        purchases = (
            obj.policy_purchases.select_related("policy").order_by("-created_at")[:10]
        )
        return _UserPurchaseRowSerializer(purchases, many=True).data

    def get_recent_claims(self, obj):
        claims = (
            obj.claims.select_related("purchase__policy").order_by("-created_at")[:10]
        )
        return _UserClaimRowSerializer(claims, many=True).data


class RejectNoteSerializer(serializers.Serializer):
    """Input for a reject-with-reason action (customer or provider KYC)."""

    note = serializers.CharField()

    def validate_note(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Give a reason for the rejection.")
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
# (it is ``Provider.user``) and is never created through the members API. These
# are exactly the assignable provider roles (:class:`~apps.providers.rbac.ProviderRole`);
# ``OWNER`` is an implicit sentinel, never assigned here.
MEMBER_ROLE_CHOICES = ProviderRole.choices


class ProviderMemberSerializer(serializers.Serializer):
    """One person in a provider organisation — the owner or an added member.

    A uniform people-list row: the owner (``membership_id`` null, role
    ``OWNER``) and each added membership with its assignable role, so the admin
    UI can render the whole team from a single shape.
    """

    user_id = serializers.IntegerField(read_only=True)
    membership_id = serializers.IntegerField(read_only=True, allow_null=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True, allow_blank=True)
    role = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)


class ProviderMemberCreateSerializer(serializers.Serializer):
    """Admin input to add a member to a provider organisation.

    Creates a verified provider-role account with a temporary password and links
    it to the organisation; the person signs in with the normal login + OTP.
    Only the assignable roles are accepted — owners are set at onboarding.
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
    """Admin input to change an existing member's assignable role."""

    role = serializers.ChoiceField(choices=MEMBER_ROLE_CHOICES)


class AdminHistoryEventSerializer(serializers.Serializer):
    """One event in a subject's merged activity + admin-action timeline.

    A read-only shape matching the dicts emitted by
    :mod:`apps.adminpanel.history`. ``source`` is ``"activity"`` (the subject's
    own record) or ``"admin"`` (an administrator's action on them); ``amount`` is
    a pre-formatted string or null.
    """

    id = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(read_only=True)
    source = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    action = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    detail = serializers.CharField(read_only=True, allow_blank=True)
    status = serializers.CharField(read_only=True, allow_blank=True)
    actor = serializers.CharField(read_only=True, allow_blank=True)
    amount = serializers.CharField(read_only=True, allow_null=True)
    ref_type = serializers.CharField(read_only=True, allow_blank=True)
    ref_id = serializers.CharField(read_only=True, allow_blank=True)
