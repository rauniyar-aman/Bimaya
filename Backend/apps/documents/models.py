from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class CustomerKyc(TimeStampedModel):
    """A customer's Know-Your-Customer record.

    Two kinds live in this table:

    * the customer's **own** reusable KYC (``is_self=True``) — there is at most
      one per customer (enforced by a partial unique constraint), and once an
      admin verifies it, it is reused for that customer's own future purchases;
    * a **beneficiary** KYC (``is_self=False``) — captured fresh each time a
      customer buys a policy for somebody else.

    An administrator reviews each record and moves it from ``PENDING`` to
    ``VERIFIED`` or ``REJECTED``. Editing a verified self-KYC sends it back to
    ``PENDING`` for re-review (see the serializer).
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    class MaritalStatus(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        MARRIED = "MARRIED", "Married"
        OTHER = "OTHER", "Other"

    class DocumentType(models.TextChoices):
        PASSPORT = "PASSPORT", "Passport"
        CITIZENSHIP = "CITIZENSHIP", "Citizenship"
        NID = "NID", "National ID card"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kyc_records",
    )
    is_self = models.BooleanField(
        default=True,
        help_text="The customer's own reusable KYC, versus a beneficiary's.",
    )

    # Personal details
    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    marital_status = models.CharField(
        max_length=10, choices=MaritalStatus.choices, blank=True
    )
    family_details = models.TextField(
        blank=True, help_text="Spouse / parents / dependents as relevant to the policy."
    )

    # Address
    temporary_address = models.TextField(blank=True)
    permanent_address = models.TextField()

    # Identity document
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    document_number = models.CharField(max_length=60)
    document_front = models.ImageField(upload_to="kyc/%Y/%m/")
    document_back = models.ImageField(upload_to="kyc/%Y/%m/", blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    review_note = models.TextField(
        blank=True, help_text="Why a KYC was rejected — shown back to the customer."
    )

    class Meta(TimeStampedModel.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=Q(is_self=True),
                name="one_self_kyc_per_customer",
            )
        ]
        indexes = [models.Index(fields=["customer", "is_self", "status"])]
        verbose_name = "customer KYC"
        verbose_name_plural = "customer KYC records"

    def __str__(self):
        who = "self" if self.is_self else "beneficiary"
        return f"{self.customer.email} · {who} · {self.get_status_display()}"

    def clean(self):
        """Enforce the per-document-type image rules.

        * Passport — a single page (front only).
        * Citizenship — front **and** back are both required.
        * National ID — front required, back optional.
        """
        super().clean()
        if self.document_type == self.DocumentType.CITIZENSHIP and not self.document_back:
            raise ValidationError(
                {"document_back": "Both sides of the citizenship are required."}
            )

    @property
    def is_verified(self):
        return self.status == self.Status.VERIFIED
