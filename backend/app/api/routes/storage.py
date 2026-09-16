"""Serve legacy photo URLs with the same household checks as vehicle records."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import AppSettings, CurrentMembership, DbSession
from app.api.routes.odometer import _vehicle_in_household

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/vehicles/{filename}")
async def vehicle_photo(
    filename: str,
    membership: CurrentMembership,
    db: DbSession,
    settings: AppSettings,
) -> FileResponse:
    path = Path(filename)
    try:
        vehicle_id = uuid.UUID(path.stem)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Photo not found") from exc
    vehicle = await _vehicle_in_household(vehicle_id, membership, db)
    if vehicle.photo_url != f"/storage/vehicles/{filename}" or path.suffix not in {
        ".jpg",
        ".png",
        ".webp",
    }:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo = Path(settings.storage_path) / "vehicles" / filename
    if not photo.is_file():
        raise HTTPException(status_code=404, detail="Photo not found")
    return FileResponse(
        photo, headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}
    )
