"""Notification dispatch — the single public surface for raising notifications.

Every notification is created by an **explicit call** from a business
transition point (there are no signals). :func:`notify` writes the in-app row
and fans out to the side channels: email (best-effort), SMS and Web Push (both
pluggable adapters that are off by default). The typed ``notify_*`` helpers
build the copy for each event so call sites stay one-liners and wording lives
in one place.

Delivery never breaks the caller: email uses ``fail_silently``, and SMS and
push swallow their own errors, so a mail/SMS/push outage cannot roll back a
payment or a claim decision.
"""

from apps.core.email import send_branded_email

from .models import Notification
from .push import send_push
from .sms import send_sms


def notify(recipient, type, title, body="", url="", email=True, sms=True, push=True):
    """Create an in-app notification and fan out to email, SMS + Web Push.

    Returns the created :class:`~apps.notifications.models.Notification`.
    """
    notification = Notification.objects.create(
        recipient=recipient, type=type, title=title, body=body, url=url
    )
    if email and getattr(recipient, "email", ""):
        _send_email(recipient.email, title, body, url)
    if sms and getattr(recipient, "phone", ""):
        send_sms(recipient.phone, f"{title} — {body}" if body else title)
    if push:
        send_push(recipient, title, body, url)
    return notification


def _send_email(address, subject, body, url=""):
    send_branded_email(
        subject=subject,
        to=address,
        heading=subject,
        paragraphs=[body] if body else [],
        cta=("View in Bimaya", url) if url else None,
    )


# --- Per-event helpers ------------------------------------------------------
# Each builds the title/body/url for one trigger event and calls notify(). The
# frontend `url`s are deep links into the customer/provider areas.


def notify_welcome(user):
    return notify(
        user,
        Notification.Type.WELCOME,
        "Welcome to Bimaya",
        "Your account is ready. Explore policies and secure your cover with Bimaya.",
        url="/dashboard",
    )


def notify_purchase_created(purchase):
    return notify(
        purchase.customer,
        Notification.Type.PURCHASE_CREATED,
        "Purchase started",
        f"Your purchase of “{purchase.policy.name}” has been created. "
        "Complete payment to activate your cover.",
        url=f"/dashboard/policies/{purchase.id}",
    )


def notify_payment_confirmed(purchase):
    return notify(
        purchase.customer,
        Notification.Type.PAYMENT_CONFIRMED,
        "Payment received",
        f"We’ve received your payment for “{purchase.policy.name}”. "
        "It’s now with Bimaya for verification.",
        url=f"/dashboard/policies/{purchase.id}",
    )


def notify_payment_failed(purchase):
    return notify(
        purchase.customer,
        Notification.Type.PAYMENT_FAILED,
        "Payment failed",
        f"Your payment for “{purchase.policy.name}” could not be confirmed. "
        "Please try again.",
        url=f"/dashboard/policies/{purchase.id}",
    )


def notify_purchase_forwarded(purchase):
    """Notify the customer their purchase moved to the provider for issuance,
    and notify the provider that a new purchase is awaiting issuance."""
    notify(
        purchase.customer,
        Notification.Type.PURCHASE_FORWARDED,
        "Verification complete",
        f"“{purchase.policy.name}” has been verified and sent to the provider "
        "to issue your policy.",
        url=f"/dashboard/policies/{purchase.id}",
    )
    provider_user = _provider_user(purchase.policy)
    if provider_user is not None:
        notify(
            provider_user,
            Notification.Type.PROVIDER_NEW_ISSUANCE,
            "New purchase to issue",
            f"A verified purchase of “{purchase.policy.name}” is ready for you "
            "to issue.",
            url="/provider",
        )


def notify_policy_issued(purchase):
    return notify(
        purchase.customer,
        Notification.Type.POLICY_ISSUED,
        "Your policy is active",
        f"“{purchase.policy.name}” is now active"
        + (f" (policy no. {purchase.policy_number})." if purchase.policy_number else "."),
        url=f"/dashboard/policies/{purchase.id}",
    )


def notify_renewal_reminder(purchase):
    return notify(
        purchase.customer,
        Notification.Type.RENEWAL_REMINDER,
        "Renewal coming up",
        f"“{purchase.policy.name}” expires on {purchase.end_date}. "
        "Renew to keep your cover active.",
        url=f"/dashboard/policies/{purchase.id}",
    )


# --- Claims -----------------------------------------------------------------

_CLAIM_EVENT = {
    "SUBMITTED": (
        Notification.Type.CLAIM_SUBMITTED,
        "Claim submitted",
        "Your claim has been submitted and is awaiting review.",
    ),
    "UNDER_REVIEW": (
        Notification.Type.CLAIM_UNDER_REVIEW,
        "Claim under review",
        "The provider has started reviewing your claim.",
    ),
    "MORE_INFO": (
        Notification.Type.CLAIM_MORE_INFO,
        "More information needed",
        "The provider needs more information to continue with your claim.",
    ),
    "APPROVED": (
        Notification.Type.CLAIM_APPROVED,
        "Claim approved",
        "Good news — your claim has been approved.",
    ),
    "REJECTED": (
        Notification.Type.CLAIM_REJECTED,
        "Claim rejected",
        "Your claim has been rejected. See the claim for details.",
    ),
    "SETTLED": (
        Notification.Type.CLAIM_SETTLED,
        "Claim settled",
        "Your claim has been settled and the payout processed.",
    ),
}


def notify_claim_status(claim, event):
    """Notify the customer about a claim moving to ``event`` (a key above)."""
    type_, title, body = _CLAIM_EVENT[event]
    return notify(
        claim.customer,
        type_,
        title,
        body,
        url=f"/dashboard/claims/{claim.id}",
    )


def notify_provider_new_claim(claim):
    provider_user = _provider_user(claim.purchase.policy)
    if provider_user is None:
        return None
    return notify(
        provider_user,
        Notification.Type.PROVIDER_NEW_CLAIM,
        "New claim to review",
        f"A claim has been filed on “{claim.purchase.policy.name}”.",
        url="/provider",
    )


# --- KYC / provider ---------------------------------------------------------


def notify_kyc_verified(kyc):
    return notify(
        kyc.customer,
        Notification.Type.KYC_VERIFIED,
        "KYC verified",
        "Your KYC has been verified. You’re all set to complete purchases.",
        url="/dashboard",
    )


def notify_kyc_rejected(kyc):
    return notify(
        kyc.customer,
        Notification.Type.KYC_REJECTED,
        "KYC needs attention",
        "Your KYC could not be verified. Please review and resubmit your details.",
        url="/dashboard/kyc",
    )


def notify_provider_approved(provider):
    return notify(
        provider.user,
        Notification.Type.PROVIDER_APPROVED,
        "You’re approved to sell",
        f"“{provider.company_name}” has been approved. Your published policies "
        "are now live on Bimaya.",
        url="/provider",
    )


def notify_policy_approved(policy):
    return notify(
        policy.provider.user,
        Notification.Type.POLICY_APPROVED,
        "Policy approved",
        f"“{policy.name}” has been approved and is now live on the marketplace.",
        url="/provider",
    )


def notify_policy_deactivated(policy):
    return notify(
        policy.provider.user,
        Notification.Type.POLICY_DEACTIVATED,
        "Policy deactivated",
        f"“{policy.name}” has been taken off the marketplace. "
        "Submit it again to relist it.",
        url="/provider",
    )


def notify_policy_rejected(policy):
    return notify(
        policy.provider.user,
        Notification.Type.POLICY_REJECTED,
        "Policy needs changes",
        f"“{policy.name}” was sent back for review. "
        "Update it and submit again when ready.",
        url="/provider",
    )


# --- Claim messages ---------------------------------------------------------


def notify_claim_message(claim, to):
    """Notify the other party of a new message on ``claim``.

    ``to`` is ``"customer"`` or ``"provider"`` — the recipient side. The message
    body itself is never included (it may reference sensitive details); the
    notification just points at the claim thread.
    """
    if to == "customer":
        return notify(
            claim.customer,
            Notification.Type.CLAIM_MESSAGE,
            "New message on your claim",
            f"The provider sent a message about your claim on "
            f"“{claim.purchase.policy.name}”.",
            url=f"/dashboard/claims/{claim.id}",
        )
    provider_user = _provider_user(claim.purchase.policy)
    if provider_user is None:
        return None
    return notify(
        provider_user,
        Notification.Type.CLAIM_MESSAGE,
        "New message on a claim",
        f"A customer sent a message about their claim on "
        f"“{claim.purchase.policy.name}”.",
        url="/provider",
    )


def _provider_user(policy):
    """The user account behind a policy's provider, or ``None``."""
    provider = getattr(policy, "provider", None)
    return getattr(provider, "user", None) if provider is not None else None
