import uuid

from pydantic import BaseModel


class GoogleCalendarStatus(BaseModel):
    configured: bool
    connected: bool
    google_account_email: str | None = None
    calendar_id: str | None = None
    synced_vehicle_ids: list[uuid.UUID] = []
    status: str | None = None
    last_error: str | None = None


class GoogleCalendarAuthorizeUrl(BaseModel):
    authorize_url: str


class GoogleCalendarOption(BaseModel):
    id: str
    summary: str


class GoogleCalendarConnectionIn(BaseModel):
    calendar_id: str
    vehicle_ids: list[uuid.UUID] = []
