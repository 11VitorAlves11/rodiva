import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.models import InventoryItem, Plan, Role, StockMovement, WorkRecord
from app.schemas.inventory import (
    InventoryItemIn,
    InventoryItemOut,
    InventoryItemUpdate,
    StockMovementIn,
    StockMovementOut,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


def _require_write(membership: CurrentMembership) -> None:
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot modify inventory"
        )


async def _item_in_household(
    item_id: uuid.UUID, membership: CurrentMembership, db: DbSession, *, lock: bool = False
) -> InventoryItem:
    query = select(InventoryItem).where(
        InventoryItem.id == item_id, InventoryItem.household_id == membership.household_id
    )
    if lock:
        query = query.with_for_update()
    item = await db.scalar(query)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found"
        )
    return item


@router.get("", response_model=list[InventoryItemOut])
async def list_inventory(membership: CurrentMembership, db: DbSession) -> list[InventoryItem]:
    result = await db.scalars(
        select(InventoryItem)
        .where(InventoryItem.household_id == membership.household_id)
        .order_by(InventoryItem.name)
    )
    return list(result)


@router.post("", response_model=InventoryItemOut, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    payload: InventoryItemIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> InventoryItem:
    _require_write(membership)
    if payload.vehicle_id:
        await _vehicle_in_household(payload.vehicle_id, membership, db)
    item = InventoryItem(
        household_id=membership.household_id, created_by=user.id, **payload.model_dump()
    )
    db.add(item)
    await db.flush()
    if payload.quantity:
        db.add(
            StockMovement(
                item_id=item.id,
                kind="entry",
                quantity_delta=payload.quantity,
                quantity_after=payload.quantity,
                notes="Initial stock",
                created_by=user.id,
            )
        )
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=InventoryItemOut)
async def update_inventory_item(
    item_id: uuid.UUID,
    payload: InventoryItemUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> InventoryItem:
    _require_write(membership)
    item = await _item_in_household(item_id, membership, db)
    changes = payload.model_dump(exclude_unset=True)
    if any(changes.get(field) is None for field in ("name", "unit") if field in changes):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Name and unit cannot be null",
        )
    if "vehicle_id" in changes and changes["vehicle_id"]:
        await _vehicle_in_household(changes["vehicle_id"], membership, db)
    for field, value in changes.items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("/{item_id}/movements", response_model=list[StockMovementOut])
async def list_stock_movements(
    item_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[StockMovement]:
    await _item_in_household(item_id, membership, db)
    result = await db.scalars(
        select(StockMovement)
        .where(StockMovement.item_id == item_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
    )
    return list(result)


@router.post(
    "/{item_id}/movements",
    response_model=StockMovementOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_stock_movement(
    item_id: uuid.UUID,
    payload: StockMovementIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> StockMovement:
    _require_write(membership)
    item = await _item_in_household(item_id, membership, db, lock=True)
    if payload.quantity == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Movement quantity cannot be zero",
        )
    if payload.kind != "adjustment" and payload.quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only adjustments may use a negative quantity",
        )
    if payload.work_record_id:
        record = await db.get(WorkRecord, payload.work_record_id)
        if record is None or (item.vehicle_id and record.vehicle_id != item.vehicle_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Work record not found"
            )
        await _vehicle_in_household(record.vehicle_id, membership, db)
    if payload.plan_id:
        plan = await db.get(Plan, payload.plan_id)
        if plan is None or (item.vehicle_id and plan.vehicle_id != item.vehicle_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        await _vehicle_in_household(plan.vehicle_id, membership, db)

    quantity = Decimal(payload.quantity)
    delta = quantity if payload.kind in {"entry", "return", "adjustment"} else -quantity
    quantity_after = item.quantity + delta
    if quantity_after < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movement would result in negative stock",
        )
    item.quantity = quantity_after
    movement = StockMovement(
        item_id=item.id,
        kind=payload.kind,
        quantity_delta=delta,
        quantity_after=quantity_after,
        work_record_id=payload.work_record_id,
        plan_id=payload.plan_id,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> None:
    _require_write(membership)
    item = await _item_in_household(item_id, membership, db)
    if item.quantity != 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock must be zero before deleting an item",
        )
    await db.delete(item)
    await db.commit()
