import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.db.filters import active, mark_deleted
from app.models import Note, Role
from app.schemas.notes import NoteIn, NoteOut, NoteUpdate
from app.services import audit

router = APIRouter(prefix="/vehicles/{vehicle_id}/notes", tags=["notes"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


@router.get("", response_model=list[NoteOut])
async def list_notes(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[Note]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(Note)
        .where(Note.vehicle_id == vehicle_id, active(Note))
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


async def _note_in_vehicle(vehicle_id: uuid.UUID, note_id: uuid.UUID, db: DbSession) -> Note:
    note = await db.get(Note, note_id)
    if note is None or note.vehicle_id != vehicle_id or note.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    vehicle_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: NoteUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> Note:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot update records"
        )
    note = await _note_in_vehicle(vehicle_id, note_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    vehicle_id: uuid.UUID,
    note_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot delete records"
        )
    note = await _note_in_vehicle(vehicle_id, note_id, db)
    mark_deleted(note, user.id)
    audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_DELETED,
        entity_type="note",
        entity_id=note.id,
        vehicle_id=vehicle_id,
        summary=note.title,
    )
    await db.commit()
