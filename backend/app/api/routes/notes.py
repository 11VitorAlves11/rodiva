import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.models import Note, Role
from app.schemas.notes import NoteIn, NoteOut

router = APIRouter(prefix="/vehicles/{vehicle_id}/notes", tags=["notes"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


@router.get("", response_model=list[NoteOut])
async def list_notes(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[Note]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(Note)
        .where(Note.vehicle_id == vehicle_id)
        .order_by(Note.pinned.desc(), Note.updated_at.desc())
    )
    return list(result)


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    vehicle_id: uuid.UUID,
    payload: NoteIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> Note:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    note = Note(vehicle_id=vehicle_id, created_by=user.id, **payload.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note
