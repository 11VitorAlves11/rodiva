import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SearchKind = Literal[
    "vehicle", "fuel", "work", "expense", "note", "plan", "inventory", "equipment", "inspection"
]

SearchSort = Literal["occurred_on_desc", "occurred_on_asc", "title_asc", "title_desc"]

BulkOperation = Literal["delete", "duplicate", "move", "edit", "export"]


class SearchResult(BaseModel):
    id: uuid.UUID
    kind: SearchKind
    title: str
    subtitle: str | None
    vehicle_id: uuid.UUID | None
    occurred_on: date | datetime | None
    url: str


class BulkItem(BaseModel):
    kind: SearchKind
    id: uuid.UUID


class BulkOperationIn(BaseModel):
    operation: BulkOperation
    items: list[BulkItem] = Field(min_length=1, max_length=200)
    target_vehicle_id: uuid.UUID | None = None
    fields: dict[str, Any] | None = None
    format: Literal["csv"] = "csv"


class BulkFailure(BaseModel):
    kind: SearchKind
    id: uuid.UUID
    reason: str


class BulkOperationResult(BaseModel):
    requested: int
    succeeded: int
    failures: list[BulkFailure]
