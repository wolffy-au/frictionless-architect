"""Validate a Candidate Delta against the ArchiMate metamodel: relationship-matrix
legality and referential integrity, checked against the whole resulting model with
the delta merged in (FR-002, R9) -- never the delta in isolation, so a change that is
valid on its own but breaks referential integrity elsewhere in the model is caught.
"""

from __future__ import annotations

from typing import Any

from modelling_specification import model_io


def validate_metamodel(elements: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> dict[str, Any]:
    """Return `{"clean": bool, "findings": [...]}` in the same finding shape
    `model_io.validate_model` uses. A delta that fails to even assemble (e.g. an
    unknown ArchiMate type, a reference to a nonexistent id) surfaces as a
    `build_error` finding rather than raising -- FR-004 needs every rejection to
    carry a specific, actionable explanation, not an exception."""
    model, build_errors, _warnings = model_io.merge_candidate(elements, relationships)
    if model is None:
        findings = [{"check": "build_error", "id": None, "detail": e} for e in build_errors]
        return {"clean": False, "findings": findings}
    result = model_io.validate_model(model)
    return {"clean": result["clean"], "findings": result["findings"]}
