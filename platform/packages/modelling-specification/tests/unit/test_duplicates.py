"""Unit tests for `validation/duplicates.py` (FR-005, R5, data-model.md Invariant 3)."""

from __future__ import annotations

from modelling_specification.validation.duplicates import find_duplicates


def test_find_duplicates_requires_at_least_two_matched_fields() -> None:
    existing = [{"id": "e1", "type": "ApplicationFunction", "name": "Completely Different Name"}]
    proposed = [{"type": "ApplicationFunction", "name": "Totally Unrelated Thing"}]

    assert find_duplicates(proposed, existing) == []


def test_find_duplicates_flags_type_and_name_match() -> None:
    existing = [{"id": "e1", "type": "ApplicationFunction", "name": "Process Invoice"}]
    proposed = [{"type": "ApplicationFunction", "name": "Process Invoices"}]

    assert find_duplicates(proposed, existing) == [
        {"existing_element_id": "e1", "matched_fields": ["type", "name"], "decision": None}
    ]


def test_find_duplicates_type_match_requires_exact_equality() -> None:
    # Only 'name' matches -- type differs, so only 1 matched field -> no duplicate.
    existing = [{"id": "e1", "type": "ApplicationComponent", "name": "Process Invoice"}]
    proposed = [{"type": "ApplicationFunction", "name": "Process Invoice"}]

    assert find_duplicates(proposed, existing) == []


def test_find_duplicates_ignores_empty_description_on_both_sides() -> None:
    # Neither side has a `desc` -- two empty strings must not count as a "description" match.
    existing = [{"id": "e1", "type": "ApplicationFunction", "name": "Process Invoice"}]
    proposed = [{"type": "ApplicationFunction", "name": "Process Invoices"}]

    result = find_duplicates(proposed, existing)

    assert result[0]["matched_fields"] == ["type", "name"]


def test_find_duplicates_flags_description_similarity() -> None:
    existing = [
        {
            "id": "e1",
            "type": "ApplicationFunction",
            "name": "Alpha",
            "desc": "Processes customer invoices every month",
        }
    ]
    proposed = [{"type": "ApplicationFunction", "name": "Beta", "desc": "Processes customer invoices every month"}]

    result = find_duplicates(proposed, existing)

    assert result[0]["matched_fields"] == ["type", "description"]


def test_find_duplicates_skips_the_same_id() -> None:
    existing = [{"id": "e1", "type": "ApplicationFunction", "name": "Process Invoice"}]
    proposed = [{"id": "e1", "type": "ApplicationFunction", "name": "Process Invoice"}]

    assert find_duplicates(proposed, existing) == []


def test_find_duplicates_is_irrelevant_to_state_classification() -> None:
    # State (Current/Transition/Target) is never a differentiator (Edge Case 3) --
    # find_duplicates doesn't even look at it, so a `props` state hint on either
    # side changes nothing about whether it flags.
    existing = [{"id": "e1", "type": "ApplicationFunction", "name": "Process Invoice", "props": {"state": "Current"}}]
    proposed = [{"type": "ApplicationFunction", "name": "Process Invoices", "props": {"state": "Target"}}]

    result = find_duplicates(proposed, existing)

    assert result[0]["existing_element_id"] == "e1"
