"""Map existing platform administrators to the System Owner staff role.

Idempotent: safe to run repeatedly. Every platform ``ADMIN`` user that has no
staff role yet is granted ``SYSTEM_OWNER`` (which holds every permission), so
the existing admin account keeps full access once granular enforcement is live.
Re-running creates no duplicates.

    python manage.py seed_staff_roles
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.staff.models import StaffRoleAssignment
from apps.staff.rbac import StaffRole

User = get_user_model()


class Command(BaseCommand):
    help = "Grant the System Owner staff role to existing platform administrators."

    def handle(self, *args, **options):
        admins = User.objects.filter(role=User.Role.ADMIN)
        if not admins.exists():
            self.stdout.write(
                self.style.WARNING("No platform administrators found — nothing to do.")
            )
            return

        granted = 0
        for admin in admins:
            _, created = StaffRoleAssignment.objects.get_or_create(
                user=admin, role=StaffRole.SYSTEM_OWNER.value
            )
            status = "granted" if created else "already had"
            self.stdout.write(f"  {admin.email}: {status} System Owner")
            granted += int(created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {granted} new System Owner assignment(s); "
                f"{admins.count()} administrator(s) checked."
            )
        )
