"""Unit tests for the stubbed LLM client seam (spec 001-oscal-ai-conversion R2)."""

import pytest
from controls_compliance_catalog.llm_client import LlmConversionError, convert_chunk


def test_convert_chunk_returns_a_labeled_stub_containing_the_prompt() -> None:
    result = convert_chunk("Account Management: the organization manages accounts.", system="convert to markdown")

    assert "STUB AI OUTPUT" in result
    assert "Account Management: the organization manages accounts." in result


def test_convert_chunk_shapes_id_title_statement_prose_like_trestle_markdown() -> None:
    result = convert_chunk(
        "AC-2 Account Management: The organization manages information system accounts.",
        system="convert to markdown",
    )

    assert "STUB AI OUTPUT" in result
    assert "# ac-2 - \\[\\] Account Management" in result
    assert "## Control Statement" in result
    assert "The organization manages information system accounts." in result


def test_convert_chunk_rejects_empty_prompt() -> None:
    with pytest.raises(LlmConversionError, match="Cannot convert empty prose"):
        convert_chunk("   ", system="convert to markdown")
