"""Step 5 demo (GH #68 "demonstrate the loop end-to-end", handoff
`.claude/handoffs/HANDOFF_gh-68_conversational-model-coach_2026-10-25.md`): a
modelling intent yields convention-grounded options, a flagged one's objection is
explained, the chosen option previews in a real domain view, and applying it
leaves the whole model validating -- the full coaching loop GH #68's desired
outcome 1 asks for, proven against the real validation/pattern/rendering engines
with only the LLM call faked (`tests/conftest.py`'s `configured_fake_llm`, never a
live provider -- #136's PII gateway has no code yet, so nothing real is sent out).

Runs against `isolated_model` (tests/api/conftest.py) throughout -- the `decide:
apply` step writes to it, and keeping every step on the same isolated copy means
the proposed/previewed state and the applied state are the same model.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from modelling_specification.app import app
from support.fake_llm import FakeCompletion

client = TestClient(app)

# Already includes store-ledger as a member (GH #55's persistence-boundary slice) --
# small and legible, exactly the kind of "comprehensible domain view" GH #68's
# desired outcome 2 asks for, rather than one of the oversized whole-platform views.
PERSISTENCE_VIEW = "view-technology-persistence-boundary"

# A real "way forward" request answered with two independently-validated options,
# grounded in an existing element (store-ledger) and a real convention rule
# (conv-interposed-neo4j-volume, the sw-neo4j -> art-tech-neo4j-volume -> store-akg
# precedent in architecture/model/conventions.yaml) -- not placeholder content.
_WAYS_FORWARD_OPTIONS = (
    '{"options": ['
    '{"rationale": "A direct Assignment from the new service to the ledger store is '
    "the simplest shape, but nothing records what medium the audit records actually "
    'live on.", "convention_refs": [],'
    ' "elements": [{"type": "SystemSoftware", "id": "sw-pii-redaction-service", '
    '"name": "PII Redaction Audit Service"}],'
    ' "relationships": [{"type": "Assignment", "source": "sw-pii-redaction-service", '
    '"target": "store-ledger"}]},'
    '{"rationale": "Follow the established interposed-pattern precedent (sw-neo4j -> '
    "art-tech-neo4j-volume -> store-akg): the new service writes to its own Artifact, "
    'which realizes the ledger store.", "convention_refs": ["conv-interposed-neo4j-volume"],'
    ' "elements": ['
    '{"type": "SystemSoftware", "id": "sw-pii-redaction-service", "name": "PII Redaction Audit Service"}, '
    '{"type": "Artifact", "id": "art-tech-pii-redaction-log", "name": "PII Redaction Audit Log File"}],'
    ' "relationships": ['
    '{"type": "Assignment", "source": "sw-pii-redaction-service", "target": "art-tech-pii-redaction-log"}, '
    '{"type": "Realization", "source": "art-tech-pii-redaction-log", "target": "store-ledger"}]}'
    "]}"
)


def test_coaching_loop_end_to_end(configured_fake_llm: FakeCompletion, isolated_model: Path) -> None:
    """Intent -> grounded options -> explain the flagged one -> preview the chosen
    one in a real domain view -> apply -> the resulting model still validates."""
    configured_fake_llm.content = _WAYS_FORWARD_OPTIONS
    session_id = client.post("/authoring/sessions").json()["session_id"]

    # 1. Ask for a way forward rather than describing one concrete change (FR-001).
    propose = client.post(
        f"/authoring/sessions/{session_id}/propose",
        json={"request": "How should the PII gateway persist its redaction decisions for audit?"},
    ).json()
    assert propose["status"] == "options"
    direct_option, interposed_option = propose["options"]

    # 2. The direct option is not just discouraged, it is outright illegal under the
    #    ArchiMate 3.2 relationship matrix (SystemSoftware --Assignment--> DataObject
    #    is not a permitted shape) -- a hard metamodel violation, never overridable
    #    (Constitution Principle VII; `_check_overridable` below confirms this).
    #    Independently, the pattern engine already names the fix the enterprise
    #    convention prescribes: route through an Artifact.
    assert direct_option["validation_result"]["clean"] is False
    (finding,) = direct_option["validation_result"]["findings"]
    assert finding["check"] == "illegal_relationship"
    assert "not permitted by the ArchiMate 3.2 matrix" in finding["detail"]
    (suggestion,) = direct_option["pattern_suggestions"]
    assert suggestion["proposed_relationship"] == {
        "type": "Assignment",
        "source": "sw-pii-redaction-service",
        "target": "store-ledger",
    }
    assert suggestion["established_pattern"]["intermediary_types"] == ["Artifact"]

    # 3. The interposed option is clean and cites the real convention it follows.
    assert interposed_option["validation_result"]["clean"] is True
    assert interposed_option["pattern_suggestions"] == []
    assert interposed_option["convention_refs"] == ["conv-interposed-neo4j-volume"]

    # 4. Choose it (FR-001's "pick one via propose/select").
    selected = client.post(f"/authoring/sessions/{session_id}/propose/select", json={"option_index": 1}).json()
    delta_id = selected["delta_id"]
    assert selected["status"] == "validated"

    # 5. Preview it in a real, already-legible domain view before anything is
    #    written -- the view already shows store-ledger, so the new nodes connect
    #    straight into it; preview_model marks them "+ <name>".
    before = (isolated_model / "elements.yaml").read_text()
    assert "sw-pii-redaction-service" not in before

    preview = client.get(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/preview",
        params={"view_id": PERSISTENCE_VIEW},
    )
    assert preview.status_code == 200
    assert "PII Redaction Audit Service" in preview.text
    # PlantUML wraps a long label across several <text> runs ("PII"/"Redaction"/
    # "Audit"/"Log"/"File"), so check the one word unique to the Artifact's name
    # rather than the whole phrase verbatim.
    assert "Log" in preview.text
    assert "sw-pii-redaction-service" not in (isolated_model / "elements.yaml").read_text()  # still nothing written

    # 6. Apply it -- the chosen option, same decide loop as a concrete delta.
    applied = client.post(
        f"/authoring/sessions/{session_id}/deltas/{delta_id}/decide",
        json={"action": "apply", "state_classification": "Target"},
    )
    assert applied.status_code == 200
    body = applied.json()
    assert body["status"] == "applied"
    assert body["state_classification"] == "Target"
    # decide() 500s if write_and_validate() fails -- 200 here is the proof the
    # resulting model (the new service, its Artifact, and the real ledger it now
    # feeds) validates as a whole, not just the isolated delta in isolation.
    after = (isolated_model / "elements.yaml").read_text()
    assert "sw-pii-redaction-service" in after
    assert "art-tech-pii-redaction-log" in after
