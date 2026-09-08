from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class NotificationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(recipient=user)

    def unread(self):
        return self.filter(read_at__isnull=True)


class Notification(TimeStampedModel):
    """An in-app notification for a single user.

    Notifications are created by :mod:`apps.notifications.services` at the
    business transition points (a payment settles, a claim is approved, …).
    Delivery is fanned out there too: the in-app row is this model; email and
    SMS are best-effort side channels. There are **no signals** — every
    notification is dispatched by an explicit service call.
    """

    class Type(models.TextChoices):
        WELCOME = "WELCOME", "Welcome"
        PURCHASE_CREATED = "PURCHASE_CREATED", "Purchase created"
        PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED", "Payment confirmed"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment failed"
        PURCHASE_FORWARDED = "PURCHASE_FORWARDED", "Purchase forwarded"
        POLICY_ISSUED = "POLICY_ISSUED", "Policy issued"
        RENEWAL_REMINDER = "RENEWAL_REMINDER", "Renewal reminder"
        CLAIM_SUBMITTED = "CLAIM_SUBMITTED", "Claim submitted"
        CLAIM_UNDER_REVIEW = "CLAIM_UNDER_REVIEW", "Claim under review"
        CLAIM_MORE_INFO = "CLAIM_MORE_INFO", "Claim needs more information"
        CLAIM_APPROVED = "CLAIM_APPROVED", "Claim approved"
        CLAIM_REJECTED = "CLAIM_REJECTED", "Claim rejected"
        CLAIM_SETTLED = "CLAIM_SETTLED", "Claim settled"
        KYC_VERIFIED = "KYC_VERIFIED", "KYC verified"
        KYC_REJECTED = "KYC_REJECTED", "KYC rejected"
        PROVIDER_APPROVED = "PROVIDER_APPROVED", "Provider approved"
        PROVIDER_NEW_ISSUANCE = "PROVIDER_NEW_ISSUANCE", "New purchase to issue"
        PROVIDER_NEW_CLAIM = "PROVIDER_NEW_CLAIM", "New claim to review"
        POLICY_APPROVED = "POLICY_APPROVED", "Policy approved"
        POLICY_DEACTIVATED = "POLICY_DEACTIVATED", "Policy deactivated"
        POLICY_REJECTED = "POLICY_REJECTED", "Policy sent back for changes"
        CLAIM_MESSAGE = "CLAIM_MESSAGE", "New claim message"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=150)
    body = models.TextField(blank=True)
    url = models.CharField(
        max_length=300,
        blank=True,
        help_text="Frontend deep link the notification points at, e.g. /dashboard/claims/5.",
    )
    read_at = models.DateTimeField(null=True, blank=True)

    objects = NotificationQuerySet.as_manager()

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["recipient", "read_at"])]

    def __str__(self):
        return f"{self.recipient.email} · {self.get_type_display()}"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at", "updated_at"])
