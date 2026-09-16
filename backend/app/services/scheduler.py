"""The periodic notification run (RF-NOT-005).

This deployment has no worker process, so the schedule lives in the API as an
asyncio task. It opens its own session per tick — the request-scoped dependency
does not exist outside a request — and swallows everything, because a failed
tick must never take the API down with it.

Set `NOTIFICATION_INTERVAL_SECONDS=0` to turn it off and drive
`POST /api/v1/notifications/run` from an external scheduler instead.
"""

import asyncio
import contextlib
import logging

from app.core.config import get_settings
from app.db.session import get_sessionmaker
from app.services.notifications import run_once

logger = logging.getLogger(__name__)


async def _loop(interval: int) -> None:
    session_maker = get_sessionmaker()
    while True:
        # Wait first: a restart loop should not mean a send loop.
        await asyncio.sleep(interval)
        try:
            async with session_maker() as db:
                result = await run_once(db)
            if result.created or result.delivered or result.failed:
                logger.info(
                    "Notification run: %d created, %d delivered, %d failed",
                    result.created,
                    result.delivered,
                    result.failed,
                )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - a bad tick must not end the schedule
            logger.exception("Notification run failed")


def start() -> asyncio.Task[None] | None:
    interval = get_settings().notification_interval_seconds
    if interval <= 0:
        return None
    return asyncio.create_task(_loop(interval))


async def stop(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
