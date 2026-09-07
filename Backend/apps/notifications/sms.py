"""Pluggable SMS adapter — OFF by default.

SMS is a paid channel, so it stays disabled until a real gateway is wired in.
The switch is ``settings.NOTIFICATIONS_SMS_ENABLED`` (default ``False``): while
off, :func:`send_sms` returns immediately without sending anything. When turned
on it dispatches through :func:`_deliver`, which is currently a logged stub —
replace its body with a real Nepali SMS gateway call (e.g. Sparrow SMS / Aakash
SMS) at go-live. No third-party dependency is added here.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def sms_enabled():
    return getattr(settings, "NOTIFICATIONS_SMS_ENABLED", False)


def send_sms(phone, text):
    """Best-effort SMS send. No-op unless the channel is switched on.

    Never raises: a messaging failure must not break the business action that
    triggered the notification.
    """
    if not sms_enabled():
        return False
    if not phone:
        return False
    try:
        return _deliver(phone, text)
    except Exception:  # pragma: no cover - defensive; SMS must never break a request
        logger.exception("SMS delivery failed for %s", phone)
        return False


def _deliver(phone, text):
    """Stub delivery. Swap this body for a real SMS gateway integration.

    TODO(sms-gateway): call the chosen Nepali SMS provider's HTTP API here and
    return whether it was accepted. For now we only log so the wiring can be
    exercised end-to-end without a paid account.
    """
    logger.info("SMS→%s: %s", phone, text)
    return True
