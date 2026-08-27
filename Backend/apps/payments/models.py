from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.purchases.models import PolicyPurchase


class Payment(TimeStampedModel):
    """One attempt to pay for a ``PolicyPurchase`` through a gateway.

    A purchase may have several payments (a failed attempt is retryable), but
    only one can ever succeed — a successful payment activates the purchase.
    """

    class Gateway(models.TextChoices):
        ESEWA = "ESEWA", "eSewa"
        KHALTI = "KHALTI", "Khalti"

    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    policy_purchase = models.ForeignKey(
        PolicyPurchase, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    gateway_transaction_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INITIATED
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.policy_purchase} · {self.gateway} · {self.status}"

    def mark_success(self, transaction_id):
        self.status = self.Status.SUCCESS
        self.gateway_transaction_id = transaction_id
        self.paid_at = timezone.now()
        self.save(
            update_fields=["status", "gateway_transaction_id", "paid_at", "updated_at"]
        )
        self.policy_purchase.activate()

    def mark_failed(self):
        self.status = self.Status.FAILED
        self.save(update_fields=["status", "updated_at"])
