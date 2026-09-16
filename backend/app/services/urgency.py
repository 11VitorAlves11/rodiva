"""How close a reminder is to being due (spec §12).

The single definition of the rule. It used to be duplicated between the
reminders route and the Google Calendar service to avoid an import cycle;
keeping it in a service both can import removes the need to keep two copies in
step by hand.
"""

from datetime import date
from typing import Literal

from app.models import Reminder

Urgency = Literal["future", "upcoming", "urgent", "very_urgent", "overdue", "completed"]

# Most pressing first. `RANK` lets a preference say "this urgency or worse".
ORDER: tuple[Urgency, ...] = (
    "overdue",
    "very_urgent",
    "urgent",
    "upcoming",
    "future",
    "completed",
)
RANK: dict[str, int] = {name: index for index, name in enumerate(ORDER)}


def urgency_of(reminder: Reminder, current_odometer: int) -> Urgency:
    if reminder.status == "completed":
        return "completed"
    days = (reminder.due_date - date.today()).days if reminder.due_date else None
    distance = reminder.due_odometer - current_odometer if reminder.due_odometer else None
    if (days is not None and days < 0) or (distance is not None and distance <= 0):
        return "overdue"
    if (days is not None and days <= 7) or (distance is not None and distance <= 250):
        return "very_urgent"
    if (days is not None and days <= 30) or (distance is not None and distance <= 1_000):
        return "urgent"
    if (days is not None and days <= 90) or (distance is not None and distance <= 3_000):
        return "upcoming"
    return "future"


def at_least_as_urgent_as(urgency: str, threshold: str) -> bool:
    """True when `urgency` is at least as pressing as `threshold`."""
    if urgency == "completed":
        return False
    return RANK.get(urgency, len(ORDER)) <= RANK.get(threshold, len(ORDER))
