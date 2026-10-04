"""Simple cache for the visualiser payload."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, cast


class SchemaCache:
    """JSON file cache holding the last aggregated schema payload."""

    def __init__(self, path: Path) -> None:
        """Create a cache backed by a single file.

        Args:
            path: Location of the cache file (parent directories are created on save).
        """
        self.path = path

    def load(self) -> dict[str, Any] | None:
        """Read the cached payload.

        Returns:
            The decoded payload, or ``None`` when no cache file exists.
        """
        if not self.path.exists():
            return None
        with self.path.open(encoding="utf-8") as fh:
            return cast(dict[str, Any], json.load(fh))

    def save(self, payload: dict[str, Any]) -> None:
        """Write the payload to the cache file, creating parent directories.

        Args:
            payload: JSON-serialisable payload to persist.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    def age_seconds(self) -> float | None:
        """Report how old the cache file is.

        Returns:
            Seconds since the file was last modified, or ``None`` when it does not exist.
        """
        if not self.path.exists():
            return None
        return time.time() - self.path.stat().st_mtime
