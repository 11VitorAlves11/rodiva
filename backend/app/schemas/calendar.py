from datetime import datetime

from pydantic import BaseModel


class CalendarFeedStatus(BaseModel):
    active: bool
    created_at: datetime | None = None


class CalendarFeedCreated(CalendarFeedStatus):
    token: str
    feed_path: str
