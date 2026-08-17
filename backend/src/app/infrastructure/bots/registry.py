"""Immutable process-private registry of one runtime per enabled bot app."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from types import MappingProxyType

from app.core.bots.ids import BotAppId
from app.infrastructure.bots.runtime import BotRuntime


class BotRuntimeRegistry:
    """Expose exact runtime lookup only to bootstrap and webhook delivery adapters."""

    def __init__(self, runtimes: Iterable[BotRuntime]) -> None:
        by_app_id: dict[BotAppId, BotRuntime] = {}
        for runtime in runtimes:
            if runtime.app_id in by_app_id:
                raise ValueError(f"Bot runtime '{runtime.app_id}' is registered more than once.")
            by_app_id[runtime.app_id] = runtime
        self._runtimes = MappingProxyType(by_app_id)
        self._closed = False

    def get(self, app_id: BotAppId) -> BotRuntime | None:
        """Return only the runtime selected by the verified public app ID."""

        return self._runtimes.get(app_id)

    async def close(self) -> None:
        """Close every logical provider client once, even after one close failure."""

        if self._closed:
            return
        self._closed = True
        results = await asyncio.gather(
            *(runtime.close() for runtime in self._runtimes.values()),
            return_exceptions=True,
        )
        failures = [result for result in results if isinstance(result, BaseException)]
        if failures:
            raise RuntimeError("One or more bot provider clients failed to close.")
