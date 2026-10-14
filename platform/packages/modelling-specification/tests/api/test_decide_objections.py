"""Contract tests for `decide` actions beyond a clean `apply` (US2, contracts/api.md):
`reject`, duplicate `merge`/`keep-both`, pattern `accept-pattern`/`keep-direct`, and
`override`. Runs against `isolated_model` (tests/api/conftest.py).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from modelling_specification.app import app
from support.fake_llm import FakeCompletion

client = TestClient(app)

# A synthetic interposed-pattern rule over a shape that IS legal directly (Serving
# ApplicationComponent -> BusinessRole) -- FR-008's scenario is specifically a *legal*
# direct relationship the model's convention discourages, unlike the real
# conv-interposed-neo4j-volume precedent, whose direct form (Assignment
# SystemSoftware -> DataObject) happens to be outright illegal per the ArchiMate
# matrix and so belongs to the metamodel-rejection path (FR-004), not this one.
_SYNTHETIC_PATTERN_RULE: dict[str, Any] = {
    "id": "conv-interposed-synthetic-test",
    "kind": "interposed-pattern",
    "scope": ["*"],
    "params": {
        "source_type": "ApplicationComponent",
        "relationship_type": "Serving",
        "target_type": "BusinessRole",
        "intermediary_types": ["ApplicationService"],
        "target_relationship_type": "Triggering",
    },
    "enabled": True,
}


def _propose(request: str) -> tuple[str, dict[str, Any]]:
    session_id: str = client.post("/authoring/sessions").json()["session_id"]
    response = client.post(f"/authoring/sessions/{session_id}/propose", json={"request": request})
    return session_id, response.json()


def _decide(session_id: str, delta_id: str, **body: object) -> Any:
    return client.post(f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide", json=body)


def test_reject_discards_the_delta_and_writes_nothing(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-flagged-reject-test", "name": "Flagged"}],'
        ' "relationships": [{"type": "Composition", "source": "sub-modelling", "target": "fn-flagged-reject-test"}]}'
    )
    session_id, body = _propose("propose a bad shape")
    assert body["status"] == "flagged"

    response = _decide(session_id, body["delta_id"], action="reject")

    assert response.status_code == 200
    assert response.json() == {"delta_id": body["delta_id"], "status": "discarded"}
    assert "fn-flagged-reject-test" not in (isolated_model / "elements.yaml").read_text()


def test_reject_then_decide_again_is_409_and_a_fresh_propose_starts_a_new_delta(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    # FR-017: the agent never auto-retries a different fix after a second rejection --
    # by construction, a discarded delta is terminal and the architect's next
    # `propose` simply starts a fresh delta rather than resuming anything.
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-flagged-restate-test", "name": "Flagged"}],'
        ' "relationships": [{"type": "Composition", "source": "sub-modelling", "target": "fn-flagged-restate-test"}]}'
    )
    session_id, body = _propose("propose a bad shape")
    _decide(session_id, body["delta_id"], action="reject")

    again = _decide(session_id, body["delta_id"], action="reject")
    assert again.status_code == 409

    configured_fake_llm.content = None
    _, restated = _propose("Restated Clean Function")
    assert restated["delta_id"] != body["delta_id"]
    assert restated["status"] == "validated"


def test_merge_without_a_target_existing_id_returns_400(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationComponent", "id": "sub-modelling-merge-400", '
        '"name": "Modelling & Specification"}], "relationships": []}'
    )
    session_id, body = _propose("propose a duplicate without saying which to merge into")
    assert body["duplicates"], body

    response = _decide(session_id, body["delta_id"], action="merge")

    assert response.status_code == 400
    assert "target_existing_id" in response.json()["detail"]


def test_accept_pattern_with_no_pattern_suggestion_returns_409(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    session_id, body = _propose("Accept Pattern Nothing Flagged Test Function")
    assert body["pattern_suggestions"] == []

    response = _decide(session_id, body["delta_id"], action="accept-pattern")

    assert response.status_code == 409
    assert "nothing to accept-pattern" in response.json()["detail"]


def test_duplicate_merge_drops_the_new_element_and_rewires_relationships_to_the_existing_one(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationComponent", "id": "sub-modelling-dup", '
        '"name": "Modelling & Specification"}],'
        ' "relationships": [{"type": "Serving", "source": "sub-modelling-dup", "target": "role-ea"}]}'
    )
    session_id, body = _propose("propose a duplicate of sub-modelling")
    assert body["status"] == "flagged"
    assert body["duplicates"], body

    response = _decide(
        session_id,
        body["delta_id"],
        action="merge",
        duplicate_decision="merge",
        target_existing_id="sub-modelling",
        state_classification="Transition",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    elements_text = (isolated_model / "elements.yaml").read_text()
    assert "sub-modelling-dup" not in elements_text
    rels_text = (isolated_model / "relationships.yaml").read_text()
    assert "source: sub-modelling, target: role-ea" in rels_text


def test_duplicate_keep_both_applies_the_new_element_alongside_the_existing_one(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationComponent", "id": "sub-modelling-kb", '
        '"name": "Modelling & Specification"}], "relationships": []}'
    )
    session_id, body = _propose("propose a duplicate, kept anyway")
    assert body["duplicates"], body

    response = _decide(session_id, body["delta_id"], action="keep-both", state_classification="Transition")

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    assert "sub-modelling-kb" in (isolated_model / "elements.yaml").read_text()


@pytest.fixture
def synthetic_pattern_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("modelling_specification.router.conventions.load_rules", lambda: [_SYNTHETIC_PATTERN_RULE])


def test_pattern_keep_direct_applies_the_direct_relationship_as_is(
    configured_fake_llm: FakeCompletion, isolated_model: Path, synthetic_pattern_rule: None
) -> None:
    configured_fake_llm.content = (
        '{"elements": [], "relationships": [{"type": "Serving", "source": "sub-modelling", "target": "role-ea"}]}'
    )
    session_id, body = _propose("serve role-ea directly from sub-modelling")
    assert body["pattern_suggestions"], body

    response = _decide(session_id, body["delta_id"], action="keep-direct", state_classification="Transition")

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    assert "source: sub-modelling, target: role-ea" in (isolated_model / "relationships.yaml").read_text()


def test_pattern_accept_pattern_synthesizes_the_intermediary_form(
    configured_fake_llm: FakeCompletion, isolated_model: Path, synthetic_pattern_rule: None
) -> None:
    # 2026-10-11 clarify: accept-pattern synthesizes the intermediary element and
    # applies the two-leg form directly, rather than discarding the candidate and
    # asking the architect to re-describe it.
    configured_fake_llm.content = (
        '{"elements": [], "relationships": [{"type": "Serving", "source": "sub-modelling", "target": "role-ea"}]}'
    )
    session_id, body = _propose("serve role-ea directly from sub-modelling")
    assert body["pattern_suggestions"], body

    response = _decide(session_id, body["delta_id"], action="accept-pattern", state_classification="Transition")

    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    elements_text = (isolated_model / "elements.yaml").read_text()
    match = re.search(
        r"type: ApplicationService, id: (\S+?), name: Modelling & Specification Application Service", elements_text
    )
    assert match, elements_text
    synthesized_id = match.group(1)
    rels_text = (isolated_model / "relationships.yaml").read_text()
    assert "source: sub-modelling, target: role-ea}" not in rels_text
    assert f"source: sub-modelling, target: {synthesized_id}" in rels_text
    assert f"source: {synthesized_id}, target: role-ea" in rels_text


def test_override_a_convention_rejection_applies_and_drafts_an_adr_stub(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "Capability", "id": "cap-override-test", "name": "Override Test Capability"}],'
        ' "relationships": [{"type": "Realization", "source": "cap-override-test", "target": "req-auto-spec-generation"}]}'
    )
    session_id, body = _propose("add a capability named after its own type")
    assert body["status"] == "flagged"
    assert body["validation_result"]["clean"] is False
    # Only the naming convention should be flagged -- the Realization edge above
    # keeps model_io's own capability-realizes-a-requirement structural check clean,
    # so this exercises overriding a *convention* finding specifically, not the
    # unrelated "build_error" a missing Requirement would also raise.
    assert all(f["check"] != "build_error" for f in body["validation_result"]["findings"])

    response = _decide(
        session_id,
        body["delta_id"],
        action="override",
        rationale="legacy naming, grandfathered in",
        state_classification="Transition",
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "applied"
    assert result["override_decision_id"] is not None
    (adr_path,) = isolated_model.parent.glob("adr/*.md")
    text = adr_path.read_text()
    assert "Status:** Proposed" in text
    assert "legacy naming, grandfathered in" in text


def test_override_cannot_bypass_a_metamodel_violation(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationFunction", "id": "fn-override-metamodel-test", "name": "X"}],'
        ' "relationships": [{"type": "Composition", "source": "sub-modelling", "target": "fn-override-metamodel-test"}]}'
    )
    session_id, body = _propose("propose an illegal relationship")

    response = _decide(session_id, body["delta_id"], action="override", rationale="please let me")

    assert response.status_code == 409
    assert list(isolated_model.parent.glob("adr/*.md")) == []


def test_override_a_duplicate_objection_applies_and_drafts_an_adr_stub(
    configured_fake_llm: FakeCompletion, isolated_model: Path
) -> None:
    # Clean metamodel, no pattern suggestion -- the only objection is the duplicate,
    # exercising _describe_objection's "duplicate" branch rather than "rejection".
    configured_fake_llm.content = (
        '{"elements": [{"type": "ApplicationComponent", "id": "sub-modelling-override-dup", '
        '"name": "Modelling & Specification"}], "relationships": []}'
    )
    session_id, body = _propose("propose a duplicate, override it")
    assert body["duplicates"], body
    assert body["validation_result"]["clean"] is True
    assert body["pattern_suggestions"] == []

    response = _decide(session_id, body["delta_id"], action="override", rationale="dup is fine, keep it")

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "applied"
    assert result["override_decision_id"] is not None
    (adr_path,) = isolated_model.parent.glob("adr/*.md")
    text = adr_path.read_text()
    assert "override: duplicate" in text
    assert "dup is fine, keep it" in text


def test_override_a_pattern_objection_applies_and_drafts_an_adr_stub(
    configured_fake_llm: FakeCompletion, isolated_model: Path, synthetic_pattern_rule: None
) -> None:
    # Clean metamodel, no duplicate -- the only objection is the pattern suggestion,
    # exercising _describe_objection's "pattern" branch rather than "rejection".
    configured_fake_llm.content = (
        '{"elements": [], "relationships": [{"type": "Serving", "source": "sub-modelling", "target": "role-ea"}]}'
    )
    session_id, body = _propose("serve role-ea directly from sub-modelling, override the pattern nudge")
    assert body["pattern_suggestions"], body
    assert body["validation_result"]["clean"] is True
    assert body["duplicates"] == []

    response = _decide(session_id, body["delta_id"], action="override", rationale="direct edge is fine here")

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "applied"
    (adr_path,) = isolated_model.parent.glob("adr/*.md")
    text = adr_path.read_text()
    assert "override: pattern" in text
    assert "source: sub-modelling, target: role-ea" in (isolated_model / "relationships.yaml").read_text()


def test_override_returns_500_when_the_rebuild_leaves_the_model_invalid(
    configured_fake_llm: FakeCompletion, isolated_model: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_fake_llm.content = (
        '{"elements": [{"type": "Capability", "id": "cap-override-build-error-test", "name": "Override Test Capability"}],'
        ' "relationships": [{"type": "Realization", "source": "cap-override-build-error-test", '
        '"target": "req-auto-spec-generation"}]}'
    )
    session_id, body = _propose("add a capability named after its own type")
    assert body["status"] == "flagged"
    monkeypatch.setattr(
        "modelling_specification.router.model_io.write_and_validate",
        lambda: (2, ["the rebuild broke"], [], None),
    )

    response = _decide(session_id, body["delta_id"], action="override", rationale="it's fine")

    assert response.status_code == 500
    assert "invalid" in response.json()["detail"]
