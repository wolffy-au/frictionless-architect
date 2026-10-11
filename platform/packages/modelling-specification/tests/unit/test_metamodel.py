"""Unit tests for `validation/metamodel.py` (FR-002): whole-resulting-model validation,
never the delta in isolation (R9)."""

from __future__ import annotations

from modelling_specification.validation.metamodel import validate_metamodel


def test_validate_metamodel_accepts_a_clean_delta_against_the_real_model() -> None:
    result = validate_metamodel(
        [{"id": "fn-test-delta", "type": "application-function", "name": "Test Delta Fn"}],
        [{"type": "assignment", "source": "sub-modelling", "target": "fn-test-delta"}],
    )

    assert result == {"clean": True, "findings": []}


def test_validate_metamodel_flags_an_illegal_relationship_against_a_real_existing_element() -> None:
    result = validate_metamodel(
        [{"id": "fn-test-delta", "type": "application-function", "name": "Test Delta Fn"}],
        [{"type": "composition", "source": "sub-modelling", "target": "fn-test-delta"}],
    )

    assert result["clean"] is False
    assert any(f["check"] == "illegal_relationship" for f in result["findings"])


def test_validate_metamodel_flags_a_build_error_as_a_finding() -> None:
    result = validate_metamodel([{"id": "x", "type": "not-a-real-type", "name": "X"}], [])

    assert result["clean"] is False
    assert any(f["check"] == "build_error" and "not-a-real-type" in f["detail"] for f in result["findings"])
