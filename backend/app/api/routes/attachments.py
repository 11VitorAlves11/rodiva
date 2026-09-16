import base64
import binascii
import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _vehicle_in_household
from app.db.filters import active, mark_deleted
from app.models import Attachment, Role
from app.schemas.attachments import AttachmentIn, AttachmentOut
from app.services import audit

router = APIRouter(prefix="/vehicles/{vehicle_id}/attachments", tags=["attachments"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}
_ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


@router.get("", response_model=list[AttachmentOut])
async def list_attachments(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[Attachment]:
    await _vehicle_in_household(vehicle_id, membership, db)
    result = await db.scalars(
        select(Attachment)
        .where(Attachment.vehicle_id == vehicle_id, active(Attachment))
        .order_by(Attachment.created_at.desc())
    )
    return list(result)


@router.post("", response_model=AttachmentOut, status_code=status.HTTP_201_CREATED)
async def create_attachment(
    vehicle_id: uuid.UUID,
    payload: AttachmentIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
    settings: AppSettings,
) -> Attachment:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot create records"
        )
    if payload.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported file type"
        )
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid file"
        ) from exc
    if not content or len(content) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is too large"
        )
    attachment_id = uuid.uuid4()
    storage_key = f"attachments/{vehicle_id}/{attachment_id}"
    path = Path(settings.storage_path) / storage_key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    attachment = Attachment(
        id=attachment_id,
        vehicle_id=vehicle_id,
        filename=Path(payload.filename).name,
        content_type=payload.content_type,
        size=len(content),
        checksum=hashlib.sha256(content).hexdigest(),
        storage_key=storage_key,
        created_by=user.id,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


@router.get("/{attachment_id}/download")
async def download_attachment(
    vehicle_id: uuid.UUID,
    attachment_id: uuid.UUID,
    membership: CurrentMembership,
    db: DbSession,
    settings: AppSettings,
) -> FileResponse:
    await _vehicle_in_household(vehicle_id, membership, db)
    attachment = await db.get(Attachment, attachment_id)
    if (
        attachment is None
        or attachment.vehicle_id != vehicle_id
        or attachment.deleted_at is not None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return FileResponse(
        Path(settings.storage_path) / attachment.storage_key,
        media_type=attachment.content_type,
        filename=attachment.filename,
    )


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    vehicle_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> None:
    await _vehicle_in_household(vehicle_id, membership, db)
    if membership.role not in _CAN_WRITE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot delete records"
        )
    attachment = await db.get(Attachment, attachment_id)
    if (
        attachment is None
        or attachment.vehicle_id != vehicle_id
        or attachment.deleted_at is not None
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    mark_deleted(attachment, user.id)
    await audit.record_record_action(
        db,
        membership=membership,
        actor=user,
        action=audit.RECORD_DELETED,
        entity_type="attachment",
        entity_id=attachment.id,
        vehicle_id=vehicle_id,
        summary=attachment.filename,
    )
    await db.commit()
