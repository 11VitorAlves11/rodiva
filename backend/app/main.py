from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.routes import (
    attachments,
    auth,
    calendar,
    expenses,
    fuel,
    health,
    households,
    inventory,
    notes,
    odometer,
    plans,
    reminders,
    storage,
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
install_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Preserve existing clients while making v1 the documented integration API.
for resource in [
    health,
    calendar,
    households,
    inventory,
    vehicles,
    odometer,
    plans,
    fuel,
    work_records,
    expenses,
    reminders,
    notes,
    attachments,
]:
    app.include_router(resource.router, prefix="/api", include_in_schema=False)
    app.include_router(resource.router, prefix="/api/v1")
app.include_router(auth.router)
app.include_router(storage.router)


@app.get("/api")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": "0.1.0"}
