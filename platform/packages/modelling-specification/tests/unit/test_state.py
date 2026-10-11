"""Unit tests for the in-memory Candidate Delta session store (R8, Clarification 2)."""

from __future__ import annotations

from modelling_specification.authoring.state import CandidateDelta, DeltaStatus, SessionStore


def test_create_session_issues_a_distinct_id_each_time() -> None:
    store = SessionStore()
    a = store.create_session()
    b = store.create_session()
    assert a != b
    assert store.get_session(a) is not None
    assert store.get_session(b) is not None


def test_get_session_returns_none_for_an_unknown_id() -> None:
    store = SessionStore()
    assert store.get_session("nope") is None


def test_add_and_get_delta_round_trips() -> None:
    store = SessionStore()
    session_id = store.create_session()
    delta = CandidateDelta(delta_id="d1", session_id=session_id, elements=[{"id": "x"}])

    store.add_delta(session_id, delta)

    stored = store.get_delta(session_id, "d1")
    assert stored is delta
    assert stored is not None
    assert stored.status == DeltaStatus.PROPOSED


def test_get_delta_returns_none_for_unknown_session_or_delta() -> None:
    store = SessionStore()
    session_id = store.create_session()
    assert store.get_delta("unknown-session", "d1") is None
    assert store.get_delta(session_id, "unknown-delta") is None


def test_deltas_are_scoped_per_session() -> None:
    store = SessionStore()
    session_a = store.create_session()
    session_b = store.create_session()
    store.add_delta(session_a, CandidateDelta(delta_id="d1", session_id=session_a))

    assert store.get_delta(session_a, "d1") is not None
    assert store.get_delta(session_b, "d1") is None


def test_new_delta_id_is_distinct_each_call() -> None:
    store = SessionStore()
    assert store.new_delta_id() != store.new_delta_id()


def test_pending_delta_returns_none_when_nothing_is_pending() -> None:
    store = SessionStore()
    session_id = store.create_session()
    assert store.pending_delta(session_id) is None


def test_pending_delta_returns_the_most_recent_non_terminal_delta() -> None:
    store = SessionStore()
    session_id = store.create_session()
    store.add_delta(session_id, CandidateDelta(delta_id="d1", session_id=session_id, status=DeltaStatus.APPLIED))
    store.add_delta(session_id, CandidateDelta(delta_id="d2", session_id=session_id, status=DeltaStatus.FLAGGED))

    pending = store.pending_delta(session_id)

    assert pending is not None
    assert pending.delta_id == "d2"


def test_pending_delta_ignores_discarded_and_applied_deltas() -> None:
    store = SessionStore()
    session_id = store.create_session()
    store.add_delta(session_id, CandidateDelta(delta_id="d1", session_id=session_id, status=DeltaStatus.APPLIED))
    store.add_delta(session_id, CandidateDelta(delta_id="d2", session_id=session_id, status=DeltaStatus.DISCARDED))

    assert store.pending_delta(session_id) is None


def test_candidate_delta_state_classification_is_null_while_proposed() -> None:
    delta = CandidateDelta(delta_id="d1", session_id="s1")
    assert delta.status == DeltaStatus.PROPOSED
    assert delta.state_classification is None


def test_candidate_delta_state_classification_is_queryable_once_set_on_apply() -> None:
    store = SessionStore()
    session_id = store.create_session()
    delta = CandidateDelta(
        delta_id="d1",
        session_id=session_id,
        elements=[{"id": "fn-example", "type": "ApplicationFunction", "name": "X"}],
        status=DeltaStatus.APPLIED,
        state_classification="Transition",
    )
    store.add_delta(session_id, delta)

    retrieved = store.get_delta(session_id, "d1")
    assert retrieved is not None
    assert retrieved.state_classification == "Transition"
