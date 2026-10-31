"""Hardening for file paths sourced from an environment variable.

Both `audit.py` and `config.py` let an environment variable override where
their file lives (research.md R3/R4) -- deliberately, so an operator can
relocate state/config outside the default home-dir location, and so tests
can redirect it to an isolated `tmp_path` (see `tests/unit/conftest.py`).
Passing that raw string straight into `pathlib.Path` is exactly the CWE-22
"path traversal" shape static analysis (Snyk Code) flags: an unsanitised
environment variable flowing into a filesystem path. `resolve_override`
normalises it -- defeating `../` segments and symlink tricks -- and confines
the result to one of the two trees this package ever legitimately points
at: the user's home directory (where both defaults live) or the OS temp
directory (where test isolation points it).
"""

from __future__ import annotations

import tempfile
from pathlib import Path


def resolve_override(raw: str, *, env_var: str) -> Path:
    """Resolve an environment-variable-sourced override path safely.

    Args:
        raw: The raw value of the environment variable.
        env_var: Its name, used only for the error message.

    Returns:
        The resolved, absolute path.

    Raises:
        ValueError: If `raw` resolves outside both the user's home
            directory and the system temp directory -- the only two trees
            this package's default paths and test fixtures ever use.
    """
    candidate = Path(raw).expanduser().resolve()
    allowed_roots = (Path.home().resolve(), Path(tempfile.gettempdir()).resolve())
    if not any(candidate == root or candidate.is_relative_to(root) for root in allowed_roots):
        msg = (
            f"{env_var}={raw!r} resolves to {candidate}, which is outside both the "
            "user's home directory and the system temp directory"
        )
        raise ValueError(msg)
    return candidate
