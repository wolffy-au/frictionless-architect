#!/usr/bin/env python3
"""Flag explicit relationships that look like ArchiMate *derived* relationships.

ArchiMate 3.2 §3.5 defines a derivation rule: given A --r1--> B --r2--> C, a
relationship A --r3--> C may be *derived* (not modelled) where r3 is the
weaker of r1/r2 on the standard strength order:

    Composition > Aggregation > Assignment > Realization > Serving >
    Access > Influence > Triggering > Flow > Specialization > Association

pyArchimate does not compute this (see pyArchimate#139), so nothing stops a
model from carrying both the two-hop chain *and* an explicit direct
relationship that duplicates what the chain already implies. This script
looks for that duplication so it can be flagged instead of silently kept.

Scope: this only auto-checks the well-behaved subset of the order —
Composition, Aggregation, Assignment, Realization, Serving, Triggering,
Flow — chained through a single intermediate element. Access, Influence,
Specialization and Association are excluded: their derivation rules carry
extra conditions (read/write direction, motivation semantics, generalisation)
that a naive "weakest link" pass would get wrong. A relationship of those
types is never flagged here even when it looks redundant — that judgement is
left to a human.

Advisory only: exit 0 always. This is a warn-don't-block check, run
alongside `validate.py`, not a metamodel legality check.

    poetry run python check_derived.py MODEL[.archimate|.xml] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

try:
    from pyArchimate import Model
except ImportError:
    sys.stderr.write(
        "pyArchimate not importable — it's a dev dependency. Run via:\n"
        "  poetry run python check_derived.py ...   (or: poetry install --with dev)\n"
    )
    raise SystemExit(2) from None

# Strongest to weakest; only this subset is auto-checked (see module docstring).
STRENGTH = ["Composition", "Aggregation", "Assignment", "Realization", "Serving", "Triggering", "Flow"]
RANK = {t: i for i, t in enumerate(STRENGTH)}


def weaker(t1: str, t2: str) -> str:
    return t1 if RANK[t1] > RANK[t2] else t2


def check(path: str) -> dict:
    model = Model("check_derived")
    model.read(path)

    rels = [r for r in model.relationships if getattr(r.source, "uuid", None) and getattr(r.target, "uuid", None)]

    # incoming[B] = [(A, type, rel)] for A --type--> B ; outgoing[B] = [(C, type, rel)] for B --type--> C
    incoming: dict[str, list] = defaultdict(list)
    outgoing: dict[str, list] = defaultdict(list)
    direct: dict[tuple[str, str], list] = defaultdict(list)  # (A,C) -> [(type, rel)]

    for r in rels:
        direct[(r.source.uuid, r.target.uuid)].append((r.type, r))
        if r.type in RANK:
            incoming[r.target.uuid].append((r.source.uuid, r.type, r))
            outgoing[r.source.uuid].append((r.target.uuid, r.type, r))

    findings = []
    seen = set()
    for b, ins in incoming.items():
        outs = outgoing.get(b, [])
        for a, t1, r1 in ins:
            for c, t2, r2 in outs:
                if a == c:
                    continue
                derived_type = weaker(t1, t2)
                for direct_type, direct_rel in direct.get((a, c), []):
                    if direct_type != derived_type:
                        continue
                    key = (direct_rel.uuid, r1.uuid, r2.uuid)
                    if key in seen:
                        continue
                    seen.add(key)
                    via_name = getattr(model.elems_dict.get(b), "name", b)
                    findings.append(
                        {
                            "relationship": direct_rel.uuid,
                            "type": direct_type,
                            "source": r1.source.name,
                            "target": r2.target.name,
                            "via": via_name,
                            "chain": f"{t1} then {t2}",
                            "detail": (
                                f"{direct_type} {r1.source.name!r} -> "
                                f"{r2.target.name!r} duplicates the derived relationship "
                                f"already implied by {t1} -> {via_name!r} -> {t2}"
                            ),
                        }
                    )

    return {
        "path": path,
        "checked_relationships": len(rels),
        "findings": findings,
        "clean": not findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    try:
        result = check(args.model)
    except Exception as exc:  # noqa: BLE001 - surface any loader/parse error
        if args.json:
            print(json.dumps({"path": args.model, "error": str(exc), "clean": False}))
        else:
            sys.stderr.write(f"could not load {args.model}: {exc}\n")
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['path']}: {result['checked_relationships']} relationships checked")
        if result["clean"]:
            print("no likely-derived relationships found (in the auto-checked subset)")
        else:
            print(f"{len(result['findings'])} possible derived relationship(s) — advisory, review by hand:")
            for f in result["findings"]:
                print(f"  [{f['type']}] {f['detail']}")

    return 0  # advisory only — never fails the build


if __name__ == "__main__":
    raise SystemExit(main())
