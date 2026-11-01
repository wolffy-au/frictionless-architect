"""`propose_delta()` never sends a planted PII string to the LLM provider (ADR-0014,
pii-gateway FR-007, SC-001) -- over a stubbed `litellm.completion` (plan.md Testing),
never a live network.

`conversational-authoring` is the one context seeded with `flag-for-review` rather
than every other consumer's `auto-redact-and-proceed` default (ADR-0014 amendment,
pii-gateway `config.CONVERSATIONAL_AUTHORING_CONTEXT`): a detected match must pause
`propose_delta()` -- via `PiiReviewRequired` -- rather than send either the original
*or* the auto-redacted text straight to the LLM. The architect's review happens at
the `router.py` boundary (`tests/api/test_propose_pii.py`); this module only proves
the `delta.py`/`pii_gateway.scrub()` seam itself."""

from __future__ import annotations

import pytest
from modelling_specification.authoring.delta import PiiReviewRequired, propose_delta, resume_proposal
from pii_gateway import Resolution
from support.fake_llm import FakeCompletion


def test_planted_pii_flags_for_review_instead_of_reaching_the_stubbed_llm_call(
    configured_fake_llm: FakeCompletion,
) -> None:
    with pytest.raises(PiiReviewRequired) as excinfo:
        propose_delta("Add an application function for Jane Doe (jane@example.com) to review.")

    assert configured_fake_llm.calls == []
    assert {m.category for m in excinfo.value.matches}


def test_ordinary_request_with_no_pii_passes_through_unchanged(configured_fake_llm: FakeCompletion) -> None:
    propose_delta("add an application function fn-example under sub-modelling")

    sent = configured_fake_llm.calls[0]
    assert sent["messages"][-1]["content"] == "add an application function fn-example under sub-modelling"


def test_resolving_allow_sends_the_original_unredacted_text(configured_fake_llm: FakeCompletion) -> None:
    with pytest.raises(PiiReviewRequired) as excinfo:
        propose_delta("Add an application function for Jane Doe (jane@example.com) to review.")
    pending = excinfo.value.pending_confirmation

    resume_proposal(pending.resolve(Resolution.ALLOW))

    sent = configured_fake_llm.calls[0]
    assert "Jane Doe" in sent["messages"][-1]["content"]


def test_resolving_redact_sends_the_redacted_text_not_the_original(configured_fake_llm: FakeCompletion) -> None:
    with pytest.raises(PiiReviewRequired) as excinfo:
        propose_delta("Add an application function for Jane Doe (jane@example.com) to review.")
    pending = excinfo.value.pending_confirmation

    resume_proposal(pending.resolve(Resolution.REDACT))

    sent = configured_fake_llm.calls[0]
    sent_content = sent["messages"][-1]["content"]
    assert "jane@example.com" not in sent_content
