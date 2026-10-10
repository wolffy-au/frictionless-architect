#!/usr/bin/env python3
"""Thin wrapper: shells into the modelling-specification platform package's CLI
`validate` subcommand (ADR-0037, R2, spec.md Assumption 1).

    poetry run python validate.py MODEL[.archimate|.xml] [--json]

The pyArchimate metamodel-check logic this used to hold directly now lives in
`platform/packages/modelling-specification/src/modelling_specification/model_io.py`'s
`validate_model()`, shared with the chat router's own validation path so the skill and
the running agent never diverge on what counts as a violation.

Exit 0 = clean, 1 = violations found, 2 = could not load the model.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[4] / "platform"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    model_path = str(Path(args.model).resolve())
    cmd = ["poetry", "run", "python", "-m", "modelling_specification.cli", "validate", model_path]
    if args.json:
        cmd.append("--json")
    result = subprocess.run(cmd, cwd=PLATFORM)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
