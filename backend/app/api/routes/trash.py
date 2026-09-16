"""Recoverable deletion: what was deleted, putting it back, and purging it.

Deleting a record marks it rather than removing it (spec §23.2), so this is
where it can be found again. Restoring reruns the derived calculations the
record takes part in — consumption and odometer distances — because those were
rebuilt without it when it was deleted.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentMembership, CurrentUser, DbSession
from app.db.filters import mark_restored
from app.models import (
    Attachment,
    ChargingRecord,
    ExpenseRecord,
    FuelRecord,
    Note,
    OdometerReading,
    Plan,
    Reminder,
    Role,
    User,
    Vehicle,
    WorkRecord,
)
from app.models.mixins import SoftDelete
from app.schemas.trash import TrashItem
from app.services import audit

router = APIRouter(prefix="/trash", tags=["trash"])

_CAN_RESTORE = {Role.OWNER, Role.MANAGER, Role.EDITOR}
# Purging destroys the record for good, so it stays with the owner (spec §25.1).
_CAN_PURGE = {Role.OWNER}


@dataclass(frozen=True)
class Kind:
    model: type[Any]
    describe: Callable[[Any], str]


# The entity_type in the URL maps to one table and how a row of it should read.
KINDS: dict[str, Kind] = {
    "vehicle": Kind(Vehicle, lambda row: row.name),
    "odometer_reading": Kind(OdometerReading, lambda row: f"{row.reading} on {row.recorded_on}"),
    "fuel_record": Kind(FuelRecord, lambda row: f"{row.volume_litres} L on {row.recorded_on}"),
    "charging_record": Kind(
        ChargingRecord, lambda row: f"{row.energy_kwh} kWh on {row.recorded_on}"
    ),
    "work_record": Kind(WorkRecord, lambda row: row.description),
    "expense_record": Kind(ExpenseRecord, lambda row: f"{row.category} {row.amount}"),
    "note": Kind(Note, lambda row: row.title),
    "attachment": Kind(Attachment, lambda row: row.filename),
    "plan": Kind(Plan, lambda row: row.description),
    "reminder": Kind(Reminder, lambda row: row.title),
}


def _kind(entity_type: str) -> Kind:
    kind = KINDS.get(entity_type)
    if kind is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown record type")
    return kind


async def _find(
    entity_type: str, entity_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> Any:
    """Fetch a deleted row, once it is confirmed to belong to this household."""
    kind = _kind(entity_type)
    row = await db.get(kind.model, entity_id)
    if row is None or row.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not in the bin")
    if kind.model is Vehicle:
        owned = row.household_id == membership.household_id
    else:
        vehicle = await db.get(Vehicle, row.vehicle_id)
        owned = vehicle is not None and vehicle.household_id == membership.household_id
    if not owned:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not in the bin")
    return row


@router.get("", response_model=list[TrashItem])
async def list_trash(
    membership: CurrentMembership,
    db: DbSession,
    entity_type: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
) -> list[TrashItem]:
    household_vehicles = select(Vehicle.id).where(Vehicle.household_id == membership.household_id)
    wanted = [entity_type] if entity_type else list(KINDS)
    names: dict[uuid.UUID, str] = {}
    items: list[TrashItem] = []

    for name in wanted:
        kind = _kind(name)
        model = kind.model
        scope = (
            model.household_id == membership.household_id
            if model is Vehicle
            else model.vehicle_id.in_(household_vehicles)
        )
        rows = await db.scalars(
            select(model)
            .where(model.deleted_at.is_not(None), scope)
            .order_by(model.deleted_at.desc())
            .limit(limit)
        )
        for row in rows:
            if row.deleted_by and row.deleted_by not in names:
                actor = await db.get(User, row.deleted_by)
                names[row.deleted_by] = audit.actor_label(actor)
            items.append(
                TrashItem(
                    entity_type=name,
                    entity_id=row.id,
                    vehicle_id=None if model is Vehicle else row.vehicle_id,
                    summary=kind.describe(row),
                    deleted_at=row.deleted_at,
                    deleted_by=row.deleted_by,
                    deleted_by_label=names.get(row.deleted_by, "") if row.deleted_by else "",
                )
            )
    items.sort(key=lambda item: item.deleted_at, reverse=True)
    return items[:limit]


async def _rebuild_derived(row: SoftDelete, db: DbSession) -> None:
    """Recompute whatever the restored record feeds into."""
    # Imported here: both modules import the vehicle guard from odometer.
    from app.api.routes.charging import recalculate as recalculate_charging
    from app.api.routes.fuel import _recalculate_consumption
    from app.api.routes.odometer import _recalculate

    if isinstance(row, OdometerReading):
        await _recalculate(row.vehicle_id, db)
    elif isinstance(row, FuelRecord):
        await _recalculate_consumption(row.vehicle_id, db)
    elif isinstance(row, ChargingRecord):
        vehicle = await db.get(Vehicle, row.vehicle_id)
        if vehicle is not None:
            await recalculate_charging(vehicle, db)


@router.post("/{entity_type}/{entity_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore(
    entity_type: str,
    entity_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    """Put a deleted record back.

    Restoring a work record does not take its parts out of stock again: the
    return raised its own stock movement when the record was deleted, and
    silently re-requisitioning could drive an item negative. Adjust stock by
    hand if the parts really were used.
    """
    if membership.role not in _CAN_RESTORE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot restore records"
        )
    row = await _find(entity_type, entity_id, membership, db)
    if entity_type != "vehicle":
        vehicle = await db.get(Vehicle, row.vehicle_id)
        if vehicle is not None and vehicle.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Restore the vehicle before the records kept against it",
            )
    mark_restored(row)
    await db.flush()
    await _rebuild_derived(row, db)
    audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.VEHICLE_RESTORED if entity_type == "vehicle" else audit.RECORD_RESTORED,
        entity_type=entity_type,
        entity_id=entity_id,
        vehicle_id=None if entity_type == "vehicle" else row.vehicle_id,
        summary=_kind(entity_type).describe(row),
    )
    await db.commit()


@router.delete("/{entity_type}/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def purge(
    entity_type: str,
    entity_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
    settings: AppSettings,
) -> None:
    """Remove a deleted record for good. There is nothing after this."""
    if membership.role not in _CAN_PURGE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only an owner can purge records"
        )
    row = await _find(entity_type, entity_id, membership, db)
    summary = _kind(entity_type).describe(row)
    # The stored file outlived the delete so a restore could find it; now it goes.
    stored = Path(settings.storage_path) / row.storage_key if entity_type == "attachment" else None
    audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_PURGED,
        entity_type=entity_type,
        entity_id=entity_id,
        vehicle_id=None if entity_type == "vehicle" else row.vehicle_id,
        summary=summary,
    )
    await db.delete(row)
    await db.commit()
    if stored is not None:
        stored.unlink(missing_ok=True)
