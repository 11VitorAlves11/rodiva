import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.db.filters import active, mark_deleted
from app.models import ExpenseRecord, Role
from app.schemas.expenses import ExpenseRecordIn, ExpenseRecordOut, ExpenseRecordUpdate
from app.services import audit
from app.services.recurrence import next_occurrence_date

router = APIRouter(prefix="/vehicles/{vehicle_id}/expenses", tags=["expenses"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


def _as_out(record: ExpenseRecord) -> ExpenseRecordOut:
    """Render a record, showing a pending one past its due date as overdue (RF-DES-007).

    Derived on read rather than stored: a stored flag would only be right until
    the next midnight nobody was around for. It is written onto the response and
    never onto the row — assigning to the ORM object would leave it dirty in the
    session, and the next flush would persist a status nobody chose.
    """
    out = ExpenseRecordOut.model_validate(record)
    if record.status == "pending" and record.due_on and record.due_on < datetime.now(UTC).date():
        out.status = "overdue"
    return out


@router.get("", response_model=list[ExpenseRecordOut])
async def list_expenses(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[ExpenseRecordOut]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(ExpenseRecord)
        .where(ExpenseRecord.vehicle_id == vehicle_id, active(ExpenseRecord))
        .order_by(ExpenseRecord.issued_on.desc(), ExpenseRecord.id.desc())
    )
    return [_as_out(record) for record in result]


@router.post("", response_model=ExpenseRecordOut, status_code=status.HTTP_201_CREATED)
async def create_expense(
    vehicle_id: uuid.UUID,
    payload: ExpenseRecordIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> ExpenseRecordOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    _check_recurrence(payload.recurrence_interval, payload.recurrence_unit)
    record = ExpenseRecord(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _as_out(record)


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
) -> ExpenseRecordOut:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update records"
        )
    record = await _expense_in_vehicle(vehicle_id, record_id, db)
    changes = payload.model_dump(exclude_unset=True)
    _check_recurrence(
        changes.get("recurrence_interval", record.recurrence_interval),
        changes.get("recurrence_unit", record.recurrence_unit),
    )
    for field, value in changes.items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return _as_out(record)


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


def _check_recurrence(interval: int | None, unit: str | None) -> None:
    """An interval without a unit, or a unit without one, says nothing about when."""
    if (interval is None) != (unit is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Recurrence needs both an interval and a unit, or neither",
        )


@router.post(
    "/{record_id}/next-occurrence",
    response_model=ExpenseRecordOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_next_occurrence(
    vehicle_id: uuid.UUID,
    record_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> ExpenseRecordOut:
    """Raise the next instance of a recurring expense (RF-DES-004, RF-DES-005).

    The new record is always pending: it has not been paid yet, and for a bill
    whose amount changes each time the amount is left at zero rather than
    copying a figure that is probably wrong.
    """
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    record = await _expense_in_vehicle(vehicle_id, record_id, db)
    if record.recurrence_interval is None or record.recurrence_unit is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This expense does not recur"
        )
    existing = await db.scalar(
        select(ExpenseRecord).where(
            ExpenseRecord.recurrence_parent_id == record.id, active(ExpenseRecord)
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The next occurrence of this expense already exists",
        )
    base: date = record.due_on or record.issued_on
    following = next_occurrence_date(base, record.recurrence_interval, record.recurrence_unit)
    nxt = ExpenseRecord(
        vehicle_id=vehicle_id,
        created_by=user.id,
        issued_on=following,
        due_on=following,
        category=record.category,
        amount=0 if record.recurrence_amount_varies else record.amount,
        supplier=record.supplier,
        status="pending",
        reference=None if record.recurrence_amount_varies else record.reference,
        notes=record.notes,
        recurrence_interval=record.recurrence_interval,
        recurrence_unit=record.recurrence_unit,
        recurrence_amount_varies=record.recurrence_amount_varies,
        recurrence_parent_id=record.id,
    )
    db.add(nxt)
    await db.commit()
    await db.refresh(nxt)
    return _as_out(nxt)
