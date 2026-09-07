import calendar

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.policies.models import Policy


def _add_months(start, months):
    """Add whole calendar months to a date, clamping the day to the target month."""
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


class PolicyPurchaseQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status=self.model.Status.ACTIVE)

    def for_customer(self, user):
        return self.filter(customer=user)


class PolicyPurchase(TimeStampedModel):
    """A customer's purchase of a policy.

    Lifecycle: ``PENDING_PAYMENT`` → ``PAID`` (payment settled) → ``FORWARDED``
    (admin verified KYC + payment and handed it to the provider) → ``ACTIVE``
    (provider issued the policy and recorded its number). ``EXPIRED`` and
    ``CANCELLED`` are the terminal off-ramps.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
        PAID = "PAID", "Paid — awaiting review"
        FORWARDED = "FORWARDED", "With provider for issuance"
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="policy_purchases",
    )
    policy = models.ForeignKey(
        Policy, on_delete=models.PROTECT, related_name="purchases"
    )
    kyc = models.ForeignKey(
        "documents.CustomerKyc",
        on_delete=models.PROTECT,
        related_name="purchases",
        null=True,
        blank=True,
        help_text="The KYC covering the insured party for this purchase.",
    )
    insured_is_self = models.BooleanField(
        default=True,
        help_text="Whether the customer is buying for themselves or someone else.",
    )
    nominee_name = models.CharField(max_length=150)
    nominee_relationship = models.CharField(max_length=80)
    nominee_contact = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT
    )
    policy_number = models.CharField(max_length=30, unique=True, blank=True, null=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    renewal_reminder_sent = models.BooleanField(default=False)

    objects = PolicyPurchaseQuerySet.as_manager()

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["status"])]
        verbose_name = "policy purchase"

    def __str__(self):
        return f"{self.customer.email} · {self.policy.name}"

    def mark_paid(self):
        """A payment succeeded — the purchase now awaits admin verification.

        This deliberately does **not** issue the policy: KYC and payment are
        verified by an administrator, who forwards the purchase to the provider,
        who then issues it (see :meth:`issue`).
        """
        if self.status == self.Status.PENDING_PAYMENT:
            self.status = self.Status.PAID
            self.save(update_fields=["status", "updated_at"])

    def forward_to_provider(self):
        """Admin has verified KYC + payment; hand the purchase to the provider."""
        if self.status != self.Status.PAID:
            raise ValueError("Only a paid purchase can be forwarded for issuance.")
        self.status = self.Status.FORWARDED
        self.save(update_fields=["status", "updated_at"])

    def issue(self, policy_number):
        """The provider issues the policy: record their number and activate it."""
        if self.status != self.Status.FORWARDED:
            raise ValueError("Only a forwarded purchase can be issued.")
        today = timezone.localdate()
        self.policy_number = policy_number
        self.status = self.Status.ACTIVE
        self.start_date = today
        self.end_date = _add_months(today, self.policy.term_months)
        self.save(
            update_fields=[
                "policy_number",
                "status",
                "start_date",
                "end_date",
                "updated_at",
            ]
        )
