import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.db.filters import active, mark_deleted
from app.models import ExpenseRecord, Role
from app.schemas.expenses import ExpenseRecordIn, ExpenseRecordOut, ExpenseRecordUpdate
from app.services import audit

router = APIRouter(prefix="/vehicles/{vehicle_id}/expenses", tags=["expenses"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


@router.get("", response_model=list[ExpenseRecordOut])
async def list_expenses(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[ExpenseRecord]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(ExpenseRecord)
        .where(ExpenseRecord.vehicle_id == vehicle_id, active(ExpenseRecord))
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


async def _expense_in_vehicle(
    vehicle_id: uuid.UUID, record_id: uuid.UUID, db: DbSession
) -> ExpenseRecord:
    record = await db.get(ExpenseRecord, record_id)
    if record is None or record.vehicle_id != vehicle_id or record.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return record


@router.patch("/{record_id}", response_model=ExpenseRecordOut)
async def update_expense(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ExpenseRecordUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> ExpenseRecord:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update records"
        )
    record = await _expense_in_vehicle(vehicle_id, record_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot delete records"
        )
    record = await _expense_in_vehicle(vehicle_id, record_id, db)
    mark_deleted(record, user.id)
    await audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_DELETED,
        entity_type="expense_record",
        entity_id=record.id,
        vehicle_id=vehicle_id,
        summary=f"{record.category} {record.amount}",
    )
    await db.commit()
