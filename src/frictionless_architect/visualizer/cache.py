"""Simple cache for the visualiser payload."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast


class SchemaCache:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        with self.path.open(encoding="utf-8") as fh:
            return cast(dict[str, Any], json.load(fh))

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    def age_seconds(self) -> float | None:
        if not self.path.exists():
            return None
        return time.time() - self.path.stat().st_mtime
