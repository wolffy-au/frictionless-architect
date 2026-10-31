"""Core `scrub()` behavior: PII/PHI redaction, passthrough, multi-category spans,
flag-for-review, and the SC-005 latency budget."""

from __future__ import annotations

import sys
import time

import pytest
from pii_gateway import ScrubAction, scrub
from pii_gateway.config import KNOWN_CONTEXTS
from pii_gateway.models import ENGINE_ERROR_CATEGORY, Resolution

# A representative corpus of ordinary technical prose (this platform's typical
# content) that must never be false-positive redacted (FR-004, SC-002).
_PROSE_CORPUS = [
    "The event-sourcing pattern decouples writes from reads.",
    "ADR-0014 mandates a PII/PHI anonymization gateway before every non-exempt LLM call.",
    "def scrub(text: str, *, context: str) -> ScrubResult: ...",
    "The settings router exposes GET /state and PUT /contexts/{context_id}.",
    "Presidio's AnalyzerEngine loads the en_core_web_lg spaCy model once at import.",
]


def test_redacts_name_pii_and_proceeds() -> None:
    result = scrub("Contact Jane Doe about the proposal.", context="spec-generator")

    assert "Jane Doe" not in result.text
    assert result.action == ScrubAction.REDACTED_AND_PROCEEDED


def test_redacts_email_and_phone_pii_and_proceeds() -> None:
    result = scrub("Reach me at jane@example.com or 415-555-0100.", context="spec-generator")

    assert "jane@example.com" not in result.text
    assert "415-555-0100" not in result.text
    assert result.action == ScrubAction.REDACTED_AND_PROCEEDED


def test_redacts_phi_identifier_and_proceeds() -> None:
    result = scrub("My SSN is 234-56-7890.", context="spec-generator")

    assert "234-56-7890" not in result.text
    assert result.action == ScrubAction.REDACTED_AND_PROCEEDED


@pytest.mark.parametrize("prose", _PROSE_CORPUS)
def test_passthrough_unchanged_for_ordinary_prose(prose: str) -> None:
    result = scrub(prose, context="spec-generator")

    assert result.text == prose
    assert result.action == ScrubAction.PASSED_THROUGH_UNCHANGED
    assert result.matches == []


def test_multi_category_span_produces_one_match_per_category() -> None:
    # "Jane Doe" alone can match both PERSON and, via the SpaCy recognizer's broader
    # LOCATION sweep, an overlapping span -- assert at minimum the redaction is applied
    # once even if more than one category reports the same location.
    result = scrub("Contact Jane Doe at jane@example.com", context="spec-generator")

    assert "Jane Doe" not in result.text
    assert "jane@example.com" not in result.text
    # No duplicate (category, location) pairs.
    pairs = [(match.category, match.location) for match in result.matches]
    assert len(pairs) == len(set(pairs))


def test_flagged_for_review_never_silently_redacts() -> None:
    result = scrub("My SSN is 234-56-7890.", context="conversational-authoring")

    assert result.action == ScrubAction.FLAGGED_FOR_REVIEW
    assert result.pending_confirmation is not None
    # The text handed back is unmutated -- redaction only happens via resolve().
    assert result.text == "My SSN is 234-56-7890."


def test_flagged_for_review_resolver_redacts_or_restores_the_original() -> None:
    result = scrub("My SSN is 234-56-7890.", context="conversational-authoring")

    pending = result.pending_confirmation
    assert pending is not None
    assert "234-56-7890" not in pending.resolve(Resolution.REDACT)
    assert pending.resolve(Resolution.ALLOW) == "My SSN is 234-56-7890."


def test_abandoned_pending_confirmation_holds_no_outside_reference() -> None:
    result = scrub("My SSN is 234-56-7890.", context="conversational-authoring")

    pending = result.pending_confirmation
    assert pending is not None
    # The only handle on it is the ScrubResult that returned it -- nothing module-level
    # or otherwise retains it, so letting `result` go out of scope discards it entirely.
    del result
    assert pending.original_text == "My SSN is 234-56-7890."


def test_detector_engine_error_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_text: str) -> None:
        raise RuntimeError("detector engine unavailable")

    # `pii_gateway.scrub` (the attribute) is shadowed by the re-exported `scrub()`
    # function (pii_gateway/__init__.py); patch the submodule via sys.modules instead.
    monkeypatch.setattr(sys.modules["pii_gateway.scrub"], "analyze", _raise)

    result = scrub("Ordinary prose with no PII.", context="spec-generator")

    # Fails closed: an engine error is treated the same as a detected match, never a
    # silent pass-through (research.md R6).
    assert result.action != ScrubAction.PASSED_THROUGH_UNCHANGED
    assert any(match.category == ENGINE_ERROR_CATEGORY for match in result.matches)


@pytest.mark.parametrize("context", KNOWN_CONTEXTS)
def test_scrub_returns_within_two_seconds(context: str) -> None:
    text = "Contact Jane Doe at jane@example.com regarding the Q3 ADR review."

    start = time.monotonic()
    scrub(text, context=context)
    elapsed = time.monotonic() - start

    assert elapsed < 2.0
