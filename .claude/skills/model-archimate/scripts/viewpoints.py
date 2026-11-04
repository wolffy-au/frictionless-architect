#!/usr/bin/env python3
"""Thin wrapper: shells into the modelling-specification platform package's
`viewpoints` module (ADR-0045).

    poetry run python viewpoints.py list
    poetry run python viewpoints.py show value_stream
    poetry run python viewpoints.py check MODEL[.xml|.archimate] --view "Name" --viewpoint value_stream

The standard-viewpoint lookup and conformance-check logic this used to hold
directly now lives in
`platform/packages/modelling-specification/src/modelling_specification/viewpoints.py`,
shared with `model_io.py`'s own build-time viewpoint check so the skill and the
running build never diverge on what counts as conformant.

Exit 0 = conformant / info printed, 1 = non-conformant, 2 = bad input.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[4] / "platform"


def platform_env() -> dict[str, str]:
    """The environment minus VIRTUAL_ENV, so `poetry run` in platform/ picks the platform venv.

    Under `poetry run` from the repo root, VIRTUAL_ENV names root's venv, and a nested `poetry run`
    reuses it instead of platform/'s own, where `modelling_specification` lives.
    """
    return {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}


def main() -> int:
    cmd = ["poetry", "run", "python", "-m", "modelling_specification.viewpoints", *sys.argv[1:]]
    return subprocess.run(cmd, cwd=PLATFORM, env=platform_env()).returncode


if __name__ == "__main__":
    raise SystemExit(main())
