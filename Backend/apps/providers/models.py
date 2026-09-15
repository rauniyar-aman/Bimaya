from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel

# The role catalog lives in rbac.py (the reviewable security policy); it is
# re-exported here so ``from apps.providers.models import ProviderRole`` keeps
# working for the model field and existing importers.
from .rbac import ProviderRole  # noqa: F401  (re-exported)


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
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("10.00"),
        help_text="Platform commission percent charged on each sale of this "
        "provider's policies.",
    )

    class Meta(TimeStampedModel.Meta):
        ordering = ["company_name"]

    def __str__(self):
        return self.company_name

    @property
    def public_id(self):
        """Human-readable provider identifier, e.g. ``PRV-00142``.

        Derived from the primary key, so it is stable once saved and needs no
        column of its own. Blank for an unsaved instance.
        """
        return f"PRV-{self.pk:05d}" if self.pk else ""

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


class ProviderMembership(TimeStampedModel):
    """Links an added staff member to a provider organisation.

    The organisation's owner is ``Provider.user`` (implicit role
    :data:`~apps.providers.rbac.OWNER`); this model holds everyone else, each
    with one assignable :class:`~apps.providers.rbac.ProviderRole`. A user belongs
    to at most one provider (``user`` is one-to-one). Membership is managed by
    the organisation's own Owner / Company Admin, and by platform admins.
    """

    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_membership",
    )
    role = models.CharField(
        max_length=20,
        choices=ProviderRole.choices,
        default=ProviderRole.FINANCE_VIEWER,
        help_text="Owners are not stored here; the owner is Provider.user.",
    )

    class Meta(TimeStampedModel.Meta):
        ordering = ["user__email"]

    def __str__(self):
        return f"{self.user} — {self.provider} ({self.get_role_display()})"
