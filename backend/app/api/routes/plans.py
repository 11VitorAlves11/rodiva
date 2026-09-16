import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _recalculate, _vehicle_in_household
from app.db.filters import active, mark_deleted
from app.models import InventoryItem, OdometerReading, Plan, Role, StockMovement, WorkRecord
from app.schemas.plans import PlanComplete, PlanIn, PlanOut, PlanUpdate
from app.services import audit

router = APIRouter(prefix="/vehicles/{vehicle_id}/plans", tags=["plans"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


def _require_write(membership: CurrentMembership) -> None:
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot modify plans"
        )


async def _plan_in_vehicle(vehicle_id: uuid.UUID, plan_id: uuid.UUID, db: DbSession) -> Plan:
    plan = await db.get(Plan, plan_id)
    if plan is None or plan.vehicle_id != vehicle_id or plan.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


@router.get("", response_model=list[PlanOut])
async def list_plans(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[Plan]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(Plan)
        .where(Plan.vehicle_id == vehicle_id, active(Plan))
        .order_by(Plan.due_date.asc().nullslast(), Plan.created_at.desc())
    )
    return list(result)


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    vehicle_id: uuid.UUID,
    payload: PlanIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> Plan:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    plan = Plan(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.patch("/{plan_id}", response_model=PlanOut)
async def update_plan(
    vehicle_id: uuid.UUID,
    plan_id: uuid.UUID,
    payload: PlanUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> Plan:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    plan = await _plan_in_vehicle(vehicle_id, plan_id, db)
    if plan.stage == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed plans must be corrected through their work record",
        )
    changes = payload.model_dump(exclude_unset=True)
    required = {"kind", "description", "priority", "stage"}
    if any(field in changes and changes[field] is None for field in required):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Required plan fields cannot be null",
        )
    for field, value in changes.items():
        setattr(plan, field, value)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.post("/{plan_id}/complete", response_model=PlanOut)
async def complete_plan(
    vehicle_id: uuid.UUID,
    plan_id: uuid.UUID,
    payload: PlanComplete,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> Plan:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    plan = await _plan_in_vehicle(vehicle_id, plan_id, db)
    if plan.stage == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Plan is already completed"
        )

    record = WorkRecord(
        vehicle_id=vehicle_id,
        created_by=user.id,
        recorded_on=payload.recorded_on,
        kind=plan.kind,
        description=plan.description,
        odometer_reading=payload.odometer_reading,
        total_cost=payload.total_cost if payload.total_cost is not None else plan.estimated_cost,
        supplier=payload.supplier,
        notes=payload.notes if payload.notes is not None else plan.notes,
    )
    db.add(record)
    db.add(
        OdometerReading(
            vehicle_id=vehicle_id,
            created_by=user.id,
            recorded_on=payload.recorded_on,
            reading=payload.odometer_reading,
            notes="Leitura criada automaticamente ao concluir um plano",
        )
    )
    await db.flush()
    for requested in payload.inventory_items:
        item = await db.scalar(
            select(InventoryItem)
            .where(
                InventoryItem.id == requested.item_id,
                InventoryItem.household_id == membership.household_id,
            )
            .with_for_update()
        )
        if item is None or (item.vehicle_id and item.vehicle_id != vehicle_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
            )
        if item.quantity < requested.quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Insufficient stock for {item.name}",
            )
        item.quantity -= requested.quantity
        db.add(
            StockMovement(
                item_id=item.id,
                kind="requisition",
                quantity_delta=-requested.quantity,
                quantity_after=item.quantity,
                work_record_id=record.id,
                plan_id=plan.id,
                notes=f"Used while completing plan: {plan.description}",
                created_by=user.id,
            )
        )
    await _recalculate(vehicle_id, db)
    plan.stage = "completed"
    plan.completed_work_record_id = record.id
    await db.commit()
    await db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    vehicle_id: uuid.UUID,
    plan_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    plan = await _plan_in_vehicle(vehicle_id, plan_id, db)
    if plan.stage == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Completed plans cannot be deleted"
        )
    mark_deleted(plan, user.id)
    audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_DELETED,
        entity_type="plan",
        entity_id=plan.id,
        vehicle_id=vehicle_id,
        summary=plan.description,
    )
    await db.commit()
