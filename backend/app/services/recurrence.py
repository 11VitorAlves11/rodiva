"""Working out when a recurring expense falls next (RF-DES-004)."""

import calendar
from datetime import date, timedelta


def next_occurrence_date(base: date, interval: int, unit: str) -> date:
    """The date `interval` days, months or years after `base`.

    Month and year steps clamp to the last day of the target month, so a bill
    due on the 31st recurs on the 30th in a 30-day month rather than spilling
    into the next one — which is how the bill itself behaves.
    """
    if unit == "day":
        return base + timedelta(days=interval)
    if unit == "month":
        return _add_months(base, interval)
    if unit == "year":
        return _add_months(base, interval * 12)
    raise ValueError(f"Unknown recurrence unit: {unit}")


def _add_months(base: date, months: int) -> date:
    total = base.month - 1 + months
    year = base.year + total // 12
    month = total % 12 + 1
    return date(year, month, min(base.day, calendar.monthrange(year, month)[1]))
