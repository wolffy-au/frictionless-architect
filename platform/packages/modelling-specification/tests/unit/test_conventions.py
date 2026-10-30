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

    matching = [f for f in findings if f["check"] == "conv-naming-no-self-type-capability"]
    assert [f["id"] for f in matching] == ["cap1"]


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


def test_check_relationships_flags_a_requirement_that_restates_its_outcome() -> None:
    rule = {
        "id": "conv-requirement-no-outcome-restatement",
        "kind": "no-restatement",
        "scope": ["Requirement"],
        "params": {
            "relationship_type": "Realization",
            "direction": "outgoing",
            "neighbour_type": "Outcome",
            "min_shared_words": 6,
        },
        "enabled": True,
    }
    elements = [
        {
            "id": "req1",
            "type": "Requirement",
            "name": "Req",
            "desc": "Every accepted ADR or spec clarification that changes architectural intent must be triaged.",
        },
        {
            "id": "outcome1",
            "type": "Outcome",
            "name": "Outcome",
            "desc": "Every accepted ADR or spec clarification that changes architectural intent lands in the model.",
        },
    ]
    relationships = [{"type": "Realization", "source": "req1", "target": "outcome1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"req1": "Requirement", "outcome1": "Outcome"}, rules=[rule]
    )

    assert len(findings) == 1
    assert "req1" in findings[0]
    assert "outcome1" in findings[0]


def test_check_relationships_accepts_a_requirement_distinct_from_its_outcome() -> None:
    rule = {
        "id": "conv-requirement-no-outcome-restatement",
        "kind": "no-restatement",
        "scope": ["Requirement"],
        "params": {
            "relationship_type": "Realization",
            "direction": "outgoing",
            "neighbour_type": "Outcome",
            "min_shared_words": 6,
        },
        "enabled": True,
    }
    elements = [
        {"id": "req1", "type": "Requirement", "name": "Req", "desc": "The system must continuously reconcile state."},
        {"id": "outcome1", "type": "Outcome", "name": "Outcome", "desc": "Drift is detected within 24 hours."},
    ]
    relationships = [{"type": "Realization", "source": "req1", "target": "outcome1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"req1": "Requirement", "outcome1": "Outcome"}, rules=[rule]
    )

    assert findings == []


def test_load_rules_rejects_required_neighbour_exclude_ids_not_a_list(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text(
        "- id: conv-bad-exclude-ids\n"
        "  kind: required-neighbour\n"
        "  scope: [Driver]\n"
        "  params: {relationship_type: Association, direction: outgoing, neighbour_type: Assessment, exclude_ids: nope}\n"
    )

    with pytest.raises(conventions.ConventionRuleError, match="exclude_ids must be a list"):
        conventions.load_rules(path)


def test_load_rules_rejects_no_bypass_missing_params(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text("- id: conv-bad-no-bypass\n  kind: no-bypass\n  scope: [Driver]\n  params: {source_type: Driver}\n")

    with pytest.raises(conventions.ConventionRuleError, match="no-bypass needs source_type"):
        conventions.load_rules(path)


def test_load_rules_rejects_no_bypass_params_that_are_not_strings(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text(
        "- id: conv-bad-no-bypass-types\n"
        "  kind: no-bypass\n"
        "  scope: [Driver]\n"
        "  params: {source_type: Driver, intermediary_type: [Assessment]}\n"
    )

    with pytest.raises(conventions.ConventionRuleError, match="must be strings"):
        conventions.load_rules(path)


def test_load_rules_rejects_no_restatement_min_shared_words_not_an_int(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text(
        "- id: conv-bad-min-shared-words\n"
        "  kind: no-restatement\n"
        "  scope: [Requirement]\n"
        "  params: {relationship_type: Realization, direction: outgoing, neighbour_type: Outcome, min_shared_words: six}\n"
    )

    with pytest.raises(conventions.ConventionRuleError, match="min_shared_words must be an int"):
        conventions.load_rules(path)


def test_load_rules_rejects_a_scoped_neighbour_rule_missing_scope_or_params(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text(
        "- id: conv-bad-scope\n"
        "  kind: required-neighbour\n"
        "  params: {relationship_type: Association, direction: outgoing, neighbour_type: Assessment}\n"
    )

    with pytest.raises(conventions.ConventionRuleError, match="needs a scope list and params mapping"):
        conventions.load_rules(path)


def test_load_rules_rejects_a_scoped_neighbour_rule_missing_a_required_param(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text(
        "- id: conv-missing-neighbour-type\n"
        "  kind: required-neighbour\n"
        "  scope: [Driver]\n"
        "  params: {relationship_type: Association, direction: outgoing}\n"
    )

    with pytest.raises(conventions.ConventionRuleError, match="missing params"):
        conventions.load_rules(path)


def test_load_rules_rejects_a_scoped_neighbour_rule_with_non_string_type_params(tmp_path: Path) -> None:
    path = tmp_path / "conventions.yaml"
    path.write_text(
        "- id: conv-bad-neighbour-type\n"
        "  kind: required-neighbour\n"
        "  scope: [Driver]\n"
        "  params: {relationship_type: Association, direction: outgoing, neighbour_type: [Assessment]}\n"
    )

    with pytest.raises(conventions.ConventionRuleError, match="must be strings"):
        conventions.load_rules(path)


def test_check_elements_skips_an_element_outside_the_rule_scope() -> None:
    findings = conventions.check_elements(
        [
            {"id": "cap1", "type": "Capability", "name": "Modelling Capability"},
            {"id": "do1", "type": "DataObject", "name": "Out of scope"},
        ],
        rules=[_NAMING_RULE],
    )

    assert [f["id"] for f in findings] == ["cap1"]


def test_check_relationships_skips_an_element_outside_the_rule_scope() -> None:
    rule = {
        "id": "conv-driver-assessment",
        "kind": "required-neighbour",
        "scope": ["Driver"],
        "params": {"relationship_type": "Association", "direction": "outgoing", "neighbour_type": "Assessment"},
        "enabled": True,
    }
    elements = [
        {"id": "driver1", "type": "Driver", "name": "Driver"},
        {"id": "goal1", "type": "Goal", "name": "Goal"},
    ]

    findings = conventions.check_relationships(elements, [], {"driver1": "Driver", "goal1": "Goal"}, rules=[rule])

    assert len(findings) == 1
    assert "'driver1'" in findings[0]


def test_check_relationships_honours_exclude_ids_on_a_required_neighbour_rule() -> None:
    rule = {
        "id": "conv-driver-assessment",
        "kind": "required-neighbour",
        "scope": ["Driver"],
        "params": {
            "relationship_type": "Association",
            "direction": "outgoing",
            "neighbour_type": "Assessment",
            "exclude_ids": ["driver1"],
        },
        "enabled": True,
    }
    elements = [{"id": "driver1", "type": "Driver", "name": "Driver"}]

    assert conventions.check_relationships(elements, [], {"driver1": "Driver"}, rules=[rule]) == []


def test_check_relationships_accepts_an_incoming_required_neighbour() -> None:
    rule = {
        "id": "conv-outcome-has-requirement",
        "kind": "required-neighbour",
        "scope": ["Outcome"],
        "params": {"relationship_type": "Realization", "direction": "incoming", "neighbour_type": "Requirement"},
        "enabled": True,
    }
    elements = [
        {"id": "outcome1", "type": "Outcome", "name": "Outcome"},
        {"id": "req1", "type": "Requirement", "name": "Req"},
    ]
    relationships = [{"type": "Realization", "source": "req1", "target": "outcome1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"outcome1": "Outcome", "req1": "Requirement"}, rules=[rule]
    )

    assert findings == []


def test_check_relationships_ignores_a_no_bypass_source_outside_its_type() -> None:
    rule = {
        "id": "conv-driver-routes-through-assessment",
        "kind": "no-bypass",
        "scope": ["Driver"],
        "params": {"source_type": "Driver", "intermediary_type": "Assessment"},
        "enabled": True,
    }
    elements = [
        {"id": "goal1", "type": "Goal", "name": "Goal"},
        {"id": "goal2", "type": "Goal", "name": "Other Goal"},
    ]
    relationships = [{"type": "Association", "source": "goal1", "target": "goal2"}]

    findings = conventions.check_relationships(
        elements, relationships, {"goal1": "Goal", "goal2": "Goal"}, rules=[rule]
    )

    assert findings == []


def test_check_relationships_excludes_first_party_only_ids_from_no_bypass() -> None:
    rule = {
        "id": "conv-it4it-routes-through-assessment",
        "kind": "no-bypass",
        "scope": ["Driver"],
        "params": {"source_type": "Driver", "intermediary_type": "Assessment", "first_party_only": True},
        "enabled": True,
    }
    elements = [
        {"id": "it4it-driver1", "type": "Driver", "name": "Driver"},
        {"id": "goal1", "type": "Goal", "name": "Goal"},
    ]
    relationships = [{"type": "Association", "source": "it4it-driver1", "target": "goal1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"it4it-driver1": "Driver", "goal1": "Goal"}, rules=[rule]
    )

    assert findings == []


def test_check_relationships_excludes_first_party_only_ids_from_no_restatement() -> None:
    rule = {
        "id": "conv-it4it-no-outcome-restatement",
        "kind": "no-restatement",
        "scope": ["Requirement"],
        "params": {
            "relationship_type": "Realization",
            "direction": "outgoing",
            "neighbour_type": "Outcome",
            "min_shared_words": 2,
            "first_party_only": True,
        },
        "enabled": True,
    }
    elements = [
        {"id": "it4it-req1", "type": "Requirement", "name": "Req", "desc": "Exactly the same words here"},
        {"id": "outcome1", "type": "Outcome", "name": "Outcome", "desc": "Exactly the same words here"},
    ]
    relationships = [{"type": "Realization", "source": "it4it-req1", "target": "outcome1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"it4it-req1": "Requirement", "outcome1": "Outcome"}, rules=[rule]
    )

    assert findings == []


def test_check_relationships_no_restatement_skips_an_element_with_no_desc() -> None:
    rule = {
        "id": "conv-requirement-no-outcome-restatement",
        "kind": "no-restatement",
        "scope": ["Requirement"],
        "params": {
            "relationship_type": "Realization",
            "direction": "outgoing",
            "neighbour_type": "Outcome",
            "min_shared_words": 2,
        },
        "enabled": True,
    }
    elements = [
        {"id": "req1", "type": "Requirement", "name": "Req"},
        {"id": "outcome1", "type": "Outcome", "name": "Outcome", "desc": "Something"},
    ]
    relationships = [{"type": "Realization", "source": "req1", "target": "outcome1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"req1": "Requirement", "outcome1": "Outcome"}, rules=[rule]
    )

    assert findings == []


def test_check_relationships_no_restatement_skips_a_relationship_of_a_different_type() -> None:
    rule = {
        "id": "conv-requirement-no-outcome-restatement",
        "kind": "no-restatement",
        "scope": ["Requirement"],
        "params": {
            "relationship_type": "Realization",
            "direction": "outgoing",
            "neighbour_type": "Outcome",
            "min_shared_words": 2,
        },
        "enabled": True,
    }
    elements = [
        {"id": "req1", "type": "Requirement", "name": "Req", "desc": "Exactly the same words here"},
        {"id": "outcome1", "type": "Outcome", "name": "Outcome", "desc": "Exactly the same words here"},
    ]
    relationships = [{"type": "Association", "source": "req1", "target": "outcome1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"req1": "Requirement", "outcome1": "Outcome"}, rules=[rule]
    )

    assert findings == []


def test_check_relationships_no_restatement_skips_a_relationship_with_no_matching_neighbour() -> None:
    rule = {
        "id": "conv-requirement-no-outcome-restatement",
        "kind": "no-restatement",
        "scope": ["Requirement"],
        "params": {
            "relationship_type": "Realization",
            "direction": "outgoing",
            "neighbour_type": "Outcome",
            "min_shared_words": 2,
        },
        "enabled": True,
    }
    elements = [
        {"id": "req1", "type": "Requirement", "name": "Req", "desc": "Exactly the same words here"},
        {"id": "cap1", "type": "Capability", "name": "Cap", "desc": "Exactly the same words here"},
    ]
    relationships = [{"type": "Realization", "source": "req1", "target": "cap1"}]

    findings = conventions.check_relationships(
        elements, relationships, {"req1": "Requirement", "cap1": "Capability"}, rules=[rule]
    )

    assert findings == []


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
