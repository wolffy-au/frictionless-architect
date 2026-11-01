"""`anonymize()`'s empty-results early return (detectors.py)."""

from __future__ import annotations

from pii_gateway.detectors import anonymize


def test_anonymize_with_no_results_returns_text_unchanged() -> None:
    text = "Ordinary prose with no detected spans."

    assert anonymize(text, []) == text
