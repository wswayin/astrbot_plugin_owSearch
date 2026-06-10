from __future__ import annotations

import time
from pathlib import Path
from threading import RLock

from ..models import PlayerIdentity
from ..utils.json import read_json_file, write_json_file


def _key_for_bnet(value: str) -> str:
    return str(value or "").strip().casefold()


class IdentityStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = RLock()
        self._loaded = False
        self._data: dict[str, dict] = {}

    def _ensure_loaded(self) -> None:
        with self._lock:
            if self._loaded:
                return
            payload = read_json_file(self.path, {"players": {}})
            players = payload.get("players") if isinstance(payload, dict) else {}
            self._data = players if isinstance(players, dict) else {}
            self._loaded = True

    def get(self, bnet_id: str) -> PlayerIdentity | None:
        self._ensure_loaded()
        key = _key_for_bnet(bnet_id)
        with self._lock:
            item = self._data.get(key)
            if not isinstance(item, dict):
                return None
            identity_payload = item.get("identity")
            if not isinstance(identity_payload, dict):
                return None
            identity = PlayerIdentity.from_cache(identity_payload)
            return identity if identity.customer_token else None

    def put(self, identity: PlayerIdentity) -> None:
        self._ensure_loaded()
        keys = {_key_for_bnet(identity.query), _key_for_bnet(identity.full_id)}
        with self._lock:
            for key in keys:
                if not key:
                    continue
                self._data[key] = {
                    "updated_at": int(time.time()),
                    "identity": identity.to_cache(),
                }
            write_json_file(self.path, {"players": self._data})

    def clear(self, bnet_id: str) -> None:
        self._ensure_loaded()
        key = _key_for_bnet(bnet_id)
        with self._lock:
            self._data.pop(key, None)
            write_json_file(self.path, {"players": self._data})
