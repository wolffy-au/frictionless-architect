#!/usr/bin/env python3
"""Flag explicit relationships that look like ArchiMate *derived* relationships.

ArchiMate 3.2 §3.5 defines a derivation rule: given A --r1--> B --r2--> C, a
relationship A --r3--> C may be *derived* (not modelled) where r3 is implied
by the pair (r1, r2) per Appendix B.2's derivation rules (DR2, DR3, DR5, DR7,
DR8). Nothing stops a model from carrying both the two-hop chain *and* an
explicit direct relationship that duplicates what the chain already implies.
This script looks for that duplication so it can be flagged instead of
silently kept.

Computation is delegated to ``pyArchimate.derivation`` (spec
015-derived-relationships, GitHub issue #140), which implements DR2/DR3/DR5/
DR7/DR8 for the seven "certain" relationship types (Composition, Aggregation,
Assignment, Realization, Serving, Triggering, Flow) chained through a single
intermediate element.

Extended scope (GitHub issue #146, ``include_dependency=True``) is enabled
by default here: Access, Influence, and Association also become eligible to
participate in chains, plus one additional best-effort rule from Appendix
B.3 (Influence-then-structural, forward, in-line, derives Influence). Access
and Association remain chainable but yield no derivation of their own —
see ``pyArchimate.derivation``'s module docstring for the full rationale.
Pass ``--strict`` to fall back to the narrower default (dependency types
excluded) if the extended scope turns out to be too noisy for a given model.

Specialization is out of scope for both modes: its derivation rule carries
generalisation semantics that chain discovery does not model.

Advisory only: exit 0 always. This is a warn-don't-block check, run
alongside `validate.py`, not a metamodel legality check.

    poetry run python check_derived.py MODEL[.archimate|.xml] [--json] [--strict]
"""

from __future__ import annotations

import argparse
import json
import sys

try:
    from pyArchimate import Model
    from pyArchimate.derivation import find_duplicate_relationships
except ImportError:
    sys.stderr.write(
        "pyArchimate not importable — it's a dev dependency. Run via:\n"
        "  poetry run python check_derived.py ...   (or: poetry install --with dev)\n"
    )
    raise SystemExit(2) from None


def check(path: str, include_dependency: bool = True) -> dict:
    model = Model("check_derived")
    model.read(path)

    findings = []
    for duplicate in find_duplicate_relationships(model, include_dependency=include_dependency):
        rel = duplicate.relationship
        for chain in duplicate.implying_chains:
            via = chain.intermediate
            findings.append(
                {
                    "relationship": rel.uuid,
                    "type": rel.type,
                    "source": chain.leg1.source.name,
                    "target": chain.leg2.target.name,
                    "via": via.name,
                    "chain": f"{chain.leg1.type} then {chain.leg2.type}",
                    "detail": (
                        f"{rel.type} {chain.leg1.source.name!r} -> "
                        f"{chain.leg2.target.name!r} duplicates the derived relationship "
                        f"already implied by {chain.leg1.type} -> {via.name!r} -> {chain.leg2.type}"
                    ),
                }
            )

    return {
        "path": path,
        "checked_relationships": len(model.rels_dict),
        "extended_scope": include_dependency,
        "findings": findings,
        "clean": not findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="use the narrower Appendix B.2 scope only (exclude Access/Influence/Association chaining)",
    )
    args = ap.parse_args()

    try:
        result = check(args.model, include_dependency=not args.strict)
    except Exception as exc:  # noqa: BLE001 - surface any loader/parse error
        if args.json:
            print(json.dumps({"path": args.model, "error": str(exc), "clean": False}))
        else:
            sys.stderr.write(f"could not load {args.model}: {exc}\n")
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        scope = "extended" if result["extended_scope"] else "strict"
        print(f"{result['path']}: {result['checked_relationships']} relationships checked ({scope} scope)")
        if result["clean"]:
            print("no likely-derived relationships found")
        else:
            print(f"{len(result['findings'])} possible derived relationship(s) — advisory, review by hand:")
            for f in result["findings"]:
                print(f"  [{f['type']}] {f['detail']}")

    return 0  # advisory only — never fails the build


if __name__ == "__main__":
    raise SystemExit(main())
