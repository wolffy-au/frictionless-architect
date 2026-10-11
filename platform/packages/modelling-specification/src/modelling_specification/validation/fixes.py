"""Deterministic `proposed_fix` generation (R14, FR-004) -- never a second LLM call.

A metamodel relationship-matrix violation's fix is the nearest legal relationship
type for the same (source, target) type pair, read from pyArchimate's own matrix. A
convention violation's fix is the value implied by the violated rule's own `params`.
"""

from __future__ import annotations

from typing import Any

from pyArchimate import check_valid_relationship

# The 11 ArchiMate 3.2 relationship types (pyArchimate.relationship.ARCHI_CATEGORY) --
# fixed by the standard, not something conventions.yaml can add to or remove from.
_RELATIONSHIP_TYPES = [
    "Composition",
    "Aggregation",
    "Assignment",
    "Realization",
    "Serving",
    "Access",
    "Influence",
    "Triggering",
    "Flow",
    "Specialization",
    "Association",
]


def _nearest_legal_relationship_types(source_type: str, target_type: str) -> list[str]:
    return [t for t in _RELATIONSHIP_TYPES if check_valid_relationship(t, source_type, target_type)]


def _metamodel_fix(finding: dict[str, Any]) -> str:
    source_type, target_type, rel_type = finding["source_type"], finding["target_type"], finding["rel_type"]
    legal = _nearest_legal_relationship_types(source_type, target_type)
    if legal:
        return f"{rel_type} is not legal from {source_type} to {target_type}; use one of: {', '.join(legal)}"
    return f"no ArchiMate 3.2 relationship type is legal from {source_type} to {target_type}"


def _convention_fix(rule: dict[str, Any]) -> str | None:
    kind = rule["kind"]
    params = rule.get("params", {})
    if kind == "naming":
        return f"name must match the required pattern {params['pattern']!r} ({rule['id']})"
    if kind == "altitude":
        return f"remove the banned term(s) {params['banned_terms']!r} from the name/description ({rule['id']})"
    if kind == "allowed-subset":
        return f"type must be one of {params['allowed_types']!r} ({rule['id']})"
    if kind == "interposed-pattern":
        return f"use the intermediary type(s) {params['intermediary_types']!r} instead of a direct relationship ({rule['id']})"
    return None


def proposed_fix_for_finding(
    finding: dict[str, Any], rules_by_id: dict[str, dict[str, Any]] | None = None
) -> str | None:
    """`None` when the finding's `check` is neither `illegal_relationship` nor a
    known convention rule id (e.g. a `build_error` -- there is nothing rule-based to
    suggest for a malformed delta)."""
    if finding.get("check") == "illegal_relationship":
        return _metamodel_fix(finding)
    rule = (rules_by_id or {}).get(finding.get("check", ""))
    if rule is not None:
        return _convention_fix(rule)
    return None
