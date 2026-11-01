"""`PendingConfirmation.resolve()` for each `Resolution` value (User Story 2 Scenario 2)."""

from __future__ import annotations

import pytest
from pii_gateway.models import Match, PendingConfirmation, Resolution


def _pending() -> PendingConfirmation:
    pending = PendingConfirmation(
        matches=[Match(category="US_SSN", location=(10, 21), confidence=0.5)],
        original_text="My SSN is 234-56-7890.",
        redacted_text="My SSN is <US_SSN>.",
    )
    pending.set_resolver(
        lambda resolution: pending.redacted_text if resolution == Resolution.REDACT else pending.original_text
    )
    return pending


@pytest.mark.parametrize(
    ("resolution", "expected"),
    [
        (Resolution.REDACT, "My SSN is <US_SSN>."),
        (Resolution.ALLOW, "My SSN is 234-56-7890."),
        (Resolution.EDIT, "My SSN is 234-56-7890."),
    ],
)
def test_resolve_returns_content_to_proceed_with(resolution: Resolution, expected: str) -> None:
    assert _pending().resolve(resolution) == expected
