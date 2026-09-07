"""Insurance claims.

A customer files a claim against one of their **active** policy purchases; the
underwriting provider works a claims queue and moves it through a review
lifecycle; an approved claim is settled by a simulated gateway payout.

Lifecycle: ``SUBMITTED`` → ``UNDER_REVIEW`` (provider opened it) → ``APPROVED``
→ ``SETTLED`` (payout confirmed). Two branches off ``UNDER_REVIEW``: the provider
may bounce it to ``MORE_INFO`` for the customer to add documents and
:meth:`Claim.resubmit`, or ``REJECTED`` it. ``REJECTED`` and ``SETTLED`` are
terminal. Each transition raises ``ValueError`` on an illegal source state, the
same shape as :class:`apps.purchases.models.PolicyPurchase`.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class ClaimQuerySet(models.QuerySet):
    def for_customer(self, user):
        return self.filter(customer=user)

    def for_provider(self, provider):
        return self.filter(purchase__policy__provider=provider)


class Claim(TimeStampedModel):
    """A customer's claim against one of their active policy purchases."""

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under review"
        MORE_INFO = "MORE_INFO", "More information needed"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        SETTLED = "SETTLED", "Settled"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="claims",
    )
    purchase = models.ForeignKey(
        "purchases.PolicyPurchase",
        on_delete=models.PROTECT,
        related_name="claims",
    )

    # What the customer reports.
    incident_date = models.DateField()
    incident_location = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    claimed_amount = models.DecimalField(max_digits=12, decimal_places=2)

    # What the provider decides.
    approved_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    review_note = models.TextField(
        blank=True,
        help_text="Why more info is needed, or why the claim was rejected — shown to the customer.",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBMITTED
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    settled_at = models.DateTimeField(null=True, blank=True)

    objects = ClaimQuerySet.as_manager()

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.customer.email} · {self.purchase.policy.name} · {self.get_status_display()}"

    def start_review(self):
        """Provider opens a submitted claim for review."""
        if self.status != self.Status.SUBMITTED:
            raise ValueError("Only a submitted claim can be moved to review.")
        self.status = self.Status.UNDER_REVIEW
        self.save(update_fields=["status", "updated_at"])

    def request_more_info(self, note):
        """Provider bounces the claim back to the customer for more documents."""
        if self.status != self.Status.UNDER_REVIEW:
            raise ValueError("Only a claim under review can be sent back for more info.")
        self.status = self.Status.MORE_INFO
        self.review_note = note
        self.save(update_fields=["status", "review_note", "updated_at"])

    def resubmit(self):
        """Customer has added the requested information — back to the queue."""
        if self.status != self.Status.MORE_INFO:
            raise ValueError("Only a claim awaiting more info can be resubmitted.")
        self.status = self.Status.UNDER_REVIEW
        self.save(update_fields=["status", "updated_at"])

    def approve(self, approved_amount, note=""):
        """Provider approves the claim for the given payout amount."""
        if self.status != self.Status.UNDER_REVIEW:
            raise ValueError("Only a claim under review can be approved.")
        self.status = self.Status.APPROVED
        self.approved_amount = approved_amount
        self.review_note = note
        self.decided_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "approved_amount",
                "review_note",
                "decided_at",
                "updated_at",
            ]
        )

    def reject(self, note):
        """Provider rejects the claim, recording why."""
        if self.status != self.Status.UNDER_REVIEW:
            raise ValueError("Only a claim under review can be rejected.")
        self.status = self.Status.REJECTED
        self.review_note = note
        self.decided_at = timezone.now()
        self.save(update_fields=["status", "review_note", "decided_at", "updated_at"])

    def mark_settled(self):
        """A payout succeeded — the claim is settled."""
        if self.status != self.Status.APPROVED:
            raise ValueError("Only an approved claim can be settled.")
        self.status = self.Status.SETTLED
        self.settled_at = timezone.now()
        self.save(update_fields=["status", "settled_at", "updated_at"])


class ClaimDocument(TimeStampedModel):
    """A supporting file on a claim (a bill, a medical/police report, a photo).

    These are sensitive documents, so they are served only through the
    authenticated download endpoint — never a public media URL.
    """

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="claims/%Y/%m/")
    caption = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.claim_id} · {self.file.name}"


class ClaimPayout(TimeStampedModel):
    """A **simulated** gateway payout that settles an approved claim.

    It mirrors the inbound :class:`apps.payments.models.Payment` flow end to end
    (initiate → confirm) but no real money moves: eSewa/Khalti here are
    collection-only sandboxes with no disbursement API. A claim may have several
    payout attempts, but only one can ever succeed (a partial unique constraint
    enforces this); a successful payout settles the claim.
    """

    class Gateway(models.TextChoices):
        ESEWA = "ESEWA", "eSewa"
        KHALTI = "KHALTI", "Khalti"

    class Status(models.TextChoices):
        INITIATED = "INITIATED", "Initiated"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="payouts")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    gateway = models.CharField(max_length=20, choices=Gateway.choices)
    gateway_reference = models.CharField(
        max_length=100, unique=True, blank=True, null=True
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INITIATED
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["claim"],
                condition=models.Q(status="SUCCESS"),
                name="one_settled_payout_per_claim",
            )
        ]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.claim_id} · {self.gateway} · {self.status}"

    def mark_success(self, reference):
        self.status = self.Status.SUCCESS
        self.gateway_reference = reference
        self.paid_at = timezone.now()
        self.save(
            update_fields=["status", "gateway_reference", "paid_at", "updated_at"]
        )
        # Simulated payout settled — the claim is now settled.
        self.claim.mark_settled()
