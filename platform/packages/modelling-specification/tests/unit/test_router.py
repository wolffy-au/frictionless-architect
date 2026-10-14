"""Unit tests for router.py's pure helpers that are awkward to exercise fully through
the HTTP contract tests under `tests/api/` -- see those for the endpoint-level
behaviour (session lifecycle, decide actions, render/preview). This file targets the
private helpers directly."""

from __future__ import annotations

from modelling_specification import router
from modelling_specification.authoring.state import CandidateDelta


def test_merge_into_existing_rewires_only_the_endpoint_that_was_dropped() -> None:
    # One relationship whose source was dropped (needs rewiring, target untouched),
    # and one whose target was dropped (source untouched) -- exercises both the
    # "source not in dropped_ids" skip and the "target in dropped_ids" rewrite.
    delta = CandidateDelta(
        delta_id="d1",
        session_id="s1",
        elements=[{"id": "new-el", "type": "ApplicationComponent", "name": "New"}],
        relationships=[
            {"type": "Serving", "source": "existing-untouched", "target": "new-el"},
            {"type": "Serving", "source": "new-el", "target": "existing-untouched"},
        ],
    )

    router._merge_into_existing(delta, "existing-target")

    assert delta.elements == []
    assert delta.relationships == [
        {"type": "Serving", "source": "existing-untouched", "target": "existing-target"},
        {"type": "Serving", "source": "existing-target", "target": "existing-untouched"},
    ]


def test_describe_objection_falls_back_to_unknown_with_no_recorded_objection() -> None:
    # `decide()`'s `override` action only reaches `_describe_objection` once
    # `_check_overridable` has confirmed the delta is FLAGGED, which `_validate_and_flag`
    # only sets when validation_result is unclean, or there are duplicates, or pattern
    # suggestions -- so this fallback is a defensive invariant, not a reachable router
    # state; exercised directly against a delta with none of those three recorded.
    delta = CandidateDelta(
        delta_id="d1",
        session_id="s1",
        validation_result={"clean": True, "findings": []},
        duplicates=[],
        pattern_suggestions=[],
    )

    assert router._describe_objection(delta) == ("unknown", "no recorded objection")
