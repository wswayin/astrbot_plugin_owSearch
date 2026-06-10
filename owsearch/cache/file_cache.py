from __future__ import annotations

import hashlib
from pathlib import Path


class FileCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for_key(self, key: str, suffix: str = ".bin") -> Path:
        digest = hashlib.sha256(str(key).encode("utf-8")).hexdigest()
        return self.root / f"{digest}{suffix}"
