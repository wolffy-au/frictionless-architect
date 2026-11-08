"""Validate a Candidate Delta against the ArchiMate metamodel: relationship-matrix
legality and referential integrity, checked against the whole resulting model with
the delta merged in (FR-002, R9) -- never the delta in isolation, so a change that is
valid on its own but breaks referential integrity elsewhere in the model is caught.
"""

from __future__ import annotations

from typing import Any

from modelling_specification import model_io


def validate_metamodel(
    elements: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    views: list[dict[str, Any]] | None = None,
    view_membership_edits: list[dict[str, Any]] | None = None,
    element_edits: list[dict[str, Any]] | None = None,
    element_removals: list[str] | None = None,
    relationship_removals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return `{"clean": bool, "findings": [...]}` in the same finding shape
    `model_io.validate_model` uses. A delta that fails to even assemble (e.g. an
    unknown ArchiMate type, a reference to a nonexistent id, or -- for a proposed
    view, or an existing view's membership after `view_membership_edits` is applied
    to it -- an unknown context/include_types type/member id, a colliding view id,
    an unknown view id, or a viewpoint conformance failure) surfaces as a
    `build_error` finding rather than raising -- FR-004 needs every rejection to
    carry a specific, actionable explanation, not an exception. `element_edits`/
    `element_removals`/`relationship_removals` (ADR-0037 item 8) are checked the
    same way: an unknown id/triple is a `build_error`; a removal leaving a dangling
    relationship endpoint elsewhere surfaces as the usual `broken_connection` finding
    once the resulting elements/relationships are assembled.
    """
    model, build_errors, _warnings = model_io.merge_candidate(
        elements, relationships, views, view_membership_edits, element_edits, element_removals, relationship_removals
    )
    if model is None:
        findings = [{"check": "build_error", "id": None, "detail": e} for e in build_errors]
        return {"clean": False, "findings": findings}
    result = model_io.validate_model(model)
    return {"clean": result["clean"], "findings": result["findings"]}
