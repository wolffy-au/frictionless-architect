"""Unit tests for `validation/conventions.py` -- the generic `naming`/`altitude`/
`allowed-subset` kinds (FR-003, R13). `interposed-pattern` is `patterns.py`'s own
concern (test_patterns.py), not checked here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from modelling_specification.validation import conventions


def test_load_rules_round_trips_the_real_conventions_yaml() -> None:
    rules = conventions.load_rules()
    assert any(r["kind"] == "interposed-pattern" for r in rules)


def test_load_rules_rejects_a_malformed_entry_naming_its_id(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text("- {id: conv-bad, kind: not-a-real-kind}\n")

    with pytest.raises(conventions.ConventionRuleError, match="conv-bad"):
        conventions.load_rules(path)


def test_load_rules_rejects_an_entry_missing_id_or_kind(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text("- {kind: naming, params: {pattern: '.*'}}\n")

    with pytest.raises(conventions.ConventionRuleError, match="missing"):
        conventions.load_rules(path)


def test_load_rules_returns_empty_when_the_file_is_absent(tmp_path: Path) -> None:
    assert conventions.load_rules(tmp_path / "absent.yaml") == []


def test_load_rules_rejects_a_file_that_is_not_a_yaml_list(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text("id: conv-bad\nkind: naming\n")  # a mapping, not a list of rules

    with pytest.raises(conventions.ConventionRuleError, match="must be a YAML list"):
        conventions.load_rules(path)


def test_load_rules_rejects_an_invalid_required_neighbour_direction(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text(
        "- id: conv-bad-direction\n"
        "  kind: required-neighbour\n"
        "  scope: [Driver]\n"
        "  params: {relationship_type: Association, direction: sideways, neighbour_type: Assessment}\n"
    )

    with pytest.raises(conventions.ConventionRuleError, match="conv-bad-direction"):
        conventions.load_rules(path)


def test_violation_returns_none_for_a_kind_it_does_not_evaluate() -> None:
    # `check_elements` never calls `_violation` for an `interposed-pattern` rule (it
    # skips those itself, per test_check_elements_skips_interposed_pattern_rules) --
    # this drives `_violation` directly to cover its own fallback for an
    # unrecognised/unevaluated kind.
    rule = {"id": "conv-interposed-example", "kind": "interposed-pattern", "scope": ["*"], "params": {}}

    assert conventions._violation(rule, {"id": "x1", "type": "DataObject", "name": "X"}) is None


_NAMING_RULE = {
    "id": "conv-naming-no-self-type-capability",
    "kind": "naming",
    "scope": ["Capability"],
    "params": {"pattern": r"(?i)^(?!.*\bcapability\b).+$"},
    "enabled": True,
}


def test_check_elements_naming_rejects_a_non_matching_name() -> None:
    findings = conventions.check_elements(
        [{"id": "cap1", "type": "Capability", "name": "Modelling Capability"}], rules=[_NAMING_RULE]
    )

    assert any(f["check"] == "conv-naming-no-self-type-capability" and f["id"] == "cap1" for f in findings)


def test_check_elements_naming_accepts_a_matching_name() -> None:
    findings = conventions.check_elements(
        [{"id": "cap1", "type": "Capability", "name": "Modelling"}], rules=[_NAMING_RULE]
    )

    assert findings == []


_ALTITUDE_RULE = {
    "id": "conv-altitude-motivation-no-tooling",
    "kind": "altitude",
    "scope": ["Goal", "Outcome"],
    "params": {"banned_terms": ["YAML", "render step"]},
    "enabled": True,
}


def test_check_elements_altitude_rejects_a_banned_term_hit() -> None:
    findings = conventions.check_elements(
        [{"id": "goal1", "type": "Goal", "name": "Ship without a manual render step"}], rules=[_ALTITUDE_RULE]
    )

    assert any(f["check"] == "conv-altitude-motivation-no-tooling" for f in findings)


def test_check_elements_altitude_accepts_clean_prose() -> None:
    findings = conventions.check_elements(
        [{"id": "goal1", "type": "Goal", "name": "Architects trust the platform"}], rules=[_ALTITUDE_RULE]
    )

    assert findings == []


_ALLOWED_SUBSET_RULE = {
    "id": "conv-allowed-subset-example",
    "kind": "allowed-subset",
    "scope": ["ApplicationFunction"],
    "params": {"allowed_types": ["ApplicationFunction", "ApplicationComponent"]},
    "enabled": True,
}


def test_check_elements_allowed_subset_rejects_a_type_outside_the_subset() -> None:
    findings = conventions.check_elements(
        [{"id": "x1", "type": "DataObject", "name": "X"}],
        rules=[{**_ALLOWED_SUBSET_RULE, "scope": ["*"]}],
    )

    assert any(f["check"] == "conv-allowed-subset-example" for f in findings)


def test_check_elements_allowed_subset_accepts_a_type_inside_the_subset() -> None:
    findings = conventions.check_elements(
        [{"id": "x1", "type": "ApplicationFunction", "name": "X"}], rules=[_ALLOWED_SUBSET_RULE]
    )

    assert findings == []


def test_check_elements_a_disabled_rule_never_fires() -> None:
    disabled = {**_NAMING_RULE, "enabled": False}

    findings = conventions.check_elements(
        [{"id": "cap1", "type": "Capability", "name": "Modelling Capability"}], rules=[disabled]
    )

    assert findings == []


def test_check_elements_skips_interposed_pattern_rules() -> None:
    rule = {
        "id": "conv-interposed-neo4j-volume",
        "kind": "interposed-pattern",
        "scope": ["*"],
        "params": {
            "source_type": "SystemSoftware",
            "relationship_type": "Assignment",
            "target_type": "DataObject",
            "intermediary_types": ["Artifact"],
        },
        "enabled": True,
    }

    findings = conventions.check_elements([{"id": "x1", "type": "DataObject", "name": "X"}], rules=[rule])

    assert findings == []


def test_check_relationships_enforces_a_configured_neighbour_rule() -> None:
    rule = {
        "id": "conv-driver-assessment",
        "kind": "required-neighbour",
        "scope": ["Driver"],
        "params": {
            "relationship_type": "Association",
            "direction": "outgoing",
            "neighbour_type": "Assessment",
        },
        "enabled": True,
    }
    elements = [{"id": "driver1", "type": "Driver", "name": "Driver"}]

    findings = conventions.check_relationships(elements, [], {"driver1": "Driver"}, rules=[rule])

    assert len(findings) == 1
    assert "conv-driver-assessment" in findings[0]
    assert "'driver1'" in findings[0]


def test_check_relationships_can_disable_a_neighbour_rule() -> None:
    rule = {
        "id": "conv-driver-assessment",
        "kind": "required-neighbour",
        "scope": ["Driver"],
        "params": {
            "relationship_type": "Association",
            "direction": "outgoing",
            "neighbour_type": "Assessment",
        },
        "enabled": False,
    }
    elements = [{"id": "driver1", "type": "Driver", "name": "Driver"}]

    assert conventions.check_relationships(elements, [], {"driver1": "Driver"}, rules=[rule]) == []


def test_check_relationships_flags_a_direct_edge_that_bypasses_an_intermediary() -> None:
    rule = {
        "id": "conv-driver-routes-through-assessment",
        "kind": "no-bypass",
        "scope": ["Driver"],
        "params": {"source_type": "Driver", "intermediary_type": "Assessment"},
        "enabled": True,
    }
    elements = [
        {"id": "driver1", "type": "Driver", "name": "Driver"},
        {"id": "goal1", "type": "Goal", "name": "Goal"},
    ]
    relationships = [{"type": "Association", "source": "driver1", "target": "goal1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"driver1": "Driver", "goal1": "Goal"}, rules=[rule]
    )

    assert len(findings) == 1
    assert "bypassing Assessment" in findings[0]
