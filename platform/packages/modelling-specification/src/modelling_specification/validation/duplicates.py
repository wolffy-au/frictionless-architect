"""Flag a proposed element as a likely duplicate of an existing one (FR-005): at
least 2 of {name, type, description} similar. `type` counts as a match only on
exact equality; `name`/`description` via `rapidfuzz.fuzz.token_sort_ratio >= 80`
(R5). State (Current/Transition/Target) is never a differentiator (Edge Case 3) --
this module never looks at it at all.
"""

from __future__ import annotations

from typing import Any

from rapidfuzz import fuzz

from modelling_specification import model_io

_THRESHOLD = 80


def _existing_elements() -> list[dict[str, Any]]:
    errors: list[str] = []
    return model_io.load_all_elements(errors)


def _matched_fields(proposed: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    matched: list[str] = []
    if str(proposed.get("type", "")).lower() == str(candidate.get("type", "")).lower():
        matched.append("type")
    if fuzz.token_sort_ratio(str(proposed.get("name", "")), str(candidate.get("name", ""))) >= _THRESHOLD:
        matched.append("name")
    proposed_desc, candidate_desc = proposed.get("desc"), candidate.get("desc")
    if proposed_desc and candidate_desc and fuzz.token_sort_ratio(proposed_desc, candidate_desc) >= _THRESHOLD:
        matched.append("description")
    return matched


def find_duplicates(
    elements: list[dict[str, Any]], existing: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    """Return a Duplicate Candidate dict per `(proposed, existing)` pair matching on
    >=2 of name/type/description (FR-005, data-model.md). `existing` defaults to the
    real model on disk; tests inject it directly."""
    existing = existing if existing is not None else _existing_elements()
    duplicates: list[dict[str, Any]] = []
    for proposed in elements:
        for candidate in existing:
            if candidate.get("id") == proposed.get("id"):
                continue  # the same id is the same element, not a duplicate of itself
            matched = _matched_fields(proposed, candidate)
            if len(matched) >= 2:
                duplicates.append({"existing_element_id": candidate["id"], "matched_fields": matched, "decision": None})
    return duplicates
