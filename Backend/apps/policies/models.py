from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.providers.models import Provider


class InsuranceCategory(TimeStampedModel):
    """A top-level line of cover (Life, Health, Vehicle, Travel)."""

    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(
        max_length=40,
        blank=True,
        help_text="Icon key the frontend maps to an SVG (e.g. heart, health, car, plane).",
    )
    order = models.PositiveSmallIntegerField(
        default=0, help_text="Lower numbers are shown first."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "insurance category"
        verbose_name_plural = "insurance categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class PolicyQuerySet(models.QuerySet):
    def public(self):
        """Only policies a visitor may see: approved, from an approved provider."""
        return self.filter(
            status=self.model.Status.APPROVED, provider__is_approved=True
        )


class Policy(TimeStampedModel):
    """A concrete insurance plan a provider offers under a category."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending review"
        APPROVED = "APPROVED", "Approved"
        INACTIVE = "INACTIVE", "Inactive"

    class Frequency(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        QUARTERLY = "QUARTERLY", "Quarterly"
        YEARLY = "YEARLY", "Yearly"
        ONE_TIME = "ONE_TIME", "One-time"

    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="policies"
    )
    category = models.ForeignKey(
        InsuranceCategory, on_delete=models.PROTECT, related_name="policies"
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    summary = models.CharField(
        max_length=255, blank=True, help_text="One-line tagline for cards and previews."
    )
    description = models.TextField(blank=True)
    premium = models.DecimalField(max_digits=12, decimal_places=2)
    premium_frequency = models.CharField(
        max_length=20, choices=Frequency.choices, default=Frequency.YEARLY
    )
    coverage_amount = models.DecimalField(
        max_digits=14, decimal_places=2, help_text="Sum assured."
    )
    term_months = models.PositiveIntegerField(help_text="Policy duration in months.")
    min_age = models.PositiveSmallIntegerField(null=True, blank=True)
    max_age = models.PositiveSmallIntegerField(null=True, blank=True)
    features = models.JSONField(
        default=list, blank=True, help_text="List of highlight strings."
    )
    add_ons = models.JSONField(
        default=list, blank=True, help_text="List of optional add-ons."
    )
    terms = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    is_featured = models.BooleanField(default=False)

    objects = PolicyQuerySet.as_manager()

    class Meta(TimeStampedModel.Meta):
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category", "status"]),
        ]
        verbose_name = "policy"
        verbose_name_plural = "policies"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.name) or "policy"
        slug = base
        suffix = 2
        while Policy.objects.exclude(pk=self.pk).filter(slug=slug).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    @property
    def is_public(self):
        return self.status == self.Status.APPROVED and self.provider.is_approved
