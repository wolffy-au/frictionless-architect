"""In-memory Candidate Delta session store (R8, Clarification 2).

Session-scoped, process-memory only -- no database, no resume path. A delta's
lifecycle (data-model.md): `proposed -> validated/flagged -> applied/discarded`.
A discarded or interrupted session's deltas are simply dropped with the process
or the session; nothing is written to `architecture/model/` until a delta is
`applied` (`model_io.py`'s write path, R9). This module only holds the shape and
the registry -- validating and applying a delta is Phase 3+ (`authoring/delta.py`).
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeltaStatus(str, Enum):
    """Lifecycle state of a Candidate Delta: proposed, validated or flagged, then applied or discarded."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    FLAGGED = "flagged"
    APPLIED = "applied"
    DISCARDED = "discarded"


@dataclass
class CandidateDelta:
    """A proposed change to the model, accumulated over a conversation (data-model.md).

    Attributes:
        delta_id: Identifier, unique within its session.
        session_id: The owning session.
        elements: Proposed elements (model YAML shape).
        relationships: Proposed relationships (model YAML shape).
        status: Where the delta is in its lifecycle.
        validation_result: ``{"clean": bool, "findings": [...]}`` once validated.
        duplicates: Likely duplicates of existing elements.
        pattern_suggestions: Established-pattern alternatives to direct relationships.
        state_classification: ``Current``, ``Transition`` or ``Target`` once decided.
    """

    delta_id: str
    session_id: str
    elements: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    status: DeltaStatus = DeltaStatus.PROPOSED
    validation_result: dict[str, Any] | None = None
    duplicates: list[dict[str, Any]] = field(default_factory=list)
    pattern_suggestions: list[dict[str, Any]] = field(default_factory=list)
    state_classification: str | None = None


@dataclass
class Session:
    """One authoring conversation and its deltas, keyed by delta id.

    Attributes:
        session_id: Identifier returned to the client.
        deltas: The session's Candidate Deltas.
        pending_options: The most recent "suggest options" proposal awaiting a pick
            (FR-001 "ways forward"), cleared once one is selected or another propose
            request replaces it. Each entry is a normalized option (rationale,
            convention_refs, elements, relationships) plus its own validation result.
    """

    session_id: str
    deltas: dict[str, CandidateDelta] = field(default_factory=dict)
    pending_options: list[dict[str, Any]] = field(default_factory=list)


class SessionStore:
    """Process-memory session/delta registry. No persistence (R8)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create_session(self) -> str:
        """Start a session.

        Returns:
            The new session id.
        """
        session_id = secrets.token_hex(6)
        self._sessions[session_id] = Session(session_id=session_id)
        return session_id

    def get_session(self, session_id: str) -> Session | None:
        """Look up a session.

        Args:
            session_id: The session id.

        Returns:
            The session, or ``None`` if unknown.
        """
        return self._sessions.get(session_id)

    def add_delta(self, session_id: str, delta: CandidateDelta) -> None:
        """Register a delta with a session.

        Args:
            session_id: The owning session.
            delta: The delta to store, keyed by its ``delta_id``.

        Raises:
            KeyError: If the session does not exist.
        """
        self._sessions[session_id].deltas[delta.delta_id] = delta

    def get_delta(self, session_id: str, delta_id: str) -> CandidateDelta | None:
        """Look up a delta.

        Args:
            session_id: The owning session.
            delta_id: The delta id.

        Returns:
            The delta, or ``None`` if the session or delta is unknown.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None
        return session.deltas.get(delta_id)

    def new_delta_id(self) -> str:
        """Return a fresh random delta id (not yet registered)."""
        return secrets.token_hex(4)

    def pending_delta(self, session_id: str) -> CandidateDelta | None:
        """The session's most recent non-terminal delta -- the FR-015 amend target, if
        any. `None` once every delta in the session is `applied`/`discarded`."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        for delta in reversed(list(session.deltas.values())):
            if delta.status not in (DeltaStatus.APPLIED, DeltaStatus.DISCARDED):
                return delta
        return None
