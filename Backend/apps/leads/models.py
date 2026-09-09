from django.db import models

from apps.core.models import TimeStampedModel


class ProviderLead(TimeStampedModel):
    """An enquiry submitted from a public form on Bimaya.

    Two kinds share this table (see :class:`Kind`): a provider onboarding
    request from the "For insurance providers" page, and a general message from
    the "Contact" page. Neither creates any account — a Bimaya administrator
    reviews the enquiry and follows up out of band. ``company_name`` is only
    meaningful for provider enquiries and is left blank for contact messages.
    """

    class Kind(models.TextChoices):
        PROVIDER = "PROVIDER", "Provider onboarding"
        CONTACT = "CONTACT", "Contact enquiry"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        ONBOARDED = "ONBOARDED", "Onboarded"
        DECLINED = "DECLINED", "Declined"

    kind = models.CharField(
        max_length=20, choices=Kind.choices, default=Kind.PROVIDER
    )
    company_name = models.CharField(max_length=150, blank=True)
    contact_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW
    )

    class Meta(TimeStampedModel.Meta):
        indexes = [models.Index(fields=["status"])]
        verbose_name = "provider lead"

    def __str__(self):
        label = self.company_name or self.contact_name
        return f"{label} · {self.get_status_display()}"
