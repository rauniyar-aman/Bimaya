"""Assemble a subject's full history for the admin detail pages.

Read-only functions that merge a customer's or provider's own activity (read
from the domain records) with the administrative actions taken on them (read
from the append-only audit log) into one chronological timeline. There are no
new models and no migrations — this only reads existing tables.

Two rules keep the two sources from double-listing each other:

* **Activity** is sourced from the domain records themselves (purchases,
  payments, claims, KYC, policies, memberships, payouts). These are complete
  for all existing data, including anything created before self-service audit
  logging was added.
* **Admin actions** are sourced from :class:`~apps.staff.models.AuditLogEntry`
  filtered to ``actor_role == ADMIN``. Self-service audit rows (a customer
  buying, a provider issuing) carry a non-admin ``actor_role`` and so never
  appear here — they are already represented by their own domain record.

Each builder returns a list of normalised event dicts sorted newest-first; the
view paginates them.
"""

from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from apps.claims.models import Claim, ClaimMessage
from apps.payments.models import Payment
from apps.purchases.models import PolicyPurchase
from apps.staff.models import AuditLogEntry
from apps.staff.rbac import Perm

User = get_user_model()

# Each per-subject query is capped so timeline assembly stays bounded in memory;
# the endpoint paginates the merged result. Comfortably above real per-subject
# volumes at marketplace scale.
PER_SOURCE_LIMIT = 200

ADMIN = User.Role.ADMIN


def _as_datetime(value):
    """Coerce a date or datetime to a timezone-aware datetime, for sorting."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value
    # A plain date (start_date, incident_date, ...): anchor it at midnight.
    return timezone.make_aware(
        datetime.combine(value, time.min), timezone.get_current_timezone()
    )


# Fallback sort key for the (theoretically impossible) event with no timestamp,
# so sorting never raises on a mixed None.
_EPOCH = _as_datetime(datetime(1970, 1, 1))


def _event(
    *,
    event_id,
    timestamp,
    source,
    category,
    action,
    title,
    detail="",
    status="",
    actor="",
    amount=None,
    ref_type="",
    ref_id="",
):
    """Build one normalised timeline event."""
    return {
        "id": event_id,
        "timestamp": _as_datetime(timestamp),
        "source": source,
        "category": category,
        "action": action,
        "title": title,
        "detail": detail or "",
        "status": status or "",
        "actor": actor or "",
        "amount": None if amount is None else str(amount),
        "ref_type": ref_type,
        "ref_id": "" if ref_id in (None, "") else str(ref_id),
    }


# --- Admin-action events (from the audit log) -------------------------------

_ADMIN_TITLES = {
    Perm.PROVIDER_APPROVE: "Provider approved",
    Perm.PROVIDER_SUSPEND: "Provider approval revoked",
    Perm.COMMISSION_MANAGE: "Commission rate changed",
    Perm.PROVIDER_EDIT: "Provider team updated",
    Perm.PROVIDER_KYC_REVIEW: "Provider KYC document reviewed",
    Perm.KYC_DOCUMENT_VIEW: "Customer KYC document viewed",
    Perm.KYC_APPROVE: "Customer KYC verified",
    Perm.KYC_REJECT: "Customer KYC rejected",
    Perm.PURCHASE_MANAGE: "Purchase forwarded to provider",
    Perm.CUSTOMER_SUSPEND: "Account suspended",
    Perm.CUSTOMER_RESTORE: "Account reactivated",
    Perm.POLICY_APPROVE: "Policy approved",
    Perm.POLICY_REJECT: "Policy sent back",
    Perm.POLICY_SUSPEND: "Policy deactivated",
}


def _humanize_action(action):
    return _ADMIN_TITLES.get(action) or action.replace(".", " ").replace(
        "_", " "
    ).capitalize()


def _format_changes(changes, reason):
    """Render an audit row's ``changes``/``reason`` as a short human string."""
    parts = []
    if isinstance(changes, dict):
        for key, value in changes.items():
            label = key.replace("_", " ")
            if isinstance(value, (list, tuple)) and len(value) == 2:
                parts.append(f"{label}: {value[0]} → {value[1]}")
            else:
                parts.append(f"{label}: {value}")
    if reason:
        parts.append(reason)
    return "; ".join(parts)


def _admin_status(changes):
    if isinstance(changes, dict):
        transition = changes.get("status")
        if isinstance(transition, (list, tuple)) and transition:
            return transition[-1] or ""
    return ""


def _admin_events(groups):
    """Admin-action events for the given ``{entity_type: [ids]}`` groups.

    Scopes the audit log to the subject by matching each entity type against the
    ids of the subject's related records, and to *administrator* actions only
    (self-service rows are represented by their domain record instead).
    """
    query = Q()
    for entity_type, ids in groups.items():
        ids = [str(i) for i in ids]
        if ids:
            query |= Q(entity_type=entity_type, entity_id__in=ids)
    if not query:
        return []
    entries = (
        AuditLogEntry.objects.filter(query, actor_role=ADMIN)
        .select_related("actor")
        .order_by("-created_at")[:PER_SOURCE_LIMIT]
    )
    return [
        _event(
            event_id=f"audit:{entry.pk}",
            timestamp=entry.created_at,
            source="admin",
            category=entry.module or entry.entity_type.lower(),
            action=entry.action,
            title=_humanize_action(entry.action),
            detail=_format_changes(entry.changes, entry.reason),
            status=_admin_status(entry.changes),
            actor=entry.actor.email if entry.actor_id else "",
            ref_type=entry.entity_type,
            ref_id=entry.entity_id,
        )
        for entry in entries
    ]


# --- Public builders --------------------------------------------------------


def build_user_history(user, *, include_admin):
    """The merged activity + admin-action timeline for one customer/user."""
    events = [
        _event(
            event_id=f"account:{user.pk}",
            timestamp=user.date_joined,
            source="activity",
            category="account",
            action="account.created",
            title="Account created",
            detail=f"Registered as {user.get_role_display()}.",
            actor=user.email,
            ref_type="User",
            ref_id=user.pk,
        )
    ]

    kyc_records = list(user.kyc_records.all()[:PER_SOURCE_LIMIT])
    for kyc in kyc_records:
        who = "own" if kyc.is_self else "beneficiary"
        events.append(
            _event(
                event_id=f"kyc:{kyc.pk}",
                timestamp=kyc.created_at,
                source="activity",
                category="kyc",
                action="kyc.submitted",
                title=f"KYC submitted ({who})",
                detail=f"{kyc.get_document_type_display()} · {kyc.full_name}",
                status=kyc.status,
                actor=user.email,
                ref_type="CustomerKyc",
                ref_id=kyc.pk,
            )
        )

    purchases = list(user.policy_purchases.select_related("policy")[:PER_SOURCE_LIMIT])
    for purchase in purchases:
        events.append(
            _event(
                event_id=f"purchase:{purchase.pk}",
                timestamp=purchase.created_at,
                source="activity",
                category="purchase",
                action="purchase.created",
                title=f"Bought {purchase.policy.name}",
                detail=f"Nominee: {purchase.nominee_name} "
                f"({purchase.nominee_relationship})",
                status=purchase.status,
                actor=user.email,
                amount=purchase.policy.premium,
                ref_type="PolicyPurchase",
                ref_id=purchase.pk,
            )
        )
        if purchase.status == PolicyPurchase.Status.ACTIVE and purchase.start_date:
            events.append(
                _event(
                    event_id=f"purchase:{purchase.pk}:issued",
                    timestamp=purchase.start_date,
                    source="activity",
                    category="purchase",
                    action="purchase.issued",
                    title=f"Policy issued · {purchase.policy_number}",
                    detail=f"Cover {purchase.start_date} – {purchase.end_date}",
                    status=purchase.status,
                    ref_type="PolicyPurchase",
                    ref_id=purchase.pk,
                )
            )

    payments = (
        Payment.objects.filter(policy_purchase__customer=user)
        .select_related("policy_purchase__policy")
        .order_by("-created_at")[:PER_SOURCE_LIMIT]
    )
    for payment in payments:
        events.append(
            _event(
                event_id=f"payment:{payment.pk}",
                timestamp=payment.paid_at or payment.created_at,
                source="activity",
                category="payment",
                action="payment.recorded",
                title=f"Payment {payment.get_status_display().lower()}",
                detail=f"{payment.get_gateway_display()} · "
                f"{payment.policy_purchase.policy.name}",
                status=payment.status,
                actor=user.email,
                amount=payment.amount,
                ref_type="Payment",
                ref_id=payment.pk,
            )
        )

    claims = list(
        user.claims.select_related("purchase__policy")[:PER_SOURCE_LIMIT]
    )
    for claim in claims:
        events.extend(_claim_events(claim, actor=user.email))

    messages = (
        ClaimMessage.objects.filter(claim__customer=user)
        .select_related("author")
        .order_by("-created_at")[:PER_SOURCE_LIMIT]
    )
    for message in messages:
        events.append(
            _event(
                event_id=f"claim_message:{message.pk}",
                timestamp=message.created_at,
                source="activity",
                category="claim_message",
                action="claim.message",
                title=f"Message from {message.author_role.lower() or 'user'}",
                detail=(message.body or "")[:160],
                actor=message.author.email if message.author_id else "",
                ref_type="Claim",
                ref_id=message.claim_id,
            )
        )

    if include_admin:
        events.extend(
            _admin_events(
                {
                    "User": [user.pk],
                    "CustomerKyc": [k.pk for k in kyc_records],
                    "PolicyPurchase": [p.pk for p in purchases],
                    "Claim": [c.pk for c in claims],
                }
            )
        )

    events.sort(key=lambda event: (event["timestamp"] or _EPOCH, event["id"]), reverse=True)
    return events


def build_provider_history(provider, *, include_admin):
    """The merged activity + admin-action timeline for one insurance provider."""
    events = [
        _event(
            event_id=f"provider:{provider.pk}",
            timestamp=provider.created_at,
            source="activity",
            category="provider",
            action="provider.created",
            title="Provider profile created",
            detail=provider.company_name,
            status=provider.kyc_status,
            actor=provider.user.email,
            ref_type="Provider",
            ref_id=provider.pk,
        )
    ]

    kyc_documents = list(
        provider.kyc_documents.select_related("uploaded_by")[:PER_SOURCE_LIMIT]
    )
    for doc in kyc_documents:
        events.append(
            _event(
                event_id=f"provider_kyc:{doc.pk}",
                timestamp=doc.created_at,
                source="activity",
                category="provider_kyc",
                action="provider_kyc.uploaded",
                title=f"KYC document uploaded · {doc.get_document_type_display()}",
                status=doc.status,
                actor=doc.uploaded_by.email if doc.uploaded_by_id else "",
                ref_type="ProviderKyc",
                ref_id=doc.pk,
            )
        )

    memberships = list(provider.memberships.select_related("user")[:PER_SOURCE_LIMIT])
    for membership in memberships:
        events.append(
            _event(
                event_id=f"membership:{membership.pk}",
                timestamp=membership.created_at,
                source="activity",
                category="membership",
                action="membership.added",
                title=f"Team member added · {membership.get_role_display()}",
                detail=membership.user.email,
                actor=membership.user.email,
                ref_type="ProviderMembership",
                ref_id=membership.pk,
            )
        )

    policies = list(provider.policies.all()[:PER_SOURCE_LIMIT])
    for policy in policies:
        events.append(
            _event(
                event_id=f"policy:{policy.pk}",
                timestamp=policy.created_at,
                source="activity",
                category="policy",
                action="policy.created",
                title=f"Policy created · {policy.name}",
                detail=policy.summary or "",
                status=policy.status,
                ref_type="Policy",
                ref_id=policy.pk,
            )
        )

    payouts = list(
        provider.payouts.select_related("purchase__policy")[:PER_SOURCE_LIMIT]
    )
    for payout in payouts:
        events.append(
            _event(
                event_id=f"payout:{payout.pk}",
                timestamp=payout.paid_at or payout.created_at,
                source="activity",
                category="payout",
                action="payout.recorded",
                title=f"Payout {payout.get_status_display().lower()}",
                detail=payout.purchase.policy.name,
                status=payout.status,
                amount=payout.net_amount,
                ref_type="ProviderPayout",
                ref_id=payout.pk,
            )
        )

    claims = list(
        Claim.objects.for_provider(provider)
        .select_related("purchase__policy", "customer")
        .order_by("-created_at")[:PER_SOURCE_LIMIT]
    )
    for claim in claims:
        events.extend(_claim_events(claim, actor=claim.customer.email))

    if include_admin:
        purchase_ids = list(
            PolicyPurchase.objects.filter(policy__provider=provider)
            .order_by("-created_at")
            .values_list("id", flat=True)[:PER_SOURCE_LIMIT]
        )
        events.extend(
            _admin_events(
                {
                    "Provider": [provider.pk],
                    "ProviderKyc": [d.pk for d in kyc_documents],
                    "ProviderMembership": [m.pk for m in memberships],
                    "Policy": [p.pk for p in policies],
                    "PolicyPurchase": purchase_ids,
                }
            )
        )

    events.sort(key=lambda event: (event["timestamp"] or _EPOCH, event["id"]), reverse=True)
    return events


def _claim_events(claim, *, actor):
    """The submitted / decided / settled activity events for one claim.

    Shared by both timelines: the customer sees their own claims, the provider
    sees claims filed against their policies — the same underlying milestones.
    """
    events = [
        _event(
            event_id=f"claim:{claim.pk}",
            timestamp=claim.created_at,
            source="activity",
            category="claim",
            action="claim.submitted",
            title=f"Claim filed · {claim.purchase.policy.name}",
            detail=(claim.description or "")[:160],
            status=claim.status,
            actor=actor,
            amount=claim.claimed_amount,
            ref_type="Claim",
            ref_id=claim.pk,
        )
    ]
    if claim.decided_at:
        events.append(
            _event(
                event_id=f"claim:{claim.pk}:decided",
                timestamp=claim.decided_at,
                source="activity",
                category="claim",
                action="claim.decided",
                title=f"Claim {claim.get_status_display().lower()}",
                detail=(claim.review_note or "")[:160],
                status=claim.status,
                amount=claim.approved_amount,
                ref_type="Claim",
                ref_id=claim.pk,
            )
        )
    if claim.settled_at:
        events.append(
            _event(
                event_id=f"claim:{claim.pk}:settled",
                timestamp=claim.settled_at,
                source="activity",
                category="claim",
                action="claim.settled",
                title="Claim settled",
                status=claim.status,
                amount=claim.approved_amount,
                ref_type="Claim",
                ref_id=claim.pk,
            )
        )
    return events
