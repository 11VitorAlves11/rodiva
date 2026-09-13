import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _recalculate, _vehicle_in_household
from app.models import OdometerReading, Role, WorkRecord
from app.schemas.work_records import WorkRecordIn, WorkRecordOut

router = APIRouter(prefix="/vehicles/{vehicle_id}/work-records", tags=["work records"])
_CAN_WRITE_RECORDS = {Role.OWNER, Role.MANAGER, Role.EDITOR}


@router.get("", response_model=list[WorkRecordOut])
async def list_work_records(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[WorkRecord]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(WorkRecord)
        .where(WorkRecord.vehicle_id == vehicle_id)
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
