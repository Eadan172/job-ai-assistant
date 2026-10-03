"""In-process event fanout for the popup stream."""

from __future__ import annotations

import threading
from typing import Any


class EventHub:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._seq = 0
        self._lock = threading.Lock()

    def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._seq += 1
            item = {"seq": self._seq, **event}
            self._events.append(item)
            if len(self._events) > 200:
                self._events = self._events[-200:]
            return item

    def since(self, seq: int) -> list[dict[str, Any]]:
        with self._lock:
            return [item for item in self._events if item["seq"] > seq]


hub = EventHub()
