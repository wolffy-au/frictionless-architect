"""`propose_delta()` never sends a planted PII string to the LLM provider (ADR-0014,
pii-gateway FR-007, SC-001) -- over a stubbed `litellm.completion` (plan.md Testing),
never a live network."""

from __future__ import annotations

from modelling_specification.authoring.delta import propose_delta
from support.fake_llm import FakeCompletion


def test_planted_pii_never_reaches_the_stubbed_llm_call(configured_fake_llm: FakeCompletion) -> None:
    propose_delta("Add an application function for Jane Doe (jane@example.com) to review.")

    sent = configured_fake_llm.calls[0]
    sent_content = sent["messages"][-1]["content"]
    assert "Jane Doe" not in sent_content
    assert "jane@example.com" not in sent_content


def test_ordinary_request_with_no_pii_passes_through_unchanged(configured_fake_llm: FakeCompletion) -> None:
    propose_delta("add an application function fn-example under sub-modelling")

    sent = configured_fake_llm.calls[0]
    assert sent["messages"][-1]["content"] == "add an application function fn-example under sub-modelling"
