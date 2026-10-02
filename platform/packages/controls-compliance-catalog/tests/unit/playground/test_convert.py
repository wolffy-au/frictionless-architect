"""Unit tests for the deterministic OSCAL -> Trestle Markdown conversion (GH #76)."""

import json

import pytest
from controls_compliance_catalog.playground.convert import (
    PlaygroundConversionError,
    convert_control_prose_to_markdown_candidate,
    convert_oscal_control_to_markdown,
)

SINGLE_CONTROL = {
    "id": "ac-2",
    "class": "SP800-53",
    "title": "Account Management",
    "parts": [
        {"id": "ac-2_smt", "name": "statement", "prose": "The organization manages information system accounts."}
    ],
}


def test_converts_a_single_pasted_control_to_markdown() -> None:
    markdown = convert_oscal_control_to_markdown(json.dumps(SINGLE_CONTROL))

    assert "Account Management" in markdown
    assert "The organization manages information system accounts." in markdown


def test_converts_a_full_pasted_catalog_to_markdown() -> None:
    catalog = {"uuid": "11111111-1111-4111-8111-111111111111", "controls": [SINGLE_CONTROL]}

    markdown = convert_oscal_control_to_markdown(json.dumps(catalog))

    assert "Account Management" in markdown


def test_rejects_malformed_json_with_a_clear_error() -> None:
    with pytest.raises(PlaygroundConversionError, match="valid JSON"):
        convert_oscal_control_to_markdown("{ not valid json")


def test_rejects_a_json_array_as_not_an_object() -> None:
    with pytest.raises(PlaygroundConversionError, match="valid JSON"):
        convert_oscal_control_to_markdown("[1, 2, 3]")


def test_rejects_a_control_missing_required_oscal_fields() -> None:
    with pytest.raises(PlaygroundConversionError, match="not a valid OSCAL control or catalog"):
        convert_oscal_control_to_markdown(json.dumps({"title": "Missing an id"}))


def test_converts_pasted_prose_to_a_candidate_markdown() -> None:
    markdown = convert_control_prose_to_markdown_candidate(
        "Account Management: the organization manages information system accounts."
    )

    assert "Account Management" in markdown


def test_rejects_empty_prose_with_a_clear_error() -> None:
    with pytest.raises(PlaygroundConversionError, match="Cannot convert empty prose"):
        convert_control_prose_to_markdown_candidate("   ")
