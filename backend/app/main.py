from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    attachments,
    auth,
    expenses,
    fuel,
    health,
    notes,
    odometer,
    reminders,
    vehicles,
    work_records,
)
from app.core.config import get_settings
from app.db.session import dispose_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_engine()


app = FastAPI(title=f"{settings.app_name} API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth.router)
app.include_router(vehicles.router, prefix="/api")
app.include_router(odometer.router, prefix="/api")
app.include_router(fuel.router, prefix="/api")
app.include_router(work_records.router, prefix="/api")
app.include_router(expenses.router, prefix="/api")
app.include_router(reminders.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(attachments.router, prefix="/api")
app.mount("/storage", StaticFiles(directory=settings.storage_path, check_dir=False), name="storage")


@app.get("/api")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": "0.1.0"}
