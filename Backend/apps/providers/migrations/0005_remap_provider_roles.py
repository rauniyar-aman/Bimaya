# Remap the legacy coarse provider-membership roles onto the new granular
# catalog. The old scheme was OWNER/STAFF/VIEWER (owners were never stored, so
# only STAFF and VIEWER rows exist here):
#
#   STAFF  → COMPANY_ADMIN  (STAFF could write broadly; preserve that reach and
#                            let the org re-scope down to a narrower role)
#   VIEWER → FINANCE_VIEWER (read-only, matching the old viewer intent)
#
# Reverse maps back so the migration is fully reversible on dev databases.

from django.db import migrations

FORWARD = {"STAFF": "COMPANY_ADMIN", "VIEWER": "FINANCE_VIEWER"}
BACKWARD = {"COMPANY_ADMIN": "STAFF", "FINANCE_VIEWER": "VIEWER"}


def _remap(apps, mapping):
    ProviderMembership = apps.get_model("providers", "ProviderMembership")
    for old_value, new_value in mapping.items():
        ProviderMembership.objects.filter(role=old_value).update(role=new_value)


def forwards(apps, schema_editor):
    _remap(apps, FORWARD)


def backwards(apps, schema_editor):
    _remap(apps, BACKWARD)


class Migration(migrations.Migration):

    dependencies = [
        ("providers", "0004_alter_providermembership_role"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
