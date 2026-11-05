"""FastAPI router for conversational model authoring (ADR-0020). Mounted into `app.py`.

`decide`/`render`/`config`/`state` land in later phases per contracts/api.md.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pii_gateway import EngineErrorAllowRejected, Resolution
from pydantic import BaseModel

from modelling_specification import model_io, rendering
from modelling_specification.authoring import overrides
from modelling_specification.authoring.delta import (
    DeltaProposalError,
    LlmMessage,
    PiiReviewRequired,
    assign_missing_ids,
    assign_missing_view_ids,
    propose_delta,
    resolve_unknown_element_edits,
    resolve_unknown_element_removals,
    resolve_unknown_endpoints,
    resolve_unknown_members,
    resume_proposal,
    scrub_or_require_review,
)
from modelling_specification.authoring.state import CandidateDelta, DeltaStatus, Session, SessionStore
from modelling_specification.validation import conventions
from modelling_specification.validation.duplicates import find_duplicates
from modelling_specification.validation.fixes import proposed_fix_for_finding
from modelling_specification.validation.metamodel import validate_metamodel
from modelling_specification.validation.patterns import find_pattern_suggestions, synthesize_intermediaries

# Metamodel-level finding `check` names (model_io.validate_model, metamodel.py's own
# build_error) -- never overridable (Constitution Principle VII, FR-002): an override
# may bypass a *convention*/duplicate/pattern objection (FR-014), never ArchiMate 3.2
# legality itself. A convention finding's `check` is always its own rule id instead.
_METAMODEL_CHECK_NAMES = {
    "illegal_relationship",
    "invalid_relationship",
    "broken_connection",
    "orphan_view_node",
    "build_error",
}

# FR-009: every decide action that results in an applied change carries a
# Current/Transition/Target classification; the agent asks rather than guessing
# (US3 Scenario 2) when the architect's decide call doesn't supply one.
_VALID_STATES = {"Current", "Transition", "Target"}

router = APIRouter(prefix="/authoring", tags=["authoring"])

_store = SessionStore()
# FR-011: auto-render-vs-on-request is a configurable, process-wide choice, not a
# per-session one -- in-memory only, same no-persistence posture as the session store.
_config = {"auto_render": False}


class ProposeRequest(BaseModel):
    """Body of ``POST /sessions/{session_id}/propose``.

    Attributes:
        request: The architect's natural-language request.
    """

    request: str


class SelectOptionRequest(BaseModel):
    """Body of ``POST /sessions/{session_id}/propose/select``.

    Attributes:
        option_index: Index into the most recent ``propose`` response's ``options``.
    """

    option_index: int


class ResolvePiiRequest(BaseModel):
    """Body of ``POST /sessions/{session_id}/propose/resolve-pii``.

    Attributes:
        resolution: How the architect resolves the flagged match --
            ``"redact"`` (proceed with the matched span(s) redacted),
            ``"allow"`` (proceed with the original text unchanged), or
            ``"edit"`` (``edited_text``, which the architect supplies themselves in
            place of the flagged original, is re-scrubbed before proceeding -- not
            assumed clean).
        edited_text: Required when ``resolution`` is ``"edit"``; ignored otherwise.
    """

    resolution: Resolution
    edited_text: str | None = None


class DecideRequest(BaseModel):
    """Body of ``POST /sessions/{session_id}/deltas/{delta_id}/decide``.

    Attributes:
        action: ``apply``, ``keep-both``, ``keep-direct``, ``merge``, ``reject``,
            ``accept-pattern`` or ``override``.
        rationale: Why an objection is overridden (``override`` only; optional).
        duplicate_decision: Echo of the duplicate decision taken (``merge``).
        target_existing_id: Existing element to merge into (required for ``merge``).
        state_classification: Optional ``Current``, ``Transition`` or ``Target``.
    """

    action: str
    rationale: str | None = None
    duplicate_decision: str | None = None
    target_existing_id: str | None = None
    state_classification: str | None = None


class ConfigRequest(BaseModel):
    """Body of ``PUT /config``.

    Attributes:
        auto_render: Whether applying a delta also renders the result inline.
    """

    auto_render: bool


@router.post("/sessions")
def create_session() -> dict[str, str]:
    """Start an authoring session.

    Returns:
        ``{"session_id": ...}``.
    """
    return {"session_id": _store.create_session()}


def _delta_response(delta: CandidateDelta) -> dict[str, Any]:
    return {
        "delta_id": delta.delta_id,
        "status": delta.status.value,
        "elements": delta.elements,
        "relationships": delta.relationships,
        "views": delta.views,
        "view_membership_edits": delta.view_membership_edits,
        "element_edits": delta.element_edits,
        "element_removals": delta.element_removals,
        "relationship_removals": delta.relationship_removals,
        "validation_result": delta.validation_result,
        "duplicates": delta.duplicates,
        "pattern_suggestions": delta.pattern_suggestions,
    }


def _catalogue_and_rules() -> tuple[
    list[tuple[str, str, str]],
    list[dict[str, Any]],
    list[str],
    list[tuple[str, str, str]],
    list[tuple[str, str, str, str]],
]:
    existing, types_by_id = model_io.existing_elements_and_types()
    catalogue = [
        (e["id"], types_by_id[e["id"]], str(e.get("name", ""))) for e in existing if e.get("id") in types_by_id
    ]
    contexts = sorted({str(e.get("context", model_io.DEFAULT_CONTEXT)) for e in existing})
    views = rendering.view_catalogue()
    relationships = model_io.existing_relationships()
    return catalogue, conventions.load_rules(), contexts, views, relationships


def _pii_match_payload(review: PiiReviewRequired) -> list[dict[str, Any]]:
    return [{"category": m.category, "location": list(m.location), "confidence": m.confidence} for m in review.matches]


def _pii_review_response(review: PiiReviewRequired) -> dict[str, Any]:
    """`propose`/`resolve-pii`'s response when `scrub()` flags a PII/PHI match for
    review (ADR-0014 amendment): no delta is created and the LLM call has not been
    made -- the architect must resolve it via `POST .../propose/resolve-pii`.

    `detection_failed` is true when the flagged "match" is pii-gateway's synthetic
    engine-error match (research.md R6) rather than a real detection -- the
    architect must be told detection failed, not left to infer it from the
    `_ENGINE_ERROR` category in `matches` (2026-11-05 decision)."""
    return {
        "delta_id": None,
        "status": "pii_review_required",
        "pii_review_required": True,
        "detection_failed": review.pending_confirmation.detection_failed,
        "matches": _pii_match_payload(review),
        "elements": [],
        "relationships": [],
    }


def _handle_proposed(
    session_id: str, session: Session, catalogue: list[tuple[str, str, str]], proposed: dict[str, Any]
) -> dict[str, Any]:
    """Turn `propose_delta`/`resume_proposal`'s successful output into the shared
    `propose`/`propose/select`/`propose/resolve-pii` response: accumulate a single
    concrete delta into the session's pending `CandidateDelta`, or stash "ways
    forward" options for `propose/select` to pick from."""
    if "options" in proposed:
        pending = _store.pending_delta(session_id)
        in_flight = pending.elements if pending else []
        session.pending_options = [_prepare_option(o, in_flight) for o in proposed["options"]]
        return {"delta_id": None, "status": "options", "options": session.pending_options}
    session.pending_options = []

    new_elements = assign_missing_ids(proposed["elements"], model_io.existing_element_ids())
    new_views = assign_missing_view_ids(proposed["views"], model_io.existing_view_ids())
    delta = _store.pending_delta(session_id)
    in_flight = [*(delta.elements if delta else []), *new_elements]
    known_names = {eid: name for eid, _etype, name in catalogue}
    known_names.update({e["id"]: str(e.get("name", "")) for e in in_flight if e.get("id")})
    new_relationships, rel_notes = resolve_unknown_endpoints(proposed["relationships"], known_names)
    new_membership_edits, membership_notes = resolve_unknown_members(
        proposed.get("view_membership_edits") or [], known_names
    )
    new_element_edits, element_edit_notes = resolve_unknown_element_edits(
        proposed.get("element_edits") or [], known_names
    )
    new_element_removals, element_removal_notes = resolve_unknown_element_removals(
        proposed.get("element_removals") or [], known_names
    )
    new_relationship_removals, relationship_removal_notes = resolve_unknown_endpoints(
        proposed.get("relationship_removals") or [], known_names
    )
    notes = rel_notes + membership_notes + element_edit_notes + element_removal_notes + relationship_removal_notes

    if delta is None:
        delta = CandidateDelta(delta_id=_store.new_delta_id(), session_id=session_id)
        _store.add_delta(session_id, delta)
    # FR-015: a later request touching the pending delta amends/extends it rather
    # than starting an independent one -- one accumulating delta per conversation
    # until it is applied or discarded (data-model.md Candidate Delta lifecycle).
    delta.elements = delta.elements + new_elements
    delta.relationships = delta.relationships + new_relationships
    delta.views = delta.views + new_views
    delta.view_membership_edits = delta.view_membership_edits + new_membership_edits
    delta.element_edits = delta.element_edits + new_element_edits
    delta.element_removals = delta.element_removals + new_element_removals
    delta.relationship_removals = delta.relationship_removals + new_relationship_removals

    _validate_and_flag(delta)
    response = _delta_response(delta)
    if not delta.has_changes():
        notes.append(
            "No change was proposed. This feature can add elements, relationships and views; "
            "rename or remove an existing element; remove an existing relationship; or "
            "add/remove an existing element from an existing view's membership. Nothing else "
            "about an existing element, relationship or view can be changed."
        )
    if notes:
        response["notes"] = notes
    return response


@router.post(
    "/sessions/{session_id}/propose",
    responses={
        404: {"description": "no session with the given session_id"},
        502: {"description": "the LLM proposal could not be turned into a usable delta"},
    },
)
def propose(session_id: str, body: ProposeRequest) -> dict[str, Any]:
    """Turn a natural-language request into a validated, possibly flagged, delta.

    Later requests extend the session's pending delta rather than starting a new one.
    Nothing is written to the model.

    Args:
        session_id: The session the request belongs to.
        body: The request text.

    Returns:
        The delta (id, status, elements, relationships, views, view_membership_edits,
        element_edits, element_removals, relationship_removals, validation result,
        duplicates and pattern suggestions), plus ``notes`` when there is something to
        tell the architect. When the LLM answers in plain text, ``status`` is ``"message"`` and
        ``delta_id`` is ``None``. When the architect asked for a way forward rather
        than describing one change, ``status`` is ``"options"`` and ``options`` holds
        2-3 candidate deltas, each with its own ``rationale``, ``convention_refs`` and
        validation result -- pick one via ``POST .../propose/select``. When `scrub()`
        flags a PII/PHI match in the request for review (ADR-0014 amendment),
        ``status`` is ``"pii_review_required"``, ``pii_review_required`` is ``true``,
        ``matches`` lists what was flagged, and the LLM call has NOT been made --
        resolve it via ``POST .../propose/resolve-pii`` before a delta is proposed.

    Raises:
        HTTPException: 404 if the session is unknown; 502 if the LLM output cannot be
            turned into a delta.
    """
    session = _store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"no session {session_id!r}")

    catalogue, rules, contexts, views, relationships = _catalogue_and_rules()
    # A fresh `propose` call supersedes any PII review left pending from an earlier
    # one in this session (the architect moved on without resolving it).
    session.pending_pii_confirmation = None
    try:
        proposed = propose_delta(body.request, catalogue, rules, contexts, views, relationships)
    except PiiReviewRequired as review:
        session.pending_pii_confirmation = review.pending_confirmation
        session.pending_options = []
        return _pii_review_response(review)
    except LlmMessage as message:
        session.pending_options = []
        return {
            "delta_id": None,
            "status": "message",
            "message": message.text,
            "elements": [],
            "relationships": [],
            "views": [],
            "view_membership_edits": [],
            "element_edits": [],
            "element_removals": [],
            "relationship_removals": [],
        }
    except DeltaProposalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _handle_proposed(session_id, session, catalogue, proposed)


@router.post(
    "/sessions/{session_id}/propose/resolve-pii",
    responses={
        404: {"description": "no session with the given session_id"},
        409: {
            "description": "no PII/PHI match is pending review, or resolution is 'allow' but the "
            "pending match is a detector-engine error (detection never ran, so there is nothing "
            "real to allow -- the pending confirmation is left in place; redact or edit instead)"
        },
        400: {"description": "resolution is 'edit' but edited_text was not supplied"},
        502: {"description": "the LLM proposal could not be turned into a usable delta"},
    },
)
def resolve_pii(session_id: str, body: ResolvePiiRequest) -> dict[str, Any]:
    """Resolve a PII/PHI match that `propose` flagged for review (ADR-0014
    amendment) and make the LLM call `propose` withheld, using the resolved text.

    ``resolution="redact"`` proceeds with the matched span(s) redacted;
    ``"allow"`` proceeds with the original text unchanged; ``"edit"`` re-scrubs
    ``edited_text`` -- the architect's own replacement for the flagged original --
    under the same `conversational-authoring` context before proceeding: it is
    never assumed clean. A still-sensitive edit is re-flagged exactly like a fresh
    `propose` call (``pii_review_required`` again, no LLM call), never silently
    sent on and never escalated to a different behaviour.

    When the pending match is pii-gateway's synthetic engine-error match
    (research.md R6) rather than a real detection, ``"allow"`` is rejected (409,
    2026-11-05 decision): detection never ran, so there is no real match for the
    architect to judge and allow, and letting it through would send wholly
    uninspected text to the LLM. The pending confirmation is left in place --
    ``"redact"`` or ``"edit"`` still resolve it.

    Args:
        session_id: The owning session.
        body: The architect's chosen resolution and, for ``edit``, the replacement text.

    Returns:
        The resulting delta/options/message, same shape as ``propose``'s -- or,
        for ``edit``, another ``pii_review_required`` response if the replacement
        text is itself still flagged.

    Raises:
        HTTPException: 404 if the session is unknown; 409 if no PII/PHI match is
            pending review, or if ``resolution`` is ``allow`` on a pending
            detector-engine-error match; 400 if ``resolution`` is ``edit`` with no
            (or blank) ``edited_text``; 502 if the LLM output cannot be turned into
            a delta.
    """
    session = _store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"no session {session_id!r}")
    pending = session.pending_pii_confirmation
    if pending is None:
        raise HTTPException(status_code=409, detail="no PII/PHI match is pending review")

    if body.resolution == Resolution.EDIT:
        if not body.edited_text or not body.edited_text.strip():
            raise HTTPException(status_code=400, detail="resolution 'edit' requires non-empty edited_text")
        try:
            resolved_text = scrub_or_require_review(body.edited_text)
        except PiiReviewRequired as review:
            session.pending_pii_confirmation = review.pending_confirmation
            session.pending_options = []
            return _pii_review_response(review)
    else:
        try:
            resolved_text = pending.resolve(body.resolution)
        except EngineErrorAllowRejected as exc:
            # Pending confirmation is deliberately left in place -- the architect
            # can still redact or edit; only `allow` on an engine-error match is
            # rejected (2026-11-05 decision).
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    session.pending_pii_confirmation = None

    catalogue, rules, _contexts, _views, _relationships = _catalogue_and_rules()
    try:
        proposed = resume_proposal(resolved_text, catalogue, rules)
    except LlmMessage as message:
        session.pending_options = []
        return {
            "delta_id": None,
            "status": "message",
            "message": message.text,
            "elements": [],
            "relationships": [],
            "views": [],
            "view_membership_edits": [],
            "element_edits": [],
            "element_removals": [],
            "relationship_removals": [],
        }
    except DeltaProposalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _handle_proposed(session_id, session, catalogue, proposed)


@router.post(
    "/sessions/{session_id}/propose/select",
    responses={
        404: {"description": "no session with the given session_id"},
        409: {"description": "no options are pending, or option_index is out of range"},
    },
)
def select_option(session_id: str, body: SelectOptionRequest) -> dict[str, Any]:
    """Pick one of the most recent ``propose`` call's suggested options (FR-001 "ways
    forward") and turn it into the session's pending Candidate Delta, same as a
    concrete ``propose`` request would -- reusing the same validation/duplicate/
    pattern checks and the normal apply/reject decision loop.

    Args:
        session_id: The owning session.
        body: The chosen option's index into the last ``propose`` response's ``options``.

    Returns:
        The resulting delta, same shape as ``propose``'s.

    Raises:
        HTTPException: 404 if the session is unknown; 409 if no options are pending or
            the index is out of range.
    """
    session = _store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"no session {session_id!r}")
    if not (0 <= body.option_index < len(session.pending_options)):
        raise HTTPException(status_code=409, detail="no pending option at that index")

    chosen = session.pending_options[body.option_index]
    session.pending_options = []

    delta = _store.pending_delta(session_id)
    if delta is None:
        delta = CandidateDelta(delta_id=_store.new_delta_id(), session_id=session_id)
        _store.add_delta(session_id, delta)
    delta.elements = delta.elements + chosen["elements"]
    delta.relationships = delta.relationships + chosen["relationships"]

    _validate_and_flag(delta)
    return _delta_response(delta)


def _delta_element_types(elements: list[dict[str, Any]]) -> dict[str, str]:
    types: dict[str, str] = {}
    for e in elements:
        eid = e.get("id")
        t = model_io.canon(str(e.get("type", "")), [], "delta element") if eid else None
        if eid and t:
            types[eid] = t
    return types


def _validate(
    elements: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    views: list[dict[str, Any]] | None = None,
    view_membership_edits: list[dict[str, Any]] | None = None,
    element_edits: list[dict[str, Any]] | None = None,
    element_removals: list[str] | None = None,
    relationship_removals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run every check (FR-002/003/005/008) against the given elements/relationships/
    views and return `{"validation_result", "duplicates", "pattern_suggestions",
    "clean"}`. A proposed view is checked the same way `model_io.add_views` always
    checks one -- unknown context, unknown include_types concept, unknown member id,
    a colliding view id, viewpoint conformance -- surfacing as a `build_error`
    finding, same as an illegal relationship (duplicate/pattern checks don't apply to
    views, only to elements/relationships). `view_membership_edits` is checked the
    same way: applied to the named existing view before the same membership checks
    run. `element_edits`/`element_removals`/`relationship_removals` (ADR-0037 item 8)
    are applied to the existing model before the same metamodel/referential-integrity
    checks run, so a removal that would leave a dangling relationship endpoint
    elsewhere surfaces as the usual finding, never silently."""
    metamodel_result = validate_metamodel(
        elements, relationships, views, view_membership_edits, element_edits, element_removals, relationship_removals
    )
    rules = conventions.load_rules()
    convention_findings = conventions.check_elements(elements, rules)
    findings = metamodel_result["findings"] + convention_findings
    rules_by_id = {r["id"]: r for r in rules}
    for finding in findings:
        finding["proposed_fix"] = proposed_fix_for_finding(finding, rules_by_id)
    validation_result = {"clean": not findings, "findings": findings}

    duplicates = find_duplicates(elements)

    types_by_id = {**model_io.existing_element_types(), **_delta_element_types(elements)}
    pattern_suggestions = find_pattern_suggestions(relationships, types_by_id, rules)

    return {
        "validation_result": validation_result,
        "duplicates": duplicates,
        "pattern_suggestions": pattern_suggestions,
        "clean": validation_result["clean"] and not duplicates and not pattern_suggestions,
    }


def _validate_and_flag(delta: CandidateDelta) -> None:
    """Run every check against the whole accumulated delta and set
    `validation_result`/`duplicates`/`pattern_suggestions`/`status`."""
    outcome = _validate(
        delta.elements,
        delta.relationships,
        delta.views,
        delta.view_membership_edits,
        delta.element_edits,
        delta.element_removals,
        delta.relationship_removals,
    )
    delta.validation_result = outcome["validation_result"]
    delta.duplicates = outcome["duplicates"]
    delta.pattern_suggestions = outcome["pattern_suggestions"]
    delta.status = DeltaStatus.VALIDATED if outcome["clean"] else DeltaStatus.FLAGGED


def _prepare_option(option: dict[str, Any], in_flight: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Assign ids, repoint misspelt endpoints, and validate one suggested option
    (FR-001 "ways forward") so the architect sees its rationale and standing before
    picking it -- mirrors the concrete-delta path but kept independent per option.

    `in_flight` is the session's already-pending `CandidateDelta.elements`, if any --
    not yet written to disk, so `model_io.existing_element_ids()` alone can't see them.
    Without folding them in too, assigning an id or resolving an endpoint here could
    collide with or misresolve against an element the architect already has pending
    (same reason `propose()`'s concrete-delta path builds its own `in_flight` list)."""
    in_flight = in_flight or []
    known_ids = model_io.existing_element_ids() | {e["id"] for e in in_flight if e.get("id")}
    elements = assign_missing_ids(option["elements"], known_ids)
    relationships, notes = resolve_unknown_endpoints(option["relationships"], _option_known_names(elements, in_flight))
    outcome = _validate(elements, relationships)
    return {
        "rationale": option["rationale"],
        "convention_refs": option["convention_refs"],
        "elements": elements,
        "relationships": relationships,
        "notes": notes,
        "validation_result": outcome["validation_result"],
        "duplicates": outcome["duplicates"],
        "pattern_suggestions": outcome["pattern_suggestions"],
    }


def _option_known_names(
    new_elements: list[dict[str, Any]], in_flight: list[dict[str, Any]] | None = None
) -> dict[str, str]:
    existing, _types = model_io.existing_elements_and_types()
    known_names = {e["id"]: str(e.get("name", "")) for e in existing if e.get("id")}
    known_names.update({e["id"]: str(e.get("name", "")) for e in (in_flight or []) if e.get("id")})
    known_names.update({e["id"]: str(e.get("name", "")) for e in new_elements if e.get("id")})
    return known_names


@router.post(
    "/sessions/{session_id}/deltas/{delta_id}/decide",
    responses={
        400: {"description": "the requested action is missing a required field, or is not a known action"},
        409: {"description": "the delta is not in a state this action can be taken on"},
    },
)
def decide(session_id: str, delta_id: str, body: DecideRequest) -> Any:
    """Act on a validated or flagged delta: apply, merge, reject, accept a pattern or override.

    Args:
        session_id: The owning session.
        delta_id: The delta to decide on.
        body: The chosen action and its supporting fields.

    Returns:
        The outcome of the action (applied or discarded, with the classification and
        any override decision id), or a 422 response ``{"needs": "state_classification"}``
        when an unrecognised classification was given.

    Raises:
        HTTPException: 400 for an unknown action or a missing required field; 409 if the
            delta is already applied or discarded, is flagged but ``apply`` was asked, the action does not fit
            its state (nothing to override or accept, or a hard metamodel violation).
    """
    delta = _store.get_delta(session_id, delta_id)
    if delta is None or delta.status in (DeltaStatus.APPLIED, DeltaStatus.DISCARDED):
        raise HTTPException(status_code=409, detail=f"delta {delta_id!r} is not awaiting a decision")

    if body.action == "apply":
        if delta.status is not DeltaStatus.VALIDATED:
            raise HTTPException(status_code=409, detail="delta is flagged -- resolve its objections or override first")
        return _finalize(delta, body, _apply_and_respond)

    if body.action in ("keep-both", "keep-direct"):
        # FR-006/FR-008: an explicit decision to proceed with the delta exactly as
        # proposed -- legal, just flagged as a likely duplicate or a non-idiomatic
        # (but legal) relationship shortcut.
        return _finalize(delta, body, _apply_and_respond)

    if body.action == "merge":
        if not body.target_existing_id:
            raise HTTPException(status_code=400, detail="merge requires target_existing_id")
        _merge_into_existing(delta, body.target_existing_id)
        return _finalize(delta, body, _apply_and_respond)

    if body.action == "reject":
        # FR-004/FR-007: never silently apply, auto-correct, or drop -- the delta is
        # discarded with no write. FR-017 falls out for free: nothing here
        # auto-retries a different fix -- the next move is always a new `propose`
        # from the architect, never generated by this endpoint.
        return _reject(delta)

    if body.action == "accept-pattern":
        # FR-008 (2026-10-11 clarify): the agent synthesizes the intermediary
        # element(s) the matched `interposed-pattern` rule implies and applies that
        # two-leg form directly, splicing it into the delta in place of the matched
        # direct relationship -- never discards-and-asks the architect to re-describe
        # the intermediary form.
        _accept_pattern(delta)
        return _finalize(delta, body, _apply_and_respond)

    if body.action == "override":
        _check_overridable(delta)
        return _finalize(delta, body, lambda d, s: _apply_with_override(d, body.rationale, s))

    raise HTTPException(status_code=400, detail=f"unsupported decide action {body.action!r}")


def _finalize(
    delta: CandidateDelta, body: DecideRequest, apply_fn: Callable[[CandidateDelta, str | None], dict[str, Any]]
) -> Any:
    """The Current/Transition/Target classification is optional (2026-10-12: state is
    not needed to author a change). When one is supplied it is still recorded, but an
    unrecognised value is rejected with a 422 shaped `{"needs": "state_classification"}`
    (contracts/api.md) rather than silently stored."""
    if body.state_classification is not None and body.state_classification not in _VALID_STATES:
        return JSONResponse(status_code=422, content={"needs": "state_classification"})
    return apply_fn(delta, body.state_classification)


def _check_overridable(delta: CandidateDelta) -> None:
    """Raises `HTTPException` when `override` isn't allowed: nothing flagged, or a
    hard ArchiMate metamodel violation among the findings (Constitution Principle
    VII) -- an override may bypass a convention/duplicate/pattern objection (FR-014),
    never metamodel legality itself."""
    if delta.status is not DeltaStatus.FLAGGED:
        raise HTTPException(status_code=409, detail="nothing is flagged to override")
    findings = (delta.validation_result or {}).get("findings", [])
    if any(f["check"] in _METAMODEL_CHECK_NAMES for f in findings):
        raise HTTPException(
            status_code=409,
            detail="ArchiMate metamodel violations cannot be overridden -- restate the request instead",
        )


def _reject(delta: CandidateDelta) -> dict[str, Any]:
    delta.status = DeltaStatus.DISCARDED
    return {"delta_id": delta.delta_id, "status": delta.status.value}


def _accept_pattern(delta: CandidateDelta) -> None:
    """FR-008 'accept-pattern': splice the synthesized intermediary form in place of
    each matched direct relationship -- the original direct relationships are
    dropped, never applied alongside the synthesized ones."""
    if not delta.pattern_suggestions:
        raise HTTPException(status_code=409, detail="nothing to accept-pattern -- no pattern suggestion is flagged")
    existing_elements, _types = model_io.existing_elements_and_types()
    name_by_id = {e["id"]: e.get("name", e["id"]) for e in existing_elements if e.get("id")}
    name_by_id.update({e["id"]: e.get("name", e["id"]) for e in delta.elements if e.get("id")})
    existing_ids = model_io.existing_element_ids() | {e["id"] for e in delta.elements if e.get("id")}

    matched = {
        (p["proposed_relationship"]["type"], p["proposed_relationship"]["source"], p["proposed_relationship"]["target"])
        for p in delta.pattern_suggestions
    }
    delta.relationships = [
        rel for rel in delta.relationships if (rel.get("type"), rel.get("source"), rel.get("target")) not in matched
    ]
    for suggestion in delta.pattern_suggestions:
        synthesized = synthesize_intermediaries(suggestion, name_by_id, existing_ids)
        delta.elements = delta.elements + synthesized["elements"]
        delta.relationships = delta.relationships + synthesized["relationships"]
        existing_ids |= {e["id"] for e in synthesized["elements"]}


def _merge_into_existing(delta: CandidateDelta, target_existing_id: str) -> None:
    """FR-006 'merge': the existing element is the one that stays -- no new element
    is written; any relationship that referenced one of the dropped elements now
    points at `target_existing_id` instead."""
    dropped_ids = {e["id"] for e in delta.elements if e.get("id")}
    delta.elements = []
    for rel in delta.relationships:
        if rel.get("source") in dropped_ids:
            rel["source"] = target_existing_id
        if rel.get("target") in dropped_ids:
            rel["target"] = target_existing_id


def _apply_delta_edits_and_removals(delta: CandidateDelta) -> None:
    """The ADR-0037 item 8 write paths: narrow, scoped edits/removals to existing
    elements/relationships, distinct from `append_delta`'s additive-only writes."""
    if delta.view_membership_edits:
        model_io.apply_view_membership_edits(delta.view_membership_edits)
    if delta.element_edits:
        model_io.apply_element_edits(delta.element_edits)
    if delta.element_removals:
        model_io.apply_element_removals(delta.element_removals)
    if delta.relationship_removals:
        model_io.apply_relationship_removals(delta.relationship_removals)


def _apply_and_respond(delta: CandidateDelta, state_classification: str | None) -> dict[str, Any]:
    model_io.append_delta(delta.elements, delta.relationships, delta.views)
    _apply_delta_edits_and_removals(delta)
    code, build_errors, _warnings, _result = model_io.write_and_validate()
    if build_errors or code != 0:
        raise HTTPException(status_code=500, detail="applying the delta left the model invalid")
    delta.status = DeltaStatus.APPLIED
    delta.state_classification = state_classification
    response: dict[str, Any] = {
        "delta_id": delta.delta_id,
        "status": delta.status.value,
        "state_classification": delta.state_classification,
        "override_decision_id": None,
    }
    affected_id = _first_affected_object_id(delta)
    if _config["auto_render"] and affected_id is not None:
        # FR-012: render the affected element immediately, with no manual step.
        # Best-effort -- an object not yet a member of any curated view simply
        # has nothing to show; that is not an apply failure.
        rendered = _resolve_and_render(affected_id, None)
        if rendered is not None:
            response["render"] = rendered
    return response


def _describe_objection(delta: CandidateDelta) -> tuple[str, str]:
    """What FR-014's Override Decision Record calls `overridden_objection` and
    `objection_detail` -- the convention/duplicate/pattern flag the architect is
    proceeding past (never a metamodel one; `decide()` already blocked those)."""
    if delta.validation_result and not delta.validation_result["clean"]:
        return "rejection", "; ".join(f["detail"] for f in delta.validation_result["findings"])
    if delta.duplicates:
        detail = "; ".join(f"{d['existing_element_id']} ({', '.join(d['matched_fields'])})" for d in delta.duplicates)
        return "duplicate", detail
    if delta.pattern_suggestions:
        detail = "; ".join(str(p["proposed_relationship"]) for p in delta.pattern_suggestions)
        return "pattern", detail
    return "unknown", "no recorded objection"


def _apply_with_override(
    delta: CandidateDelta, rationale: str | None, state_classification: str | None
) -> dict[str, Any]:
    overridden_objection, objection_detail = _describe_objection(delta)
    model_io.append_delta(delta.elements, delta.relationships, delta.views)
    _apply_delta_edits_and_removals(delta)
    code, build_errors, _warnings, _result = model_io.write_and_validate()
    if build_errors or code != 0:
        raise HTTPException(status_code=500, detail="applying the override left the model invalid")
    delta.status = DeltaStatus.APPLIED
    delta.state_classification = state_classification
    applied_delta_summary = ", ".join(e["id"] for e in delta.elements if e.get("id")) or "relationship-only delta"
    record = overrides.draft_override(overridden_objection, objection_detail, rationale, applied_delta_summary)
    return {
        "delta_id": delta.delta_id,
        "status": delta.status.value,
        "state_classification": delta.state_classification,
        "override_decision_id": record["id"],
    }


@router.get("/config")
def get_config() -> dict[str, bool]:
    """Return the current configuration.

    Returns:
        ``{"auto_render": bool}``.
    """
    return dict(_config)


@router.put("/config")
def put_config(body: ConfigRequest) -> dict[str, bool]:
    """Set the process-wide auto-render choice (in memory only).

    Args:
        body: The new configuration.

    Returns:
        The configuration now in force.
    """
    _config["auto_render"] = body.auto_render
    return dict(_config)


def _first_affected_object_id(delta: CandidateDelta) -> str | None:
    """A representative id for the delta's "affected element(s)" (FR-012): the first
    new element if any, else the first new relationship's target, else the first new
    view's own id, else the first view-membership edit's view id, else the first
    edited/removed element's own id, else the first removed relationship's target --
    a delta that only touches existing objects still has an affected object to
    render where one still exists on disk (a removal has none, so falls through to
    `None`). `rendering.resolve_view_request` tries `object_id` as an exact view id
    before an element id, so a view id resolves straight to itself once it's on disk."""
    if delta.elements:
        return delta.elements[0].get("id")
    if delta.relationships:
        return delta.relationships[0].get("target")
    if delta.views:
        return delta.views[0].get("id")
    if delta.view_membership_edits:
        return delta.view_membership_edits[0].get("view_id")
    if delta.element_edits:
        return delta.element_edits[0].get("id")
    return None


def _resolve_and_render(object_id: str | None, description: str | None) -> dict[str, Any] | None:
    """Resolve+render (FR-013/FR-016); `None` when nothing resolves unambiguously --
    the caller decides what that means (a 404 for an explicit request, silently
    skipped for an auto-render best-effort)."""
    resolution = rendering.resolve_view_request(object_id, description)
    if resolution["resolved_view_id"] is None:
        return None
    return {
        "view_id": resolution["resolved_view_id"],
        "svg": rendering.render_single_view(resolution["resolved_view_id"]),
    }


def _known_view_id(view_id: str) -> str | None:
    """The server's own copy of `view_id` if it names a real view, else `None`, so a
    query-string value never flows into what is rendered or served."""
    return next((v["id"] for v in rendering.list_views() if v["id"] == view_id), None)


def _svg_headers(view_id: str) -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "X-View-Id": view_id,
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
    }


@router.get("/views")
def get_views() -> list[dict[str, str]]:
    return rendering.list_views()


@router.get(
    "/render",
    responses={404: {"description": "no view resolves from the given object_id/description"}},
)
def get_render(
    object_id: str | None = None,
    description: str | None = None,
    output_format: Annotated[Literal["json", "svg"], Query(alias="format")] = "json",
) -> Any:
    resolution = rendering.resolve_view_request(object_id, description)
    if resolution["ambiguous_candidates"]:
        return JSONResponse(status_code=300, content={"ambiguous_candidates": resolution["ambiguous_candidates"]})
    if resolution["resolved_view_id"] is None:
        raise HTTPException(status_code=404, detail="no view resolves from the given object_id/description")
    known = _known_view_id(str(resolution["resolved_view_id"]))
    if known is None:
        raise HTTPException(status_code=404, detail="no view resolves from the given object_id/description")
    svg = rendering.render_single_view(known)
    if output_format == "svg":
        # `render_single_view` already strips active content before returning (see
        # `rendering.sanitize_svg`); re-applying it at the response boundary is
        # idempotent and keeps this endpoint safe even if a future change to
        # `rendering` ever returns unsanitized markup -- the sink, not just the
        # source, is responsible for what crosses the trust boundary (CWE-79).
        return Response(
            content=rendering.sanitize_svg(svg),
            media_type="image/svg+xml",
            headers=_svg_headers(known),
        )
    return {
        "view_id": resolution["resolved_view_id"],
        "svg": svg,
    }


def _preview_view_resolution(delta: CandidateDelta) -> dict[str, Any]:
    """Where to preview `delta` when no view was chosen, in `resolve_view_request`'s
    shape: the view it proposes or edits, else a view showing an existing element it
    touches -- the first such element that resolves, or is ambiguous, wins."""
    named = [v.get("id") for v in delta.views] + [e.get("view_id") for e in delta.view_membership_edits]
    if named:
        return {"resolved_view_id": named[0], "ambiguous_candidates": []}
    existing = model_io.existing_element_ids()
    touched: list[Any] = [end for r in delta.relationships for end in (r.get("source"), r.get("target"))]
    touched += [*(e.get("id") for e in delta.element_edits), *delta.element_removals]
    touched += [end for r in delta.relationship_removals for end in (r.get("source"), r.get("target"))]
    for object_id in touched:
        if object_id in existing:
            resolution = rendering.resolve_view_request(object_id, None)
            if resolution["resolved_view_id"] is not None or resolution["ambiguous_candidates"]:
                return resolution
    return {"resolved_view_id": None, "ambiguous_candidates": []}


@router.get(
    "/sessions/{session_id}/deltas/{delta_id}/preview",
    responses={
        404: {"description": "no such pending delta, or no view resolves/exists for it"},
        409: {"description": "the delta is empty, or the change cannot be previewed"},
    },
)
def get_preview(session_id: str, delta_id: str, view_id: str | None = None) -> Response:
    """Render a pending delta, of any kind, in a view *before* anything is written
    (nothing is persisted). `view_id` may name a view the delta itself proposes. Without
    it the view comes from `_preview_view_resolution`; ambiguity or no match is reported
    like `GET /render`."""
    delta = _store.get_delta(session_id, delta_id)
    if delta is None or delta.status in (DeltaStatus.APPLIED, DeltaStatus.DISCARDED):
        raise HTTPException(status_code=404, detail=f"no pending delta {delta_id!r}")
    if not delta.has_changes():
        raise HTTPException(status_code=409, detail="the delta is empty; there is nothing to preview")
    if view_id is None:
        resolution = _preview_view_resolution(delta)
        if resolution["ambiguous_candidates"]:
            return JSONResponse(status_code=300, content={"ambiguous_candidates": resolution["ambiguous_candidates"]})
        resolved = resolution["resolved_view_id"]
        if resolved is None:
            raise HTTPException(status_code=404, detail="no view to preview in; choose one")
        view_id = str(resolved)
    known = next((v["id"] for v in delta.views if v.get("id") == view_id), None) or _known_view_id(view_id)
    if known is None:
        raise HTTPException(status_code=404, detail=f"no view with id {view_id!r}")
    try:
        svg = rendering.render_candidate_view(
            known,
            delta.elements,
            delta.relationships,
            delta.views,
            delta.view_membership_edits,
            delta.element_edits,
            delta.element_removals,
            delta.relationship_removals,
        )
    except rendering.ViewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except rendering.PreviewError as exc:
        raise HTTPException(status_code=409, detail=f"cannot preview this change: {exc}") from exc
    # See the matching comment in `get_render`: `render_candidate_view` already
    # sanitizes, but re-sanitizing here keeps the response sink itself responsible
    # for what it serves (CWE-79) -- this is the endpoint where delta content
    # (element/relationship labels proposed via the authoring flow) is most directly
    # user-influenced.
    return Response(content=rendering.sanitize_svg(svg), media_type="image/svg+xml", headers=_svg_headers(known))


@router.get(
    "/sessions/{session_id}/deltas/{delta_id}/state",
    responses={404: {"description": "no applied delta with the given delta_id"}},
)
def get_state(session_id: str, delta_id: str) -> dict[str, Any]:
    """FR-010: the classification recorded at apply time, looked up over the applied
    Candidate Delta itself -- not a separate store (data-model.md)."""
    delta = _store.get_delta(session_id, delta_id)
    if delta is None or delta.status is not DeltaStatus.APPLIED:
        raise HTTPException(status_code=404, detail=f"no applied delta {delta_id!r}")
    return {"applies_to": _first_affected_object_id(delta), "value": delta.state_classification}
