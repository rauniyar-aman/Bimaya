import calendar
import secrets
import string

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.policies.models import Policy

POLICY_NUMBER_ALPHABET = string.ascii_uppercase + string.digits


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

    Created in ``PENDING_PAYMENT`` and only becomes ``ACTIVE`` once a linked
    ``Payment`` succeeds — see ``apps.payments``, which calls :meth:`activate`.
    """

    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending payment"
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

    def activate(self):
        """Mark payment as settled: generate the policy number and term dates."""
        if not self.policy_number:
            self.policy_number = self._generate_policy_number()
        today = timezone.localdate()
        self.status = self.Status.ACTIVE
        self.start_date = today
        self.end_date = _add_months(today, self.policy.term_months)
        self.save(
            update_fields=[
                "status",
                "policy_number",
                "start_date",
                "end_date",
                "updated_at",
            ]
        )

    def _generate_policy_number(self):
        year = timezone.localdate().year
        while True:
            suffix = "".join(secrets.choice(POLICY_NUMBER_ALPHABET) for _ in range(6))
            candidate = f"BIM-{year}-{suffix}"
            if not PolicyPurchase.objects.filter(policy_number=candidate).exists():
                return candidate
