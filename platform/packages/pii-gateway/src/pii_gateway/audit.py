"""Metadata-only audit log: one JSON line per `scrub()` call (FR-011, research.md R3).

Never records the matched text or surrounding content -- only that a call happened,
which categories matched, and the action taken. The path is
`$PII_GATEWAY_AUDIT_PATH` if set, else
`~/.local/state/frictionless-architect/pii-gateway-audit.jsonl`.
"""

from __future__ import annotations

import contextlib
import os
from pathlib import Path

from pii_gateway.models import AuditEntry

PATH_ENV_VAR = "PII_GATEWAY_AUDIT_PATH"


def default_audit_path() -> Path:
    """Return where the audit log lives.

    Returns:
        ``$PII_GATEWAY_AUDIT_PATH`` if set, else
        ``~/.local/state/frictionless-architect/pii-gateway-audit.jsonl``.
    """
    override = os.environ.get(PATH_ENV_VAR)
    if override:
        return Path(override)
    return Path.home() / ".local" / "state" / "frictionless-architect" / "pii-gateway-audit.jsonl"


class AuditLogger:
    """Appends one metadata-only `AuditEntry` per `scrub()` call.

    `path` is resolved lazily, at `record()` time, rather than fixed at
    construction -- so a long-lived (e.g. module-level) logger still honors a
    `PII_GATEWAY_AUDIT_PATH` set after it was built (notably in tests).
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path

    def record(self, entry: AuditEntry) -> None:
        """Append `entry` as one JSON line, creating parent directories."""
        target = self._path or default_audit_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json())
            handle.write("\n")
        with contextlib.suppress(OSError):  # e.g. drvfs/9p mounts
            target.chmod(0o600)
