import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.models import ExpenseRecord, Role
from app.schemas.expenses import ExpenseRecordIn, ExpenseRecordOut

router = APIRouter(prefix="/vehicles/{vehicle_id}/expenses", tags=["expenses"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


@router.get("", response_model=list[ExpenseRecordOut])
async def list_expenses(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[ExpenseRecord]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(ExpenseRecord)
        .where(ExpenseRecord.vehicle_id == vehicle_id)
        .order_by(ExpenseRecord.issued_on.desc(), ExpenseRecord.id.desc())
    )
    return list(result)


@router.post("", response_model=ExpenseRecordOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    vehicle_id: uuid.UUID,
    payload: ExpenseRecordIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> ExpenseRecord:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    record = ExpenseRecord(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record
