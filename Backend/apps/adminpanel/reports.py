"""CSV report exports for the admin panel (SRS 3.4.3 — report generation).

Each admin list view has a matching ``reports/<resource>/`` endpoint that
streams the same rows — honouring the same filters and search — as a
downloadable CSV. This is kept separate from the JSON list serializers on
purpose: a report is a flat, human-readable snapshot for a spreadsheet, not an
API shape.
"""

import csv
from datetime import datetime

from django.http import HttpResponse
from django.utils import timezone


def yes_no(value):
    """Render a boolean as a spreadsheet-friendly Yes / No."""
    return "Yes" if value else "No"


def money(value):
    """Render a currency amount as a plain decimal string (no separators)."""
    if value is None:
        return ""
    return f"{value:.2f}"


def local_date(value):
    """Render a date or datetime as an ISO date in the project's timezone."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        return value.date().isoformat()
    return value.isoformat()


def csv_response(basename, header, rows):
    """Build a downloadable CSV ``HttpResponse``.

    ``basename`` is dated so repeated downloads sort naturally and don't
    overwrite each other; ``rows`` is any iterable of value sequences aligned to
    ``header``.
    """
    filename = f"{basename}-{timezone.localdate().isoformat()}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response
