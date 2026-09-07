"""Send renewal reminders for active policies nearing expiry.

Run manually or from cron (there is no scheduler in the request path). Finds
ACTIVE purchases whose cover ends within a window and that have not already had
a reminder sent, notifies the customer, and flips ``renewal_reminder_sent`` so
each purchase is reminded at most once.

    python manage.py send_renewal_reminders --days 30
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications import services as notifications
from apps.purchases.models import PolicyPurchase


class Command(BaseCommand):
    help = "Notify customers whose active policies are due to expire soon."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="How many days ahead of expiry to send the reminder (default 30).",
        )

    def handle(self, *args, **options):
        days = options["days"]
        cutoff = timezone.localdate() + timedelta(days=days)
        due = (
            PolicyPurchase.objects.filter(
                status=PolicyPurchase.Status.ACTIVE,
                renewal_reminder_sent=False,
                end_date__isnull=False,
                end_date__lte=cutoff,
            )
            .select_related("policy", "customer")
        )

        sent = 0
        for purchase in due:
            notifications.notify_renewal_reminder(purchase)
            purchase.renewal_reminder_sent = True
            purchase.save(update_fields=["renewal_reminder_sent", "updated_at"])
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} renewal reminder(s)."))
