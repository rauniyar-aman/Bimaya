"""Report issued (ACTIVE) policies to the government insurance registry.

Run manually or from cron — never from the request path, so a slow or failing
registry can't delay a customer's purchase. When the gov-integration seam is off
(the default) this is a safe no-op: it reports nothing and says so. Only non-PII
regulatory metadata is ever sent (see apps/adminpanel/gov_integration.py).

    python manage.py sync_gov_registry
"""

from django.core.management.base import BaseCommand

from apps.adminpanel import gov_integration
from apps.purchases.models import PolicyPurchase


class Command(BaseCommand):
    help = "Report active policies to the government insurance registry (no-op when disabled)."

    def handle(self, *args, **options):
        if not gov_integration.gov_enabled():
            self.stdout.write(
                self.style.WARNING(
                    "Government registry sync is disabled — nothing sent. Set "
                    "GOV_INTEGRATION_ENABLED and configure the endpoint/key to enable it."
                )
            )
            return

        active = PolicyPurchase.objects.active().select_related(
            "policy", "policy__provider", "policy__category"
        )
        counts = gov_integration.report_batch(active)
        self.stdout.write(
            self.style.SUCCESS(
                f"Gov registry sync complete: {counts['sent']} sent, "
                f"{counts['error']} failed."
            )
        )
