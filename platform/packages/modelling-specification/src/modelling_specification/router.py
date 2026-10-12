"""FastAPI router for conversational model authoring (ADR-0020). Mounted into `app.py`.

`decide`/`render`/`config`/`state` land in later phases per contracts/api.md.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from modelling_specification import model_io, rendering
from modelling_specification.authoring import overrides
from modelling_specification.authoring.delta import (
    DeltaProposalError,
    LlmMessage,
    assign_missing_ids,
    propose_delta,
    resolve_unknown_endpoints,
)
from modelling_specification.authoring.state import CandidateDelta, DeltaStatus, SessionStore
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
    request: str


class DecideRequest(BaseModel):
    action: str
    rationale: str | None = None
    duplicate_decision: str | None = None
    target_existing_id: str | None = None
    state_classification: str | None = None


class ConfigRequest(BaseModel):
    auto_render: bool


@router.post("/sessions")
def create_session() -> dict[str, str]:
    return {"session_id": _store.create_session()}


def _delta_response(delta: CandidateDelta) -> dict[str, Any]:
    return {
        "delta_id": delta.delta_id,
        "status": delta.status.value,
        "elements": delta.elements,
        "relationships": delta.relationships,
        "validation_result": delta.validation_result,
        "duplicates": delta.duplicates,
        "pattern_suggestions": delta.pattern_suggestions,
    }


@router.post("/sessions/{session_id}/propose")
def propose(session_id: str, body: ProposeRequest) -> dict[str, Any]:
    if _store.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail=f"no session {session_id!r}")

    existing, types_by_id = model_io.existing_elements_and_types()
    catalogue = [
        (e["id"], types_by_id[e["id"]], str(e.get("name", ""))) for e in existing if e.get("id") in types_by_id
    ]
    try:
        proposed = propose_delta(body.request, catalogue)
    except LlmMessage as message:
        return {"delta_id": None, "status": "message", "message": message.text, "elements": [], "relationships": []}
    except DeltaProposalError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    new_elements = assign_missing_ids(proposed["elements"], model_io.existing_element_ids())
    delta = _store.pending_delta(session_id)
    in_flight = [*(delta.elements if delta else []), *new_elements]
    known_names = {eid: name for eid, _etype, name in catalogue}
    known_names.update({e["id"]: str(e.get("name", "")) for e in in_flight if e.get("id")})
    new_relationships, notes = resolve_unknown_endpoints(proposed["relationships"], known_names)

    if delta is None:
        delta = CandidateDelta(delta_id=_store.new_delta_id(), session_id=session_id)
        _store.add_delta(session_id, delta)
    # FR-015: a later request touching the pending delta amends/extends it rather
    # than starting an independent one -- one accumulating delta per conversation
    # until it is applied or discarded (data-model.md Candidate Delta lifecycle).
    delta.elements = delta.elements + new_elements
    delta.relationships = delta.relationships + new_relationships

    _validate_and_flag(delta)
    response = _delta_response(delta)
    if not delta.elements and not delta.relationships:
        notes.append(
            "No change was proposed. This feature can only add elements and relationships; "
            "it cannot edit, rename or remove existing ones."
        )
    if notes:
        response["notes"] = notes
    return response


def _delta_element_types(elements: list[dict[str, Any]]) -> dict[str, str]:
    types: dict[str, str] = {}
    for e in elements:
        eid = e.get("id")
        t = model_io.canon(str(e.get("type", "")), [], "delta element") if eid else None
        if eid and t:
            types[eid] = t
    return types


def _validate_and_flag(delta: CandidateDelta) -> None:
    """Run every check (FR-002/003/005/008) against the whole accumulated delta and
    set `validation_result`/`duplicates`/`pattern_suggestions`/`status`."""
    metamodel_result = validate_metamodel(delta.elements, delta.relationships)
    rules = conventions.load_rules()
    convention_findings = conventions.check_elements(delta.elements, rules)
    findings = metamodel_result["findings"] + convention_findings
    rules_by_id = {r["id"]: r for r in rules}
    for finding in findings:
        finding["proposed_fix"] = proposed_fix_for_finding(finding, rules_by_id)
    delta.validation_result = {"clean": not findings, "findings": findings}

    delta.duplicates = find_duplicates(delta.elements)

    types_by_id = {**model_io.existing_element_types(), **_delta_element_types(delta.elements)}
    delta.pattern_suggestions = find_pattern_suggestions(delta.relationships, types_by_id, rules)

    if delta.validation_result["clean"] and not delta.duplicates and not delta.pattern_suggestions:
        delta.status = DeltaStatus.VALIDATED
    else:
        delta.status = DeltaStatus.FLAGGED


@router.post("/sessions/{session_id}/deltas/{delta_id}/decide")
def decide(session_id: str, delta_id: str, body: DecideRequest) -> Any:
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


def _apply_and_respond(delta: CandidateDelta, state_classification: str | None) -> dict[str, Any]:
    model_io.append_delta(delta.elements, delta.relationships)
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
    model_io.append_delta(delta.elements, delta.relationships)
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
    return dict(_config)


@router.put("/config")
def put_config(body: ConfigRequest) -> dict[str, bool]:
    _config["auto_render"] = body.auto_render
    return dict(_config)


def _first_affected_object_id(delta: CandidateDelta) -> str | None:
    """A representative id for the delta's "affected element(s)" (FR-012): the first
    new element if any, else the first new relationship's target -- a delta that only
    adds an edge between existing elements still has an affected object to render."""
    if delta.elements:
        return delta.elements[0].get("id")
    if delta.relationships:
        return delta.relationships[0].get("target")
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


@router.get("/render")
def get_render(
    object_id: str | None = None,
    description: str | None = None,
    output_format: Literal["json", "svg"] = Query(default="json", alias="format"),
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
        return Response(
            content=svg,
            media_type="image/svg+xml",
            headers=_svg_headers(known),
        )
    return {
        "view_id": resolution["resolved_view_id"],
        "svg": svg,
    }


@router.get("/sessions/{session_id}/deltas/{delta_id}/preview")
def get_preview(session_id: str, delta_id: str, view_id: str | None = None) -> Response:
    """Render a pending delta in a view *before* anything is written (nothing is
    persisted). Without `view_id`, the view is resolved from an existing element the
    delta touches; ambiguity or no match is reported like `GET /render`."""
    delta = _store.get_delta(session_id, delta_id)
    if delta is None or delta.status in (DeltaStatus.APPLIED, DeltaStatus.DISCARDED):
        raise HTTPException(status_code=404, detail=f"no pending delta {delta_id!r}")
    if not delta.elements and not delta.relationships:
        raise HTTPException(status_code=409, detail="the delta is empty; there is nothing to preview")
    if view_id is None:
        existing = model_io.existing_element_ids()
        touched = [e for r in delta.relationships for e in (r.get("source"), r.get("target")) if e in existing]
        resolution = rendering.resolve_view_request(touched[0] if touched else None, None)
        if resolution["ambiguous_candidates"]:
            return JSONResponse(status_code=300, content={"ambiguous_candidates": resolution["ambiguous_candidates"]})
        resolved = resolution["resolved_view_id"]
        if resolved is None:
            raise HTTPException(status_code=404, detail="no view to preview in; choose one")
        view_id = str(resolved)
    known = _known_view_id(view_id)
    if known is None:
        raise HTTPException(status_code=404, detail=f"no view with id {view_id!r}")
    try:
        svg = rendering.render_candidate_view(known, delta.elements, delta.relationships)
    except rendering.ViewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except rendering.PreviewError as exc:
        raise HTTPException(status_code=409, detail=f"cannot preview this change: {exc}") from exc
    return Response(content=svg, media_type="image/svg+xml", headers=_svg_headers(known))


@router.get("/sessions/{session_id}/deltas/{delta_id}/state")
def get_state(session_id: str, delta_id: str) -> dict[str, Any]:
    """FR-010: the classification recorded at apply time, looked up over the applied
    Candidate Delta itself -- not a separate store (data-model.md)."""
    delta = _store.get_delta(session_id, delta_id)
    if delta is None or delta.status is not DeltaStatus.APPLIED:
        raise HTTPException(status_code=404, detail=f"no applied delta {delta_id!r}")
    return {"applies_to": _first_affected_object_id(delta), "value": delta.state_classification}
