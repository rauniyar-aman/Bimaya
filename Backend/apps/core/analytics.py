"""Reusable, model-agnostic helpers for the analytics endpoints.

These take querysets and choice lists and return plain, JSON-ready structures
(``{"key", "label", "value"}`` breakdowns, a monthly series, formatted money),
so the admin and provider analytics builders share the same shapes. Money comes
back as a fixed two-decimal **string** — the frontend formats it for display —
while counts stay integers.
"""

import calendar
from datetime import date
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone


def money(value):
    """Format a ``Decimal``/``None`` amount as a fixed two-decimal string."""
    return f"{value or Decimal('0'):.2f}"


def month_label(day):
    """Short label for a month-start date: ``date(2026, 9, 1)`` -> ``"Sep"``."""
    return calendar.month_abbr[day.month]


def recent_months(count):
    """First day of each of the last ``count`` months, oldest first.

    Ends with the current month, so ``recent_months(6)`` on 2026-09-07 spans
    April through September 2026.
    """
    today = timezone.localdate()
    year, month = today.year, today.month
    months = []
    for _ in range(count):
        months.append(date(year, month, 1))
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    months.reverse()
    return months


def field_breakdown(queryset, field, choices):
    """Count rows grouped by ``field``, in the canonical order of ``choices``.

    ``choices`` is a ``TextChoices.choices`` list of ``(value, label)`` pairs.
    Every choice appears exactly once — values with no rows come back as 0 — so
    the frontend renders a stable, complete set of bars.
    """
    counts = {
        row[field]: row["n"]
        for row in queryset.values(field).annotate(n=Count("id"))
    }
    return [
        {"key": value, "label": label, "value": counts.get(value, 0)}
        for value, label in choices
    ]


def _bucket_by_month(queryset, date_field, aggregate):
    """Aggregate a queryset into ``{(year, month): value}`` buckets."""
    rows = (
        queryset.annotate(_month=TruncMonth(date_field))
        .values("_month")
        .annotate(_value=aggregate)
    )
    return {
        (row["_month"].year, row["_month"].month): row["_value"]
        for row in rows
        if row["_month"] is not None
    }


def monthly_series(months, purchases, successful_payments):
    """A per-month series of purchase counts and premium collected.

    Purchases are bucketed by ``created_at`` (count); premium by the payment's
    ``paid_at`` (sum of amounts). ``months`` is the window from
    :func:`recent_months`; months with no activity fill with ``0`` / ``"0.00"``.
    """
    counts = _bucket_by_month(purchases, "created_at", Count("id"))
    premiums = _bucket_by_month(successful_payments, "paid_at", Sum("amount"))
    series = []
    for day in months:
        key = (day.year, day.month)
        series.append(
            {
                "month": day.strftime("%Y-%m"),
                "label": month_label(day),
                "purchases": counts.get(key, 0),
                "premium": money(premiums.get(key)),
            }
        )
    return series
