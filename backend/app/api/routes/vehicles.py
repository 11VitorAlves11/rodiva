"""Garage (spec §5): vehicles scoped to the caller's household.

Every query filters by `household_id` server-side (RNF-SEG-001) — the household
comes from the caller's own membership, never from a client-supplied id.
"""

import base64
import binascii
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentMembership, CurrentUser, DbSession
from app.models import Role, Vehicle, VehicleStatus
from app.schemas.vehicles import VehicleIn, VehicleOut, VehiclePhotoIn, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

# RF-AGR matrix §2.3: owner and manager create vehicles; editor and reader cannot.
_CAN_CREATE_VEHICLE = {Role.OWNER, Role.MANAGER}


@router.get("", response_model=list[VehicleOut])
async def list_vehicles(membership: CurrentMembership, db: DbSession) -> list[Vehicle]:
    result = await db.scalars(
        select(Vehicle)
        .where(Vehicle.household_id == membership.household_id, Vehicle.deleted_at.is_(None))
        .order_by(Vehicle.created_at)
    )
    return list(result)


def _require_manage(membership: CurrentMembership) -> None:
    if membership.role not in _CAN_CREATE_VEHICLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot manage vehicles"
        )


@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> Vehicle:
    if membership.role not in _CAN_CREATE_VEHICLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create vehicles"
        )
    vehicle = Vehicle(
        household_id=membership.household_id,
        created_by=user.id,
        status=VehicleStatus.ACTIVE,
        **payload.model_dump(),
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> Vehicle:
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.household_id != membership.household_id or vehicle.deleted_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> Vehicle:
    _require_manage(membership)
    vehicle = await get_vehicle(vehicle_id, membership, db)
    changes = payload.model_dump(exclude_unset=True)
    if any(
        changes.get(field) is None
        for field in ("name", "distance_unit", "status")
        if field in changes
    ):
        raise HTTPException(status_code=422, detail="Required vehicle fields cannot be null")
    for field, value in changes.items():
        setattr(vehicle, field, value)
    await db.commit()
    await db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> None:
    _require_manage(membership)
    vehicle = await get_vehicle(vehicle_id, membership, db)
    vehicle.deleted_at = datetime.now(UTC)
    await db.commit()


@router.post("/{vehicle_id}/photo", response_model=VehicleOut)
async def upload_vehicle_photo(
    vehicle_id: uuid.UUID,
    payload: VehiclePhotoIn,
    membership: CurrentMembership,
    db: DbSession,
    settings: AppSettings,
) -> Vehicle:
    vehicle = await get_vehicle(vehicle_id, membership, db)
    _require_manage(membership)
    extensions = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    extension = extensions.get(payload.content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported image type"
        )
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid image"
        ) from exc
    if not content or len(content) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Image is too large"
        )
    directory = Path(settings.storage_path) / "vehicles"
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{vehicle.id}.{extension}"
    (directory / filename).write_bytes(content)
    vehicle.photo_url = f"/storage/vehicles/{filename}"
    await db.commit()
    await db.refresh(vehicle)
    return vehicle
