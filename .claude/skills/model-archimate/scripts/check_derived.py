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

Accepted exceptions (GH #99): a finding that is a deliberate, reviewed
duplication rather than an authoring mistake can be recorded in
`SERVING_EXCEPTIONS` / `_accepted_reason` below with a one-line reason,
instead of being removed from the source model. Accepted findings still
print (so the full picture stays visible) but are labelled `[accepted]` and
excluded from the "unexplained" count the exit summary is based on.

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


# --- Accepted exceptions (GH #99) ----------------------------------------
#
# Exact (type, source name, target name) duplicates that were reviewed and
# kept deliberately, each with a one-line reason. These are first-party,
# hand-authored relationships where the direct edge carries presentational
# weight the chain alone doesn't: the C4 projection (`diagram-c4`) only
# promotes ApplicationComponent elements to containers, so a chain that
# routes through an ApplicationInterface (e.g. `if-catalog-ui`,
# `if-twin-read-path`) disappears at the container level unless the direct
# Serving edge is also modelled. See `architecture/model/relationships.yaml`
# for the matching inline comments.
SERVING_EXCEPTIONS: dict[tuple[str, str, str], str] = {
    (
        "Serving",
        "Controls & Compliance Catalog",
        "Compliance Officer / Auditor",
    ): "kept for the C4 container view: if-catalog-ui (an ApplicationInterface) is dropped from the C4 projection, so this direct edge is the only one left there.",
    (
        "Serving",
        "Digital Twin & Knowledge Graph",
        "Schema Visualiser API",
    ): "kept for the C4 container view: if-twin-read-path (an ApplicationInterface) is dropped from the C4 projection, so this direct edge is the only one left there.",
}

# Any Flow duplicate between two IT4IT value-stream elements (names
# "IT4IT: ..."): the vendored third_party/it4it relationships.yaml (ADR-0029)
# carries the IT4IT standard's own dense, multi-directional value-stream Flow
# diagram verbatim rather than a simple chain — several stream pairs flow
# both ways in the source standard itself. That is reference-model content
# this repo does not hand-edit; see third_party/it4it/relationships.yaml's
# "Stream-to-stream network" comment and ADR-0029 ("no touchpoint-filtering
# — build.py imports the whole vendored file").
IT4IT_FLOW_EXCEPTION_REASON = (
    "vendored verbatim from the IT4IT standard's own dense, multi-directional "
    "value-stream Flow diagram (ADR-0029, third_party/it4it); not a local "
    "modelling duplication to prune."
)


def _accepted_reason(finding: dict) -> str | None:
    """Return the one-line reason a finding is an accepted exception, else None."""
    if (
        finding["type"] == "Flow"
        and finding["source"].startswith("IT4IT: ")
        and finding["target"].startswith("IT4IT: ")
    ):
        return IT4IT_FLOW_EXCEPTION_REASON
    return SERVING_EXCEPTIONS.get((finding["type"], finding["source"], finding["target"]))


def check(path: str, include_dependency: bool = True) -> dict:
    model = Model("check_derived")
    model.read(path)

    findings = []
    for duplicate in find_duplicate_relationships(model, include_dependency=include_dependency):
        rel = duplicate.relationship
        for chain in duplicate.implying_chains:
            via = chain.intermediate
            finding = {
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
            finding["accepted_reason"] = _accepted_reason(finding)
            findings.append(finding)

    unexplained = [f for f in findings if not f["accepted_reason"]]

    return {
        "path": path,
        "checked_relationships": len(model.rels_dict),
        "extended_scope": include_dependency,
        "findings": findings,
        "unexplained_count": len(unexplained),
        "clean": not unexplained,
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
        if not result["findings"]:
            print("no likely-derived relationships found")
        else:
            accepted = [f for f in result["findings"] if f["accepted_reason"]]
            unexplained = [f for f in result["findings"] if not f["accepted_reason"]]
            print(
                f"{len(result['findings'])} possible derived relationship(s) found "
                f"({len(accepted)} accepted exception(s), {len(unexplained)} unexplained):"
            )
            for f in unexplained:
                print(f"  [{f['type']}] {f['detail']}")
            for f in accepted:
                print(f"  [{f['type']}] [accepted] {f['detail']} — {f['accepted_reason']}")

    return 0  # advisory only — never fails the build


if __name__ == "__main__":
    raise SystemExit(main())
