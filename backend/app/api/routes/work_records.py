import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _recalculate, _vehicle_in_household
from app.db.filters import active, mark_deleted
from app.models import InventoryItem, OdometerReading, Role, StockMovement, WorkRecord
from app.schemas.work_records import WorkRecordIn, WorkRecordOut, WorkRecordUpdate
from app.services import audit

router = APIRouter(prefix="/vehicles/{vehicle_id}/work-records", tags=["work records"])
_CAN_WRITE_RECORDS = {Role.OWNER, Role.MANAGER, Role.EDITOR}


@router.get("", response_model=list[WorkRecordOut])
async def list_work_records(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[WorkRecord]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(WorkRecord)
        .where(WorkRecord.vehicle_id == vehicle_id, active(WorkRecord))
        .order_by(WorkRecord.recorded_on.desc(), WorkRecord.id.desc())
    )
    return list(result)


@router.post("", response_model=WorkRecordOut, status_code=status.HTTP_201_CREATED)
async def create_work_record(
    vehicle_id: uuid.UUID,
    payload: WorkRecordIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> WorkRecord:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    record = WorkRecord(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(record)
    if payload.odometer_reading is not None:
        db.add(
            OdometerReading(
                vehicle_id=vehicle_id,
                created_by=user.id,
                recorded_on=payload.recorded_on,
                reading=payload.odometer_reading,
                notes="Leitura criada automaticamente a partir de uma intervenção",
            )
        )
    await db.flush()
    await _recalculate(vehicle_id, db)
    await db.commit()
    await db.refresh(record)
    return record


async def _work_record_in_vehicle(
    vehicle_id: uuid.UUID, record_id: uuid.UUID, db: DbSession
) -> WorkRecord:
    record = await db.get(WorkRecord, record_id)
    if record is None or record.vehicle_id != vehicle_id or record.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work record not found")
    return record


@router.patch("/{record_id}", response_model=WorkRecordOut)
async def update_work_record(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: WorkRecordUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> WorkRecord:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update records"
        )
    record = await _work_record_in_vehicle(vehicle_id, record_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_work_record(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot delete records"
        )
    record = await _work_record_in_vehicle(vehicle_id, record_id, db)
    await _restore_requisitioned_stock(record_id, user.id, db)
    mark_deleted(record, user.id)
    await audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_DELETED,
        entity_type="work_record",
        entity_id=record.id,
        vehicle_id=vehicle_id,
        summary=record.description,
    )
    await db.commit()


async def _restore_requisitioned_stock(
    record_id: uuid.UUID, user_id: uuid.UUID, db: DbSession
) -> None:
    movements = list(
        await db.scalars(
            select(StockMovement).where(
                StockMovement.work_record_id == record_id, StockMovement.quantity_delta < 0
            )
        )
    )
    for movement in movements:
        item = await db.scalar(
            select(InventoryItem).where(InventoryItem.id == movement.item_id).with_for_update()
        )
        if item is None:
            continue
        restored = -movement.quantity_delta
        item.quantity += restored
        db.add(
            StockMovement(
                item_id=item.id,
                kind="return",
                quantity_delta=restored,
                quantity_after=item.quantity,
                notes="Stock restored after deleting the work record that requisitioned it",
                created_by=user_id,
            )
        )
