from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel


class Provider(TimeStampedModel):
    """An insurance company that lists policies on the marketplace.

    One profile per provider user. Policies can only be published once the
    provider is approved (``is_approved``) *and* the policy itself is approved,
    so the profile is the platform's gate on who may sell insurance here.
    """

    class KycStatus(models.TextChoices):
        PENDING = "PENDING", "Pending review"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_profile",
    )
    company_name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    registration_number = models.CharField(
        max_length=100, blank=True, help_text="Company / insurer registration number."
    )
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to="providers/logos/", blank=True, null=True)
    website = models.URLField(blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=20, blank=True)
    kyc_status = models.CharField(
        max_length=20, choices=KycStatus.choices, default=KycStatus.PENDING
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="Approved providers may have their policies published.",
    )

    class Meta(TimeStampedModel.Meta):
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.company_name) or "provider"
        slug = base
        suffix = 2
        while Provider.objects.exclude(pk=self.pk).filter(slug=slug).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug
