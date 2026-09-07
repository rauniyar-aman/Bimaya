"""Platform-wide analytics for the admin dashboard.

A single read-only aggregate across every app's data: headline stat cards, a few
breakdowns for the bar charts, the action queues, and a recent monthly series.
Everything is computed with ORM aggregates — there is no analytics model.
"""

from django.contrib.auth import get_user_model
from django.db.models import Sum

from apps.claims.models import Claim, ClaimPayout
from apps.core.analytics import field_breakdown, money, monthly_series, recent_months
from apps.documents.models import CustomerKyc
from apps.payments.models import Payment
from apps.policies.models import Policy
from apps.providers.models import Provider
from apps.purchases.models import PolicyPurchase

User = get_user_model()

# How many months of history the trend charts show.
MONTHS = 6


def build_admin_analytics():
    """Assemble the platform analytics payload for the admin dashboard."""
    purchases = PolicyPurchase.objects.all()
    successful_payments = Payment.objects.filter(status=Payment.Status.SUCCESS)
    settled_payouts = ClaimPayout.objects.filter(status=ClaimPayout.Status.SUCCESS)

    providers_total = Provider.objects.count()
    providers_approved = Provider.objects.filter(is_approved=True).count()
    providers_pending = providers_total - providers_approved
    premium_collected = successful_payments.aggregate(total=Sum("amount"))["total"]
    claims_settled = settled_payouts.aggregate(total=Sum("amount"))["total"]

    return {
        "stats": [
            {"key": "users", "label": "Users", "value": User.objects.count(), "format": "count"},
            {"key": "providers", "label": "Approved providers", "value": providers_approved, "format": "count"},
            {"key": "policies", "label": "Published policies", "value": Policy.objects.filter(status=Policy.Status.APPROVED).count(), "format": "count"},
            {"key": "purchases", "label": "Purchases", "value": purchases.count(), "format": "count"},
            {"key": "premium", "label": "Premium collected", "value": money(premium_collected), "format": "currency"},
            {"key": "settled", "label": "Claims settled", "value": money(claims_settled), "format": "currency"},
        ],
        "users_by_role": field_breakdown(User.objects.all(), "role", User.Role.choices),
        "providers": {
            "total": providers_total,
            "approved": providers_approved,
            "pending": providers_pending,
        },
        "queues": {
            "pending_providers": providers_pending,
            "pending_kyc": CustomerKyc.objects.filter(status=CustomerKyc.Status.PENDING).count(),
            "paid_purchases": purchases.filter(status=PolicyPurchase.Status.PAID).count(),
        },
        "purchases_by_status": field_breakdown(purchases, "status", PolicyPurchase.Status.choices),
        "claims_by_status": field_breakdown(Claim.objects.all(), "status", Claim.Status.choices),
        "monthly": monthly_series(recent_months(MONTHS), purchases, successful_payments),
    }
