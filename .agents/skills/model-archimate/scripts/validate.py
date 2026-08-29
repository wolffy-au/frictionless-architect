#!/usr/bin/env python3
"""Validate an ArchiMate model with pyArchimate's metamodel checks.

Run ephemerally:

    uv run --with 'pyArchimate==1.12.3' --python 3.12 \
        python validate.py MODEL[.archimate|.xml] [--json]

Exit 0 = clean, 1 = violations found, 2 = could not load the model.
"""
from __future__ import annotations

import argparse
import json
import sys

try:
    from pyArchimate import Model, check_valid_relationship
except ImportError:
    sys.stderr.write(
        "pyArchimate not importable. Run via:\n"
        "  uv run --with 'pyArchimate==1.12.3' --python 3.12 python validate.py ...\n"
    )
    raise SystemExit(2) from None


def validate(path: str) -> dict:
    model = Model("validate")
    model.read(path)

    findings: list[dict] = []

    # 1. Relationship-matrix legality, endpoint by endpoint.
    for rel in model.relationships:
        src = getattr(rel.source, "type", None)
        tgt = getattr(rel.target, "type", None)
        if src is None or tgt is None:
            findings.append(
                {
                    "check": "dangling_relationship",
                    "id": rel.uuid,
                    "detail": f"{rel.type} has a missing endpoint",
                }
            )
            continue
        if not check_valid_relationship(rel.type, src, tgt):
            findings.append(
                {
                    "check": "illegal_relationship",
                    "id": rel.uuid,
                    "detail": f"{rel.type}: {src} -> {tgt} is not permitted by the ArchiMate 3.2 matrix",
                }
            )

    # 2. Model-wide re-validation (catches anything the per-rel loop missed).
    for uuid in model.check_invalid_relationships() or []:
        if not any(f["id"] == uuid for f in findings):
            findings.append(
                {"check": "invalid_relationship", "id": uuid, "detail": "fails check_invalid_relationships()"}
            )

    # 3. Referential integrity.
    for cid in model.check_invalid_conn() or []:
        findings.append({"check": "broken_connection", "id": cid, "detail": "connection with a broken reference"})
    for nid in model.check_invalid_nodes() or []:
        findings.append({"check": "orphan_view_node", "id": nid, "detail": "view node references an unknown element"})

    return {
        "path": path,
        "elements": len(model.elements),
        "relationships": len(model.relationships),
        "views": len(model.views),
        "findings": findings,
        "clean": not findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("model")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    try:
        result = validate(args.model)
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


if __name__ == "__main__":
    raise SystemExit(main())
