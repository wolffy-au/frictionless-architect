#!/usr/bin/env python3
"""Thin wrapper: shells into the modelling-specification platform package's
`c4` module (ADR-0045).

    poetry run python model_to_c4.py MODEL --system "Name" \
        [--level context|container] [--layout WITH_LEGEND|TOP_DOWN|LEFT_RIGHT] [-o OUT.puml]

Applies the ArchiMate-to-C4 mapping in
`platform/packages/modelling-specification/src/modelling_specification/c4.py`,
which this used to hold directly -- also used in-process by `rendering.py`'s
batch diagram regeneration. Exit 0 = wrote output, 2 = load/lookup error.
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


def pop_output(args: list[str]) -> Path | None:
    """Remove `-o`/`--output VALUE` from `args`, returning it resolved against the caller's cwd."""
    for flag in ("-o", "--output"):
        if flag in args:
            i = args.index(flag)
            value = args[i + 1]
            del args[i : i + 2]
            return Path(value).resolve()
    return None


def main() -> int:
    argv = sys.argv[1:]
    if not argv:
        sys.stderr.write("usage: model_to_c4.py MODEL --system NAME ...\n")
        return 2
    args = list(argv)
    args[0] = str(Path(args[0]).resolve())
    output = pop_output(args)
    cmd = ["poetry", "run", "python", "-m", "modelling_specification.c4", *args]
    # The package only prints (ADR-0045); `-o` is this script's to honour.
    result = subprocess.run(
        cmd, cwd=PLATFORM, env=platform_env(), stdout=subprocess.PIPE if output else None, text=True
    )
    if output and result.returncode == 0:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(result.stdout.rstrip("\n") + "\n")
        sys.stderr.write(f"wrote {output}\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
