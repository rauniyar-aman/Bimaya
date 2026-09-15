from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

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

    def mark_verified(self, note=""):
        """Approve this KYC. Clears any prior rejection note."""
        self.status = self.Status.VERIFIED
        self.review_note = note
        self.save(update_fields=["status", "review_note", "updated_at"])

    def mark_rejected(self, note):
        """Reject this KYC, recording why (shown back to the customer)."""
        self.status = self.Status.REJECTED
        self.review_note = note
        self.save(update_fields=["status", "review_note", "updated_at"])


class ProviderKyc(TimeStampedModel):
    """A verification document belonging to a provider (insurance company).

    Where :class:`CustomerKyc` captures a person's identity, this stores the
    company's registration / tax / licensing paperwork. A provider organisation
    can hold several documents; each is reviewed by a Bimaya administrator and
    moved from ``PENDING`` to ``VERIFIED`` or ``REJECTED`` (the review backs
    ``apps.staff.rbac.Perm.PROVIDER_KYC_REVIEW``). The provider-wide
    ``Provider.kyc_status`` flag remains the headline gate; these are the
    supporting evidence behind it.

    Files are PII-adjacent company documents kept under the git-ignored
    ``MEDIA_ROOT`` and served only through authenticated, scoped download
    endpoints — never a raw media URL.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    class DocumentType(models.TextChoices):
        REGISTRATION = "REGISTRATION", "Company registration"
        TAX = "TAX", "Tax / PAN registration"
        LICENSE = "LICENSE", "Insurance licence"
        OTHER = "OTHER", "Other"

    provider = models.ForeignKey(
        "providers.Provider",
        on_delete=models.CASCADE,
        related_name="kyc_documents",
    )
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    file = models.FileField(upload_to="provider_kyc/%Y/%m/")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    review_note = models.TextField(
        blank=True, help_text="Why a document was rejected — shown back to the provider."
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_provider_kyc",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_provider_kyc",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["provider", "status"])]
        verbose_name = "provider KYC document"
        verbose_name_plural = "provider KYC documents"

    def __str__(self):
        return f"{self.provider} · {self.get_document_type_display()} · {self.get_status_display()}"

    @property
    def is_verified(self):
        return self.status == self.Status.VERIFIED

    def mark_verified(self, reviewer=None, note=""):
        """Approve this document. Clears any prior rejection note."""
        self.status = self.Status.VERIFIED
        self.review_note = note
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "review_note",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )

    def mark_rejected(self, note, reviewer=None):
        """Reject this document, recording why (shown back to the provider)."""
        self.status = self.Status.REJECTED
        self.review_note = note
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "review_note",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )
