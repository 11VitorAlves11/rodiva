from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.errors import install_error_handlers
from app.api.routes import (
    api_keys,
    attachments,
    audit,
    auth,
    calendar,
    charging,
    equipment,
    expenses,
    fuel,
    health,
    households,
    imports,
    inspections,
    inventory,
    notes,
    notifications,
    odometer,
    plans,
    reminders,
    reports,
    search,
    storage,
    trash,
    vehicles,
    webhooks,
    work_records,
)
from app.api.security_headers import install_security_headers
from app.core.config import get_settings
from app.db.session import dispose_engine
from app.services import scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = scheduler.start()
    yield
    await scheduler.stop(task)
    await dispose_engine()


app = FastAPI(title=f"{settings.app_name} API", version="0.1.0", lifespan=lifespan)
install_error_handlers(app)
install_security_headers(app, hsts=settings.hsts_enabled)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Outermost, so a forged Host is refused before any handler builds a link from it.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

# Preserve existing clients while making v1 the documented integration API.
for resource in [
    api_keys,
    audit,
    charging,
    imports,
    health,
    calendar,
    equipment,
    households,
    inventory,
    inspections,
    vehicles,
    odometer,
    plans,
    fuel,
    work_records,
    expenses,
    reminders,
    reports,
    search,
    notes,
    notifications,
    attachments,
    trash,
    webhooks,
]:
    app.include_router(resource.router, prefix="/api", include_in_schema=False)
    app.include_router(resource.router, prefix="/api/v1")
app.include_router(auth.router)
app.include_router(storage.router)


@app.get("/api")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": "0.1.0"}
