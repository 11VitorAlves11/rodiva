import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.odometer import _recalculate, _vehicle_in_household
from app.models import Inspection, InspectionTemplate, OdometerReading, Plan, Role
from app.schemas.inspections import (
    InspectionIn,
    InspectionOut,
    InspectionUpdate,
    TemplateIn,
    TemplateOut,
)

router = APIRouter(tags=["inspections"])
_CAN_WRITE = {Role.OWNER, Role.MANAGER, Role.EDITOR}


def _require_write(membership: CurrentMembership) -> None:
    if membership.role not in _CAN_WRITE:
        raise HTTPException(status_code=403, detail="Role cannot modify inspections")


async def _template(
    template_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> InspectionTemplate:
    template = await db.get(InspectionTemplate, template_id)
    if template is None or template.household_id != membership.household_id:
        raise HTTPException(status_code=404, detail="Inspection template not found")
    return template


@router.get("/inspection-templates", response_model=list[TemplateOut])
async def list_templates(membership: CurrentMembership, db: DbSession) -> list[InspectionTemplate]:
    return list(
        await db.scalars(
            select(InspectionTemplate)
            .where(
                InspectionTemplate.household_id == membership.household_id,
                InspectionTemplate.archived.is_(False),
            )
            .order_by(InspectionTemplate.name)
        )
    )


@router.post("/inspection-templates", response_model=TemplateOut, status_code=201)
async def create_template(
    payload: TemplateIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> InspectionTemplate:
    _require_write(membership)
    if payload.vehicle_id:
        await _vehicle_in_household(payload.vehicle_id, membership, db)
    template = InspectionTemplate(
        household_id=membership.household_id,
        created_by=user.id,
        name=payload.name,
        vehicle_id=payload.vehicle_id,
        fields=[field.model_dump(mode="json") for field in payload.fields],
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.patch("/inspection-templates/{template_id}", response_model=TemplateOut, status_code=201)
async def version_template(
    template_id: uuid.UUID,
    payload: TemplateIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> InspectionTemplate:
    _require_write(membership)
    original = await _template(template_id, membership, db)
    if original.archived:
        raise HTTPException(status_code=409, detail="Archived templates cannot be versioned")
    if payload.vehicle_id:
        await _vehicle_in_household(payload.vehicle_id, membership, db)
    original.archived = True
    version = InspectionTemplate(
        household_id=membership.household_id,
        created_by=user.id,
        name=payload.name,
        vehicle_id=payload.vehicle_id,
        version=original.version + 1,
        fields=[field.model_dump(mode="json") for field in payload.fields],
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


@router.post(
    "/inspection-templates/{template_id}/duplicate", response_model=TemplateOut, status_code=201
)
async def duplicate_template(
    template_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> InspectionTemplate:
    _require_write(membership)
    original = await _template(template_id, membership, db)
    duplicate = InspectionTemplate(
        household_id=membership.household_id,
        created_by=user.id,
        name=f"{original.name} (copy)",
        vehicle_id=original.vehicle_id,
        fields=original.fields,
    )
    db.add(duplicate)
    await db.commit()
    await db.refresh(duplicate)
    return duplicate


async def _inspection(vehicle_id: uuid.UUID, inspection_id: uuid.UUID, db: DbSession) -> Inspection:
    item = await db.get(Inspection, inspection_id)
    if item is None or item.vehicle_id != vehicle_id:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return item


@router.get("/vehicles/{vehicle_id}/inspections", response_model=list[InspectionOut])
async def list_inspections(
    vehicle_id: uuid.UUID, membership: CurrentMembership, db: DbSession
) -> list[Inspection]:
    await _vehicle_in_household(vehicle_id, membership, db)
    return list(
        await db.scalars(
            select(Inspection)
            .where(Inspection.vehicle_id == vehicle_id)
            .order_by(Inspection.recorded_on.desc())
        )
    )


@router.post("/vehicles/{vehicle_id}/inspections", response_model=InspectionOut, status_code=201)
async def create_inspection(
    vehicle_id: uuid.UUID,
    payload: InspectionIn,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> Inspection:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    template = await _template(payload.template_id, membership, db)
    if template.archived or (template.vehicle_id and template.vehicle_id != vehicle_id):
        raise HTTPException(status_code=409, detail="Template is not available for this vehicle")
    snapshot = {"name": template.name, "version": template.version, "fields": template.fields}
    item = Inspection(
        vehicle_id=vehicle_id,
        template_id=template.id,
        template_snapshot=snapshot,
        created_by=user.id,
        **payload.model_dump(exclude={"template_id"}),
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/vehicles/{vehicle_id}/inspections/{inspection_id}", response_model=InspectionOut)
async def update_inspection(
    vehicle_id: uuid.UUID,
    inspection_id: uuid.UUID,
    payload: InspectionUpdate,
    membership: CurrentMembership,
    db: DbSession,
) -> Inspection:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = await _inspection(vehicle_id, inspection_id, db)
    if item.status == "completed":
        raise HTTPException(status_code=409, detail="Completed inspections are immutable")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("recorded_on") is None and "recorded_on" in changes:
        raise HTTPException(status_code=422, detail="recorded_on cannot be null")
    if changes.get("responses") is None and "responses" in changes:
        raise HTTPException(status_code=422, detail="responses cannot be null")
    for field, value in changes.items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.post(
    "/vehicles/{vehicle_id}/inspections/{inspection_id}/complete", response_model=InspectionOut
)
async def complete_inspection(
    vehicle_id: uuid.UUID,
    inspection_id: uuid.UUID,
    user: CurrentUser,
    membership: CurrentMembership,
    db: DbSession,
) -> Inspection:
    await _vehicle_in_household(vehicle_id, membership, db)
    _require_write(membership)
    item = await _inspection(vehicle_id, inspection_id, db)
    if item.status == "completed":
        raise HTTPException(status_code=409, detail="Inspection is already completed")
    fields = item.template_snapshot["fields"]
    missing = [
        field["label"]
        for field in fields
        if field.get("required")
        and (field["id"] not in item.responses or item.responses[field["id"]] in (None, "", []))
    ]
    if missing:
        raise HTTPException(
            status_code=422, detail=f"Missing required responses: {', '.join(missing)}"
        )
    failed = []
    for field in fields:
        value = item.responses.get(field["id"])
        values = value if isinstance(value, list) else [value]
        if any(candidate in field.get("failure_values", []) for candidate in values):
            failed.append(field)
    item.result = "failed" if failed else ("passed_with_observations" if item.notes else "passed")
    item.status = "completed"
    item.completed_at = datetime.now(UTC)
    for field in failed:
        if field.get("create_plan_on_failure"):
            db.add(
                Plan(
                    vehicle_id=vehicle_id,
                    created_by=user.id,
                    kind="repair",
                    priority="high",
                    description=f"Inspection: {field['label']}",
                    stage="planned",
                )
            )
    if item.odometer is not None:
        db.add(
            OdometerReading(
                vehicle_id=vehicle_id,
                created_by=user.id,
                recorded_on=item.recorded_on,
                reading=item.odometer,
                notes=f"Inspection: {item.template_snapshot['name']}",
            )
        )
        await db.flush()
        await _recalculate(vehicle_id, db)
    await db.commit()
    await db.refresh(item)
    return item
