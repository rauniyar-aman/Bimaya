from django.db import models

from apps.core.models import TimeStampedModel


class ProviderLead(TimeStampedModel):
    """An enquiry from an insurance company that wants to sell on Bimaya.

    Providers are never self-registered — they submit this lead from the public
    "For insurance providers" page, and a Bimaya administrator reviews it,
    contacts the company, and onboards them out of band. This model only
    captures the enquiry; it does not create any account.
    """

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        ONBOARDED = "ONBOARDED", "Onboarded"
        DECLINED = "DECLINED", "Declined"

    company_name = models.CharField(max_length=150)
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
        return f"{self.company_name} · {self.get_status_display()}"
