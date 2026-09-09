"""Government insurance registry sync — a dormant, config-gated seam.

Nepal's insurance regulator may require every issued policy to be reported to a
central registry. This module is the scaffolding for that integration. It ships
OFF and does nothing until it is switched on AND an endpoint and API key are
configured (see :func:`gov_enabled`); until then :func:`report_policy` and
:func:`report_batch` return a clear "disabled" result and make no network call.

It is driven only by the ``sync_gov_registry`` management command — never from
the request path — so a slow or failing registry can never delay or break a
customer's purchase.

**Privacy.** Only non-PII regulatory metadata leaves Bimaya: the policy number,
plan and provider identifiers, amounts and cover dates. Customer identity,
nominee details and KYC never appear in the payload (see :func:`policy_summary`).

No live regulator endpoint is wired here — this is a documented seam, not a
finished client. ``requests`` is imported lazily inside :func:`_post` so a
missing dependency can never break app import, and delivery never raises to the
caller.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

# How long to wait on the registry before giving up (seconds).
_REQUEST_TIMEOUT = 10


def gov_enabled():
    """True only when the sync is switched on AND fully configured."""
    return bool(
        getattr(settings, "GOV_INTEGRATION_ENABLED", False)
        and getattr(settings, "GOV_INTEGRATION_ENDPOINT", "")
        and getattr(settings, "GOV_INTEGRATION_API_KEY", "")
    )


def policy_summary(purchase):
    """Build the non-PII regulatory summary for one issued purchase.

    Deliberately excludes every customer identifier — no email, name, nominee
    or KYC. Only the regulatory metadata a registry needs: the policy number,
    the plan and provider (with its registration number), the amounts and the
    cover period.
    """
    policy = purchase.policy
    provider = policy.provider
    return {
        "policy_number": purchase.policy_number,
        "plan": policy.name,
        "category": policy.category.name,
        "provider": provider.company_name,
        "provider_registration_number": provider.registration_number,
        "premium": str(policy.premium),
        "coverage_amount": str(policy.coverage_amount),
        "term_months": policy.term_months,
        "start_date": purchase.start_date.isoformat() if purchase.start_date else None,
        "end_date": purchase.end_date.isoformat() if purchase.end_date else None,
        "status": purchase.status,
    }


def report_policy(purchase):
    """Report one issued policy to the registry. Never raises.

    Returns a small status dict ``{"status": "disabled"|"sent"|"error", ...}``.
    A no-op (``disabled``) when the seam is off.
    """
    if not gov_enabled():
        return {"status": "disabled", "policy_number": purchase.policy_number}
    return _post(policy_summary(purchase))


def report_batch(purchases):
    """Report each purchase in an iterable; return a tallied summary.

    Runs clean as an all-``disabled`` no-op when the seam is off.
    """
    counts = {"sent": 0, "error": 0, "disabled": 0}
    for purchase in purchases:
        status = report_policy(purchase).get("status", "error")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _post(summary):
    """POST one summary to the configured registry endpoint. Never raises."""
    try:
        import requests
    except Exception:  # pragma: no cover - defensive; dep must never break import
        logger.exception("requests unavailable; cannot sync to gov registry")
        return {"status": "error", "policy_number": summary.get("policy_number")}

    try:
        response = requests.post(
            settings.GOV_INTEGRATION_ENDPOINT,
            json=summary,
            headers={"Authorization": f"Bearer {settings.GOV_INTEGRATION_API_KEY}"},
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return {"status": "sent", "policy_number": summary.get("policy_number")}
    except Exception:
        # Never surface registry internals; a sync failure isn't the caller's problem.
        logger.exception(
            "Gov registry sync failed for policy %s", summary.get("policy_number")
        )
        return {"status": "error", "policy_number": summary.get("policy_number")}
