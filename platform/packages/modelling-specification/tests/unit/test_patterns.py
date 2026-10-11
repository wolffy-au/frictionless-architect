"""Unit tests for `validation/patterns.py` (FR-008, R6, data-model.md Invariant 4)."""

from __future__ import annotations

from modelling_specification.validation.patterns import find_pattern_suggestions, synthesize_intermediaries

_NEO4J_RULE = {
    "id": "conv-interposed-neo4j-volume",
    "kind": "interposed-pattern",
    "scope": ["*"],
    "params": {
        "source_type": "SystemSoftware",
        "relationship_type": "Assignment",
        "target_type": "DataObject",
        "intermediary_types": ["Artifact"],
        "target_relationship_type": "Realization",
    },
    "enabled": True,
}


def test_find_pattern_suggestions_flags_a_matching_direct_shape() -> None:
    relationships = [{"type": "Assignment", "source": "sw-x", "target": "do-y"}]
    types_by_id = {"sw-x": "SystemSoftware", "do-y": "DataObject"}

    result = find_pattern_suggestions(relationships, types_by_id, rules=[_NEO4J_RULE])

    assert result == [
        {
            "proposed_relationship": {"type": "Assignment", "source": "sw-x", "target": "do-y"},
            "established_pattern": {"intermediary_types": ["Artifact"], "target_relationship_type": "Realization"},
            "decision": None,
        }
    ]


def test_find_pattern_suggestions_no_match_raises_nothing() -> None:
    # Edge Case 4: no established pattern for this shape -> no suggestion, not an error.
    relationships = [{"type": "Serving", "source": "sw-x", "target": "do-y"}]
    types_by_id = {"sw-x": "SystemSoftware", "do-y": "DataObject"}

    assert find_pattern_suggestions(relationships, types_by_id, rules=[_NEO4J_RULE]) == []


def test_find_pattern_suggestions_ignores_a_disabled_rule() -> None:
    relationships = [{"type": "Assignment", "source": "sw-x", "target": "do-y"}]
    types_by_id = {"sw-x": "SystemSoftware", "do-y": "DataObject"}

    result = find_pattern_suggestions(relationships, types_by_id, rules=[{**_NEO4J_RULE, "enabled": False}])

    assert result == []


def test_find_pattern_suggestions_ignores_non_interposed_pattern_rules() -> None:
    naming_rule = {"id": "conv-x", "kind": "naming", "scope": ["*"], "params": {"pattern": ".*"}, "enabled": True}
    relationships = [{"type": "Assignment", "source": "sw-x", "target": "do-y"}]
    types_by_id = {"sw-x": "SystemSoftware", "do-y": "DataObject"}

    assert find_pattern_suggestions(relationships, types_by_id, rules=[naming_rule]) == []


def test_find_pattern_suggestions_requires_both_endpoint_types_known() -> None:
    relationships = [{"type": "Assignment", "source": "sw-x", "target": "unknown-id"}]
    types_by_id = {"sw-x": "SystemSoftware"}

    assert find_pattern_suggestions(relationships, types_by_id, rules=[_NEO4J_RULE]) == []


def test_synthesize_intermediaries_builds_the_two_leg_chain() -> None:
    # 2026-10-11 clarify: accept-pattern synthesizes the intermediary form itself
    # rather than discarding the candidate and asking the architect to re-describe it.
    suggestion = {
        "proposed_relationship": {"type": "Assignment", "source": "sw-x", "target": "do-y"},
        "established_pattern": {"intermediary_types": ["Artifact"], "target_relationship_type": "Realization"},
        "decision": None,
    }

    result = synthesize_intermediaries(suggestion, name_by_id={"sw-x": "X Software"}, existing_ids={"sw-x", "do-y"})

    assert result["elements"] == [
        {"type": "Artifact", "name": "X Software Artifact", "id": "artifact-x-software-artifact"}
    ]
    assert result["relationships"] == [
        {"type": "Assignment", "source": "sw-x", "target": "artifact-x-software-artifact"},
        {"type": "Realization", "source": "artifact-x-software-artifact", "target": "do-y"},
    ]


def test_synthesize_intermediaries_deduplicates_the_synthesized_id() -> None:
    suggestion = {
        "proposed_relationship": {"type": "Assignment", "source": "sw-x", "target": "do-y"},
        "established_pattern": {"intermediary_types": ["Artifact"], "target_relationship_type": "Realization"},
        "decision": None,
    }
    existing_ids = {"sw-x", "do-y", "artifact-x-software-artifact"}

    result = synthesize_intermediaries(suggestion, name_by_id={"sw-x": "X Software"}, existing_ids=existing_ids)

    assert result["elements"][0]["id"] == "artifact-x-software-artifact-2"
