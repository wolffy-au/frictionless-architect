#!/usr/bin/env python3
"""Thin wrapper: shells into the modelling-specification platform package's CLI
`render` subcommand (ADR-0037, R2).

    poetry run python architecture/model/render_diagrams.py [--check] [--no-svg]

Run `build.py` first (this reads the generated XML, it does not rebuild it). The
view->PlantUML->SVG regeneration logic this used to hold directly now lives in
`platform/packages/modelling-specification/src/modelling_specification/rendering.py`.

Exit 0 = up to date / written, 1 = stale (`--check`), 2 = error.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[2] / "platform"


def platform_env() -> dict[str, str]:
    """The environment minus VIRTUAL_ENV, so `poetry run` in platform/ picks the platform venv.

    Under `poetry run` from the repo root, VIRTUAL_ENV names root's venv, and a nested `poetry run`
    reuses it instead of platform/'s own, where `modelling_specification` lives.
    """
    return {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail if committed diagrams are stale")
    ap.add_argument("--no-svg", action="store_true", help="write .puml only")
    args = ap.parse_args()

    cmd = ["poetry", "run", "python", "-m", "modelling_specification.cli", "render"]
    if args.check:
        cmd.append("--check")
    if args.no_svg:
        cmd.append("--no-svg")
    # platform/'s venv is keyed by project name/lock hash, not checkout path, so
    # it's shared across git worktrees; whichever checkout last ran `poetry
    # install` baked its own absolute path into the editable install. Prepending
    # each package's own src/ makes this invocation use THIS checkout's source
    # regardless of which one the venv was installed from (see build.py).
    pythonpath = os.pathsep.join(str(src) for src in sorted((PLATFORM / "packages").glob("*/src")) if src.is_dir())
    env = {**platform_env(), "PYTHONPATH": pythonpath}
    result = subprocess.run(cmd, cwd=PLATFORM, env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
