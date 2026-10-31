"""Entity models for the scrub contract (data-model.md's class diagram, Principle XI).

`ScrubAction`'s three values are `spec.md`'s "redacted-and-proceeded" /
"flagged-for-review" / "passed-through-unchanged" in snake_case -- same outcomes, no
fourth state anywhere.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

#: Synthetic category recorded for a detector-engine exception (research.md R6, fail-closed).
ENGINE_ERROR_CATEGORY = "_ENGINE_ERROR"


class ScrubAction(StrEnum):
    """The outcome of one `scrub()` call."""

    REDACTED_AND_PROCEEDED = "redacted_and_proceeded"
    FLAGGED_FOR_REVIEW = "flagged_for_review"
    PASSED_THROUGH_UNCHANGED = "passed_through_unchanged"


class Resolution(StrEnum):
    """How an architect resolves a flagged-for-review match (User Story 2 Scenario 2)."""

    REDACT = "redact"
    ALLOW = "allow"
    EDIT = "edit"


class Match(BaseModel):
    """One detected span, against one category.

    A span matching more than one category produces one `Match` per matching
    category, sharing the same `location`; redaction is still applied once per span
    (spec Edge Cases).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: str
    location: tuple[int, int]
    confidence: float


class PendingConfirmation(BaseModel):
    """A turn-scoped confirmation request -- never persisted or resumed across calls
    (2026-10-31 clarification, User Story 2 Scenario 3).

    There is no database row, cache entry, or queue item for this state: it exists
    only as the return value of one `scrub()` invocation and the caller's in-memory
    handling of it within that turn.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    matches: list[Match] = Field(min_length=1)
    original_text: str
    redacted_text: str
    # Not serializable by design -- a closure over the original text, nothing to
    # persist. Set after construction (see `set_resolver`); never part of __init__
    # validation, so it's exempt from the model's `extra="forbid"` field set.
    _resolver: Callable[[Resolution], str] = PrivateAttr()

    def set_resolver(self, resolver: Callable[[Resolution], str]) -> None:
        """Wire up the closure `resolve()` delegates to; called once, by `scrub()`."""
        self._resolver = resolver

    def resolve(self, resolution: Resolution) -> str:
        """Return the content to proceed with for the given resolution.

        Args:
            resolution: The architect's choice for the flagged match(es).

        Returns:
            `original_text` for `ALLOW`/`EDIT`, `redacted_text` for `REDACT`.
        """
        return self._resolver(resolution)


class AuditEntry(BaseModel):
    """Metadata-only record that a `scrub()` call happened (FR-011).

    Never contains the matched text or surrounding content. `categories` holds
    distinct `Match.category` values from the call only -- no locations, no
    confidence, no text.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    timestamp: datetime
    context: str
    categories: list[str]
    action: ScrubAction


class ScrubResult(BaseModel):
    """What one `scrub()` call hands back to its caller."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    text: str
    action: ScrubAction
    matches: list[Match] = Field(default_factory=list)
    pending_confirmation: PendingConfirmation | None = None


class DetectorCategoryConfiguration(BaseModel):
    """Operator-editable setting: which categories are checked and what happens on a
    match, per caller context (FR-009).

    An absent context falls back to the global default (spec Edge Cases). Changes
    apply to the next `scrub()` call with no restart (SC-003).
    """

    model_config = ConfigDict(extra="forbid")

    context: str
    active_categories: set[str]
    failure_mode: ScrubAction
