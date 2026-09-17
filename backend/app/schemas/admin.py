from pydantic import BaseModel


class StorageUsage(BaseModel):
    path: str
    exists: bool
    #: False when the directory is there but cannot be walked — a permission
    #: problem that would otherwise only show up as failed uploads.
    readable: bool = True
    used_bytes: int = 0
    free_bytes: int = 0


class TaskStatus(BaseModel):
    notifications_interval_seconds: int
    notifications_running: bool


class InstanceStatus(BaseModel):
    app_name: str
    version: str
    environment: str
    auth_mode: str
    public_registration: bool
    database_reachable: bool
    database_version: str
    migration_revision: str | None
    storage: StorageUsage
    tasks: TaskStatus
    integrations: dict[str, bool]
    counts: dict[str, int]
