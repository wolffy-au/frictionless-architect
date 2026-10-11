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
