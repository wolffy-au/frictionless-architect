"""The `scrub(text, *, context) -> ScrubResult` call contract (FR-001, contracts/scrub.md).

Every caller gets auto-redact-and-proceed on a detected match except the
`conversational-authoring` context, which gets flag-for-review (ADR-0014
amendment). A detector-engine error is treated the same as a detected match
(fails closed, research.md R6) -- never a silent pass-through of unscrubbed
content.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from presidio_analyzer import RecognizerResult

from pii_gateway.audit import AuditLogger
from pii_gateway.config import load_config, resolve_context
from pii_gateway.detectors import analyze, anonymize
from pii_gateway.models import (
    ENGINE_ERROR_CATEGORY,
    AuditEntry,
    Match,
    PendingConfirmation,
    Resolution,
    ScrubAction,
    ScrubResult,
)

logger = logging.getLogger(__name__)

_audit_logger = AuditLogger()


def _run_detectors(text: str) -> list[RecognizerResult]:
    try:
        return analyze(text)
    except Exception:  # noqa: BLE001 - Presidio/spaCy can raise a wide family of errors
        logger.warning("PII/PHI detector engine failed; treating as a match (fail closed)", exc_info=True)
        return [RecognizerResult(entity_type=ENGINE_ERROR_CATEGORY, start=0, end=0, score=0.0)]


def _to_matches(results: list[RecognizerResult]) -> list[Match]:
    return [Match(category=r.entity_type, location=(r.start, r.end), confidence=r.score) for r in results]


def _filter_to_active_categories(
    results: list[RecognizerResult], active_categories: set[str]
) -> list[RecognizerResult]:
    # The fail-closed synthetic engine-error match (research.md R6) is never a real
    # detector category, so it can't be toggled off by a category config (FR-009's
    # "which detector categories are active" is about real PII/PHI categories only).
    return [r for r in results if r.entity_type == ENGINE_ERROR_CATEGORY or r.entity_type in active_categories]


def _record_audit(context: str, categories: list[str], action: ScrubAction) -> None:
    _audit_logger.record(AuditEntry(timestamp=datetime.now(UTC), context=context, categories=categories, action=action))


def _redact(text: str, results: list[RecognizerResult]) -> str:
    # The synthetic engine-error match (research.md R6) is a zero-length span --
    # running it through anonymize() like a real match would redact nothing and
    # leave the original text intact. Fail-closed means no part of the text the
    # engine couldn't inspect survives, so replace all of it instead of the span.
    if any(result.entity_type == ENGINE_ERROR_CATEGORY for result in results):
        return f"<{ENGINE_ERROR_CATEGORY}>"
    return anonymize(text, results)


def _flag_for_review(text: str, redacted_text: str, matches: list[Match]) -> ScrubResult:
    def _resolver(resolution: Resolution, *, _original: str = text, _redacted: str = redacted_text) -> str:
        return _redacted if resolution == Resolution.REDACT else _original

    pending = PendingConfirmation(matches=matches, original_text=text, redacted_text=redacted_text)
    pending.set_resolver(_resolver)
    return ScrubResult(text=text, action=ScrubAction.FLAGGED_FOR_REVIEW, matches=matches, pending_confirmation=pending)


def scrub(text: str, *, context: str) -> ScrubResult:
    """Scrub `text` of PII/PHI before it reaches an LLM provider.

    Args:
        text: Architect-authored content about to be sent to an LLM provider.
        context: Caller identity (e.g. `"governance-eval"`, `"spec-generator"`,
            `"conversational-authoring"`); an unrecognized context falls back to
            the global default failure-mode (spec Edge Cases).

    Returns:
        A `ScrubResult` carrying the text to proceed with and what was done to get
        there.
    """
    config = resolve_context(context, load_config())
    results = _filter_to_active_categories(_run_detectors(text), config.active_categories)
    matches = _to_matches(results)

    if not matches:
        _record_audit(context, [], ScrubAction.PASSED_THROUGH_UNCHANGED)
        return ScrubResult(text=text, action=ScrubAction.PASSED_THROUGH_UNCHANGED, matches=[])

    categories = sorted({match.category for match in matches})
    redacted_text = _redact(text, results)

    if config.failure_mode == ScrubAction.FLAGGED_FOR_REVIEW:
        _record_audit(context, categories, ScrubAction.FLAGGED_FOR_REVIEW)
        return _flag_for_review(text, redacted_text, matches)

    _record_audit(context, categories, ScrubAction.REDACTED_AND_PROCEEDED)
    return ScrubResult(text=redacted_text, action=ScrubAction.REDACTED_AND_PROCEEDED, matches=matches)
