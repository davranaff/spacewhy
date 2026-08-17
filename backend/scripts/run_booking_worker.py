"""Run booking background work as one explicit process, never inside the ASGI lifespan."""

from __future__ import annotations

import asyncio
import signal
from contextlib import suppress

from app.bootstrap.booking_worker import create_booking_worker
from app.bootstrap.container import create_container
from app.core.config.settings import Settings
from app.core.observability.logging import configure_logging


async def _run() -> None:
    """Initialize only the resources required by the durable booking worker."""

    settings = Settings()
    configure_logging(settings)
    container = create_container(settings)
    container.database.initialize()
    container.telemetry.initialize()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(shutdown_signal, stop_event.set)
    try:
        await container.bot_platform.initialize()
        await create_booking_worker(container).run_forever(stop_event=stop_event)
    finally:
        await container.bot_platform.shutdown()
        await container.telemetry.shutdown()
        await container.database.dispose()


def main() -> None:
    """Start the worker under a fresh event loop."""

    asyncio.run(_run())


if __name__ == "__main__":
    main()
