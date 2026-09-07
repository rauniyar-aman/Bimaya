"""Analytics scoped to a single provider's own book of business.

Same shapes as the admin analytics (stat cards, status breakdowns, a monthly
series) but every queryset is filtered to the provider's policies, so a provider
only ever sees their own numbers. Platform-wide breakdowns (users, queues) are
deliberately omitted.
"""

from django.db.models import Sum

from apps.claims.models import Claim, ClaimPayout
from apps.core.analytics import field_breakdown, money, monthly_series, recent_months
from apps.payments.models import Payment
from apps.policies.models import Policy
from apps.purchases.models import PolicyPurchase

# How many months of history the trend charts show.
MONTHS = 6


def build_provider_analytics(provider):
    """Assemble the analytics payload scoped to ``provider``'s own policies."""
    policies = Policy.objects.filter(provider=provider)
    purchases = PolicyPurchase.objects.filter(policy__provider=provider)
    successful_payments = Payment.objects.filter(
        status=Payment.Status.SUCCESS,
        policy_purchase__policy__provider=provider,
    )
    claims = Claim.objects.filter(purchase__policy__provider=provider)
    settled_payouts = ClaimPayout.objects.filter(
        status=ClaimPayout.Status.SUCCESS,
        claim__purchase__policy__provider=provider,
    )

    premium_collected = successful_payments.aggregate(total=Sum("amount"))["total"]
    claims_settled = settled_payouts.aggregate(total=Sum("amount"))["total"]

    return {
        "stats": [
            {"key": "policies", "label": "Published policies", "value": policies.filter(status=Policy.Status.APPROVED).count(), "format": "count"},
            {"key": "purchases", "label": "Purchases", "value": purchases.count(), "format": "count"},
            {"key": "active", "label": "Active policies", "value": purchases.filter(status=PolicyPurchase.Status.ACTIVE).count(), "format": "count"},
            {"key": "premium", "label": "Premium collected", "value": money(premium_collected), "format": "currency"},
            {"key": "claims", "label": "Claims filed", "value": claims.count(), "format": "count"},
            {"key": "settled", "label": "Claims settled", "value": money(claims_settled), "format": "currency"},
        ],
        "purchases_by_status": field_breakdown(purchases, "status", PolicyPurchase.Status.choices),
        "claims_by_status": field_breakdown(claims, "status", Claim.Status.choices),
        "monthly": monthly_series(recent_months(MONTHS), purchases, successful_payments),
    }
