from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any


@dataclass(frozen=True)
class ContextKey:
    platform: str
    session: str
    user: str
    module: str = "ow"

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (self.platform, self.session, self.user, self.module)


class ContextCache:
    def __init__(self, ttl_seconds: int = 1800, max_size: int = 256) -> None:
        self.ttl_seconds = max(1, int(ttl_seconds))
        self.max_size = max(1, int(max_size))
        self._items: OrderedDict[tuple[str, str, str, str], dict[str, Any]] = OrderedDict()
        self._lock = RLock()

    def get(self, key: ContextKey) -> dict[str, Any] | None:
        with self._lock:
            item = self._items.get(key.as_tuple())
            if not item:
                return None
            if time.time() >= float(item.get("expires_at", 0)):
                self._items.pop(key.as_tuple(), None)
                return None
            self._items.move_to_end(key.as_tuple())
            value = item.get("value")
            return dict(value) if isinstance(value, dict) else None

    def set(self, key: ContextKey, value: dict[str, Any]) -> None:
        with self._lock:
            self._items[key.as_tuple()] = {
                "value": dict(value),
                "expires_at": time.time() + self.ttl_seconds,
            }
            self._items.move_to_end(key.as_tuple())
            while len(self._items) > self.max_size:
                self._items.popitem(last=False)
