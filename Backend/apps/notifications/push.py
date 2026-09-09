"""Web Push adapter — OFF by default.

Browser push needs a VAPID keypair and an opt-in per device, so it stays
disabled until both the flag and the keys are set. The switch is
``settings.NOTIFICATIONS_PUSH_ENABLED`` combined with a configured
``VAPID_PRIVATE_KEY``/``VAPID_PUBLIC_KEY`` (see :func:`push_enabled`); while off,
:func:`send_push` returns immediately without sending anything.

When on, :func:`send_push` fans a short, non-sensitive payload out to every
subscription the user has registered and prunes any the push service reports as
gone (HTTP 404/410). Delivery never raises to the caller: a push outage must not
break the business action that triggered the notification. ``pywebpush`` is
imported lazily inside :func:`_deliver` so a missing dependency can never crash
the app at import time.
"""

import json
import logging

from django.conf import settings

from .models import PushSubscription

logger = logging.getLogger(__name__)


def push_enabled():
    """True only when push is switched on AND a VAPID keypair is configured."""
    return bool(
        getattr(settings, "NOTIFICATIONS_PUSH_ENABLED", False)
        and getattr(settings, "VAPID_PRIVATE_KEY", "")
        and getattr(settings, "VAPID_PUBLIC_KEY", "")
    )


def send_push(user, title, body="", url=""):
    """Best-effort Web Push to all of ``user``'s subscriptions.

    No-op unless the channel is switched on. Returns the number of subscriptions
    that accepted the message. Never raises: dead subscriptions are pruned and
    any other error is swallowed and logged.
    """
    if not push_enabled():
        return 0

    subscriptions = list(user.push_subscriptions.all())
    if not subscriptions:
        return 0

    # Only the display copy and a deep link travel to the browser — never any
    # customer PII beyond what the user already sees in-app.
    payload = json.dumps({"title": title, "body": body, "url": url})

    sent = 0
    dead = []
    for sub in subscriptions:
        result = _deliver(sub, payload)
        if result is True:
            sent += 1
        elif result == "gone":
            dead.append(sub.pk)

    if dead:
        PushSubscription.objects.filter(pk__in=dead).delete()
    return sent


def _deliver(sub, payload):
    """Send one encrypted push message. Never raises.

    Returns ``True`` on success, the string ``"gone"`` when the push service
    says the subscription no longer exists (so the caller prunes it), or
    ``False`` on any other error.
    """
    try:
        from pywebpush import WebPushException, webpush
    except Exception:  # pragma: no cover - defensive; dep must never break import
        logger.exception("pywebpush unavailable; cannot send push")
        return False

    admin_email = getattr(settings, "VAPID_ADMIN_EMAIL", "") or "admin@bimaya.local"
    sub_claim = admin_email if "://" in admin_email or admin_email.startswith(
        "mailto:"
    ) else f"mailto:{admin_email}"

    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": sub_claim},
        )
        return True
    except WebPushException as exc:
        status_code = getattr(getattr(exc, "response", None), "status_code", None)
        if status_code in (404, 410):
            return "gone"  # subscription expired/unsubscribed — prune it
        logger.warning(
            "Push rejected (status %s) for subscription %s", status_code, sub.pk
        )
        return False
    except Exception:  # pragma: no cover - defensive; push must never break a request
        logger.exception("Push delivery failed for subscription %s", sub.pk)
        return False
