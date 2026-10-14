"""CLI entry point for the modelling-specification package.

Root's `architecture/model/build.py`, `architecture/model/render_diagrams.py` and the
`model-archimate` skill's `validate.py` are now thin wrappers shelling into this CLI
(ADR-0037, R2) -- `poetry run --directory platform python -m modelling_specification.cli
build|render|validate`. This is the one place the three entry points' behaviour lives.
"""

from __future__ import annotations

import argparse
import json
import sys

from modelling_specification import model_io, rendering


def _build(_args: argparse.Namespace) -> int:
    code, errors, warnings, result = model_io.write_and_validate()
    for msg in errors:
        sys.stderr.write(f"error: {msg}\n")
    if not errors:
        for msg in warnings:
            print(msg)
        assert result is not None
        print(
            f"wrote {model_io.OUT.relative_to(model_io.REPO_ROOT)}  "
            f"({result['elements']} elements, {result['relationships']} relationships)"
        )
        if result["clean"]:
            print("VALID — no metamodel or referential-integrity violations")
        else:
            print(f"INVALID — {len(result['findings'])} finding(s):")
            for f in result["findings"]:
                print(f"  [{f['check']}] {f['id']}: {f['detail']}")
    return code


def _render(args: argparse.Namespace) -> int:
    code, stale, orphan = rendering.render_diagrams(check=args.check, svg=not args.no_svg)
    if code == 2:
        sys.stderr.write(f"{rendering.MODEL_REL} missing — run `build` first\n")
        return 2
    if args.check:
        for f in stale:
            print(f"STALE   {f}")
        for f in orphan:
            print(f"ORPHAN  {f}")
        if stale or orphan:
            print("\nrun: poetry run python -m modelling_specification.cli render")
        else:
            print("diagrams up to date")
        return code
    for f in stale:
        print(f"regenerated {f}")
    for f in orphan:
        print(f"removed {f}")
    if not (stale or orphan):
        print("diagrams already up to date, nothing regenerated")
    return code


def _validate(args: argparse.Namespace) -> int:
    try:
        result = model_io.validate_model(args.model)
    except Exception as exc:  # noqa: BLE001 - surface any loader/parse error
        if args.json:
            print(json.dumps({"path": args.model, "error": str(exc), "clean": False}))
        else:
            sys.stderr.write(f"could not load {args.model}: {exc}\n")
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"{result['path']}: {result['elements']} elements, "
            f"{result['relationships']} relationships, {result['views']} views"
        )
        if result["clean"]:
            print("VALID — no metamodel or referential-integrity violations")
        else:
            print(f"INVALID — {len(result['findings'])} finding(s):")
            for f in result["findings"]:
                print(f"  [{f['check']}] {f['id']}: {f['detail']}")
    return 0 if result["clean"] else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="modelling_specification", description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="load elements.yaml/relationships.yaml/views.yaml, write and validate the XML")

    render_ap = sub.add_parser("render", help="regenerate diagrams from the built XML")
    render_ap.add_argument("--check", action="store_true", help="fail if committed diagrams are stale")
    render_ap.add_argument("--no-svg", action="store_true", help="write .puml only")

    validate_ap = sub.add_parser("validate", help="run pyArchimate's metamodel checks against a model file")
    validate_ap.add_argument("model")
    validate_ap.add_argument("--json", action="store_true", help="machine-readable output")

    args = ap.parse_args(argv)
    handler = {"build": _build, "render": _render, "validate": _validate}[args.command]
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
