"""Account services: issuing, delivering and verifying one-time passwords.

Keeping this out of the serializers means the same logic backs the API, the
Django admin and any future management command, and it gives us one place to
swap the console/e-mail delivery for a Nepali SMS gateway at go-live.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import OTP

# Human-readable copy per purpose, used in the delivery message.
_PURPOSE_COPY = {
    OTP.Purpose.REGISTER: (
        "Verify your Bimaya account",
        "Welcome to Bimaya! Use the code below to verify your account.",
    ),
    OTP.Purpose.LOGIN: (
        "Your Bimaya login code",
        "Use the code below to finish signing in to Bimaya.",
    ),
    OTP.Purpose.RESET: (
        "Reset your Bimaya password",
        "Use the code below to set a new password for your Bimaya account.",
    ),
}


def generate_code(length=None):
    """A cryptographically random, zero-padded numeric code."""
    length = length or settings.OTP_LENGTH
    return f"{secrets.randbelow(10 ** length):0{length}d}"


def issue_otp(user, purpose):
    """Invalidate any pending code for this purpose and send a fresh one."""
    OTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

    otp = OTP.objects.create(
        user=user,
        code=generate_code(),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
    )
    deliver_otp(otp)
    return otp


def deliver_otp(otp):
    """Send the code to the user.

    Development uses the console mail backend, so the code simply appears in the
    server log. Production swaps in a real mail/SMS backend via ``.env``.
    """
    subject, intro = _PURPOSE_COPY.get(
        otp.purpose, ("Your Bimaya verification code", "Use the code below to continue.")
    )
    body = (
        f"{intro}\n\n"
        f"    {otp.code}\n\n"
        f"This code expires in {settings.OTP_EXPIRY_MINUTES} minutes. "
        "If you did not request it, you can safely ignore this message.\n\n"
        "— Bimaya"
    )
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[otp.user.email],
        fail_silently=True,  # never fail a signup because mail delivery is down
    )


class OTPError(Exception):
    """Raised when a submitted code cannot be accepted.

    ``code`` is a stable machine-readable reason for the frontend.
    """

    def __init__(self, message, code):
        super().__init__(message)
        self.message = message
        self.code = code


def consume_otp(user, submitted_code, purpose):
    """Validate ``submitted_code`` and burn it. Raises :class:`OTPError`."""
    otp = (
        OTP.objects.filter(user=user, purpose=purpose, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if otp is None:
        raise OTPError(
            "No verification code is pending. Please request a new one.",
            "otp_not_found",
        )
    if otp.is_expired:
        raise OTPError(
            "This code has expired. Please request a new one.", "otp_expired"
        )
    if otp.is_locked:
        raise OTPError(
            "Too many incorrect attempts. Please request a new code.", "otp_locked"
        )
    if not otp.is_valid(submitted_code):
        otp.register_failed_attempt()
        remaining = max(settings.OTP_MAX_ATTEMPTS - otp.attempts, 0)
        raise OTPError(
            f"That code is not correct. {remaining} attempt(s) remaining.",
            "otp_invalid",
        )

    otp.mark_used()
    return otp
