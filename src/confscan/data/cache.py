"""Small JSON disk cache with a hard staleness cap."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class DiskCache:
    def __init__(
        self, dir: str = ".cache", ttl_seconds: int = 3600, max_ttl_seconds: int = 172_800
    ):
        self.dir = Path(dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = min(ttl_seconds, max_ttl_seconds)
        self.max_ttl_seconds = max_ttl_seconds

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.dir / f"{digest}.json"

    def get(self, key: str):
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        age = time.time() - float(payload.get("ts", 0))
        if age > self.max_ttl_seconds or age > self.ttl_seconds:
            return None
        return payload.get("value")

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        path.write_text(
            json.dumps({"ts": time.time(), "value": value}, ensure_ascii=False),
            encoding="utf-8",
        )
