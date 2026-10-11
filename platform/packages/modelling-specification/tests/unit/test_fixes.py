"""Unit tests for `validation/fixes.py` (R14, FR-004) -- deterministic `proposed_fix`
generation, never a second LLM call.
"""

from __future__ import annotations

from typing import Any

from modelling_specification.validation.fixes import proposed_fix_for_finding


def test_metamodel_finding_fix_names_the_nearest_legal_relationship_types() -> None:
    finding = {
        "check": "illegal_relationship",
        "id": "rel-1",
        "detail": "Composition: BusinessActor -> Goal is not permitted by the ArchiMate 3.2 matrix",
        "rel_type": "Composition",
        "source_type": "BusinessActor",
        "target_type": "Goal",
    }

    fix = proposed_fix_for_finding(finding)

    assert fix is not None
    assert "BusinessActor" in fix and "Goal" in fix
    assert "Composition" in fix


def test_metamodel_finding_fix_handles_no_legal_type_at_all() -> None:
    finding = {
        "check": "illegal_relationship",
        "id": "rel-1",
        "detail": "x",
        "rel_type": "Composition",
        "source_type": "Junction",
        "target_type": "Junction",
    }

    fix = proposed_fix_for_finding(finding)

    assert fix is not None


def test_naming_convention_finding_fix_names_the_required_pattern() -> None:
    rule: dict[str, Any] = {
        "id": "conv-naming-no-self-type-capability",
        "kind": "naming",
        "params": {"pattern": r"(?i)^(?!.*\bcapability\b).+$"},
    }
    finding = {"check": rule["id"], "id": "cap1", "detail": "name ... does not match ..."}

    fix = proposed_fix_for_finding(finding, rules_by_id={rule["id"]: rule})

    assert fix is not None
    assert repr(rule["params"]["pattern"]) in fix


def test_altitude_convention_finding_fix_names_the_banned_terms() -> None:
    rule: dict[str, Any] = {
        "id": "conv-altitude-motivation-no-tooling",
        "kind": "altitude",
        "params": {"banned_terms": ["YAML", "render step"]},
    }
    finding = {"check": rule["id"], "id": "goal1", "detail": "..."}

    fix = proposed_fix_for_finding(finding, rules_by_id={rule["id"]: rule})

    assert fix is not None
    assert "YAML" in fix and "render step" in fix


def test_allowed_subset_convention_finding_fix_names_the_allowed_types() -> None:
    rule: dict[str, Any] = {
        "id": "conv-allowed-subset-example",
        "kind": "allowed-subset",
        "params": {"allowed_types": ["ApplicationFunction", "ApplicationComponent"]},
    }
    finding = {"check": rule["id"], "id": "x1", "detail": "..."}

    fix = proposed_fix_for_finding(finding, rules_by_id={rule["id"]: rule})

    assert fix is not None
    assert "ApplicationFunction" in fix and "ApplicationComponent" in fix


def test_interposed_pattern_convention_finding_fix_names_the_intermediary_types() -> None:
    rule: dict[str, Any] = {
        "id": "conv-interposed-neo4j-volume",
        "kind": "interposed-pattern",
        "params": {
            "source_type": "SystemSoftware",
            "relationship_type": "Assignment",
            "target_type": "DataObject",
            "intermediary_types": ["Artifact"],
        },
    }
    finding = {"check": rule["id"], "id": "rel-1", "detail": "..."}

    fix = proposed_fix_for_finding(finding, rules_by_id={rule["id"]: rule})

    assert fix is not None
    assert "Artifact" in fix


def test_unknown_finding_check_returns_none() -> None:
    assert proposed_fix_for_finding({"check": "build_error", "id": None, "detail": "x"}) is None
