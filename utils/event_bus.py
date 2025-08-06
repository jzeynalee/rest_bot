# --------------------------------------------------------------------
# utils/event_bus.py
# --------------------------------------------------------------------
"""A super‑light, asyncio‑based pub/sub that the whole bot can import.
Place this file at rest_bot/utils/event_bus.py"""
from __future__ import annotations
import asyncio
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List, Tuple

_Handler = Callable[[object], Awaitable[None] or None]


class _EventBus:
    def __init__(self) -> None:
        self._subs: Dict[str, List[_Handler]] = defaultdict(list)
        self._q: asyncio.Queue[tuple[str, object]] = asyncio.Queue()
        # background task started lazily on first publish
        self._task: asyncio.Task | None = None

    # -------------------------------------------------------------- #
    def subscribe(self, topic: str, fn: _Handler) -> None:
        self._subs[topic].append(fn)

    def publish(self, topic: str, payload: object) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._worker())
        self._q.put_nowait((topic, payload))

    # -------------------------------------------------------------- #
    async def _worker(self) -> None:
        while True:
            topic, payload = await self._q.get()
            for fn in self._subs.get(topic, []):
                try:
                    res = fn(payload)
                    if asyncio.iscoroutine(res):
                        await res
                except Exception as exc:  # pragma: no cover – keep bus alive
                    print("[event_bus] handler error:", exc)

# singleton – import this everywhere
BUS = _EventBus()

# convenience shims so callers don’t care about the BUS name
subscribe = BUS.subscribe
publish = BUS.publish