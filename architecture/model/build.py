#!/usr/bin/env python3
"""Thin wrapper: shells into the modelling-specification platform package's CLI
`build` subcommand (ADR-0037, R2).

    poetry run python architecture/model/build.py

The YAML load/merge/validate/write logic this used to hold directly now lives in
`platform/packages/modelling-specification/src/modelling_specification/model_io.py`,
shared with the chat router's in-memory validate-before-write path (R9). This keeps
ADR-0001's root-never-imports-a-platform-package boundary intact -- root only shells
out, as before, just via the platform venv's CLI instead of holding its own
pyArchimate-based implementation.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[2] / "platform"


def main() -> int:
    # platform/ has its own poetry.lock and virtualenv (ADR-0002) -- `poetry run`
    # from there, not `sys.executable`, which is root's own venv and does not
    # have `modelling_specification` installed.
    #
    # That venv is keyed by project name/lock hash, not by checkout path, so it
    # is shared across git worktrees of this repo; whichever checkout last ran
    # `poetry install` baked its own absolute path into the editable install.
    # Prepending each package's own src/ here makes this invocation always use
    # THIS checkout's source, regardless of which one the venv was installed
    # from -- without touching (and so without disturbing) the shared venv.
    pythonpath = os.pathsep.join(str(src) for src in sorted((PLATFORM / "packages").glob("*/src")) if src.is_dir())
    env = {**os.environ, "PYTHONPATH": pythonpath}
    result = subprocess.run(
        ["poetry", "run", "python", "-m", "modelling_specification.cli", "build"],
        cwd=PLATFORM,
        env=env,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
