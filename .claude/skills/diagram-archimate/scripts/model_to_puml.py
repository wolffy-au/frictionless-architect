#!/usr/bin/env python3
"""Thin wrapper: shells into the modelling-specification platform package's
`puml` module (ADR-0045).

    poetry run python model_to_puml.py MODEL[.archimate|.xml] [--view NAME] [-o OUT.puml]
        [--no-direction TYPE ...] [--context CTX] [--max-width PX]

Emits PlantUML using the bundled `<archimate/Archimate>` stdlib. See
`platform/packages/modelling-specification/src/modelling_specification/puml.py`
for the full flag reference and generation logic, which this used to hold
directly -- also used in-process by `rendering.py`'s batch diagram regeneration.

Exit 0 = wrote output, 2 = load/lookup error.
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
    argv = sys.argv[1:]
    if not argv:
        sys.stderr.write("usage: model_to_puml.py MODEL [--view NAME] [-o OUT.puml] ...\n")
        return 2
    args = list(argv)
    args[0] = str(Path(args[0]).resolve())
    for flag in ("-o", "--output"):
        if flag in args:
            i = args.index(flag)
            args[i + 1] = str(Path(args[i + 1]).resolve())
    cmd = ["poetry", "run", "python", "-m", "modelling_specification.puml", *args]
    return subprocess.run(cmd, cwd=PLATFORM, env=platform_env()).returncode


if __name__ == "__main__":
    raise SystemExit(main())
