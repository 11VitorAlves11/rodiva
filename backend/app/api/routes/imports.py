"""CSV import: mapped columns, regional values, dry-run validation and atomic commit."""

import contextlib
import csv
import hashlib
import io
import json
import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.api.deps import CurrentMembership, CurrentUser, DbSession
from app.api.routes.fuel import _recalculate_consumption
from app.api.routes.odometer import _recalculate, _vehicle_in_household
from app.db.filters import active
from app.models import ExpenseRecord, FuelRecord, Note, OdometerReading, Role, Vehicle, WorkRecord
from app.models.import_batch import ImportBatch
from app.schemas.expenses import ExpenseRecordIn
from app.schemas.fuel import FuelRecordIn
from app.schemas.notes import NoteIn
from app.schemas.odometer import OdometerReadingIn
from app.schemas.work_records import WorkRecordIn

router = APIRouter(prefix="/imports", tags=["imports"])
Kind = Literal["fuel", "work", "expenses", "odometer", "notes"]
SCHEMAS: dict[str, type[BaseModel]] = {
    "fuel": FuelRecordIn,
    "work": WorkRecordIn,
    "expenses": ExpenseRecordIn,
    "odometer": OdometerReadingIn,
    "notes": NoteIn,
}
MODELS: dict[str, Any] = {
    "fuel": FuelRecord,
    "work": WorkRecord,
    "expenses": ExpenseRecord,
    "odometer": OdometerReading,
    "notes": Note,
}
NUMBERS = {
    "reading",
    "start_reading",
    "odometer_reading",
    "volume_litres",
    "total_price",
    "unit_price",
    "total_cost",
    "amount",
}
EXAMPLES = {
    "recorded_on": "2026-01-15",
    "issued_on": "2026-01-15",
    "volume_litres": "40.000",
    "total_price": "65.00",
    "unit_price": "",
    "kind": "maintenance",
    "description": "Revisão",
    "amount": "25.00",
    "category": "parking",
    "reading": "10000",
    "title": "Nota",
    "content": "Observações",
    "full_tank": "true",
}


class ImportIn(BaseModel):
    vehicle_id: uuid.UUID
    kind: Kind
    csv_text: str = Field(min_length=1, max_length=1_000_000)
    mapping: dict[str, str] = Field(default_factory=dict, max_length=50)
    locale: Literal["pt-PT", "en"] = "pt-PT"


@router.get("/{kind}/template.csv")
async def template(
    kind: Kind, membership: CurrentMembership, locale: Literal["pt-PT", "en"] = "pt-PT"
) -> Response:
    fields = list(SCHEMAS[kind].model_fields)
    stream = io.StringIO()
    writer = csv.writer(stream, delimiter=";" if locale == "pt-PT" else ",")
    writer.writerow(fields)
    writer.writerow([EXAMPLES.get(field, "") for field in fields])
    return Response(
        "\ufeff" + stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="rodiva-{kind}-template.csv"'},
    )


def parse(payload: ImportIn) -> tuple[list[str], list[dict[str, Any]]]:
    text = payload.csv_text.lstrip("\ufeff")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    columns = list(reader.fieldnames or [])
    if not columns or len(columns) != len(set(columns)) or any(not col.strip() for col in columns):
        raise HTTPException(status_code=422, detail="CSV needs unique, non-empty column headers")
    fields = SCHEMAS[payload.kind].model_fields
    if any(
        key not in fields or (value and value not in columns)
        for key, value in payload.mapping.items()
    ):
        raise HTTPException(status_code=422, detail="Unknown column mapping")
    rows: list[dict[str, Any]] = []
    try:
        for number, raw in enumerate(reader, start=2):
            if len(rows) >= 500:
                raise HTTPException(status_code=422, detail="Import at most 500 rows at a time")
            errors = []
            data: dict[str, Any] = {}
            if None in raw:
                errors.append("Row has more values than column headers")
            for field in fields:
                column = payload.mapping.get(field, field)
                value = (raw.get(column) or "").strip()
                if not value:
                    continue
                if field in NUMBERS and payload.locale == "pt-PT":
                    value = value.replace(" ", "").replace("\u00a0", "")
                    if "," in value:
                        value = value.replace(".", "").replace(",", ".")
                if field in {"recorded_on", "issued_on"} and "/" in value:
                    with contextlib.suppress(ValueError):
                        value = (
                            datetime.strptime(
                                value, "%d/%m/%Y" if payload.locale == "pt-PT" else "%m/%d/%Y"
                            )
                            .date()
                            .isoformat()
                        )
                data[field] = value
            try:
                validated = SCHEMAS[payload.kind].model_validate(data)
                data = validated.model_dump(mode="json")
            except ValidationError as exc:
                errors.extend(
                    f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in exc.errors()
                )
            rows.append({"line": number, "data": data, "errors": errors})
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail="Invalid CSV") from exc
    if not rows:
        raise HTTPException(status_code=422, detail="CSV contains no records")
    return columns, rows


async def execute(
    payload: ImportIn, user: CurrentUser, membership: CurrentMembership, db: DbSession, commit: bool
) -> dict[str, Any]:
    await _vehicle_in_household(payload.vehicle_id, membership, db)
    if membership.role not in {Role.OWNER, Role.MANAGER, Role.EDITOR}:
        raise HTTPException(status_code=403, detail="Role cannot import records")
    columns, rows = parse(payload)
    result: dict[str, Any] = {
        "columns": columns,
        "fields": list(SCHEMAS[payload.kind].model_fields),
        "rows": rows,
        "errors": [],
        "imported": 0,
    }
    if any(row["errors"] for row in rows):
        if commit:
            raise HTTPException(status_code=422, detail="Correct the invalid rows before importing")
        return result
    fingerprint = hashlib.sha256(
        json.dumps(
            {"kind": payload.kind, "rows": [row["data"] for row in rows]}, sort_keys=True
        ).encode()
    ).hexdigest()
    # Serialize concurrent imports for the same vehicle before the deduplication check.
    await db.scalar(
        select(Vehicle).where(Vehicle.id == payload.vehicle_id, active(Vehicle)).with_for_update()
    )
    previous = await db.scalar(
        select(ImportBatch).where(
            ImportBatch.vehicle_id == payload.vehicle_id, ImportBatch.fingerprint == fingerprint
        )
    )
    if previous:
        result["already_imported"] = True
        result["imported"] = previous.count if commit else 0
        return result
    transaction = await db.begin_nested()
    try:
        for row in rows:
            data = SCHEMAS[payload.kind].model_validate(row["data"]).model_dump()
            db.add(MODELS[payload.kind](vehicle_id=payload.vehicle_id, created_by=user.id, **data))
            if payload.kind in {"fuel", "work"} and data.get("odometer_reading") is not None:
                db.add(
                    OdometerReading(
                        vehicle_id=payload.vehicle_id,
                        created_by=user.id,
                        recorded_on=data["recorded_on"],
                        reading=data["odometer_reading"],
                        notes="Leitura de importação CSV",
                    )
                )
        await db.flush()
        if payload.kind in {"odometer", "fuel", "work"}:
            await _recalculate(payload.vehicle_id, db)
        if payload.kind == "fuel":
            await _recalculate_consumption(payload.vehicle_id, db)
        if commit:
            db.add(
                ImportBatch(
                    vehicle_id=payload.vehicle_id,
                    created_by=user.id,
                    kind=payload.kind,
                    fingerprint=fingerprint,
                    count=len(rows),
                )
            )
            await transaction.commit()
            await db.commit()
            result["imported"] = len(rows)
        else:
            await transaction.rollback()
    except HTTPException as exc:
        await transaction.rollback()
        if commit:
            raise
        result["errors"].append(str(exc.detail))
    return result


@router.post("/preview")
async def preview(
    payload: ImportIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> dict[str, Any]:
    return await execute(payload, user, membership, db, commit=False)


@router.post("/commit")
async def commit_import(
    payload: ImportIn, user: CurrentUser, membership: CurrentMembership, db: DbSession
) -> dict[str, Any]:
    return await execute(payload, user, membership, db, commit=True)
