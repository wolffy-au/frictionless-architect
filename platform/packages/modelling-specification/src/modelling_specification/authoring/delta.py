"""Turn an architect's natural-language request into a structured candidate delta
(FR-001), via `llm-provider-config`/`litellm` (ADR-0034, R4), component
`modelling-specification.conversational-authoring`. Mirrors
`controls-compliance-catalog.llm_client`'s own seam (same pattern, no new credential
path, plan.md Security). The request is scrubbed of PII/PHI before the LLM call
(ADR-0014, pii-gateway FR-007).
"""

from __future__ import annotations

import difflib
import json
import logging
import re
from typing import Any

from litellm import completion
from llm_provider_config import MissingCredentialError, NotConfiguredError, resolve_call
from pii_gateway import PendingConfirmation, ScrubAction, scrub

logger = logging.getLogger(__name__)

COMPONENT_ID = "modelling-specification.conversational-authoring"

SYSTEM_PROMPT = """You turn an enterprise/solution architect's natural-language request into a
candidate ArchiMate model delta. Respond with JSON only, no prose, shaped exactly as:

{"elements": [{"type": "<ArchiMate 3.2 concept, e.g. ApplicationFunction>", "id": "<optional stable id>", "name": "<name>", "desc": "<optional description>"}],
 "relationships": [{"type": "<ArchiMate 3.2 relationship, e.g. Serving>", "source": "<element id>", "target": "<element id>", "label": "<optional>"}]}

Both "elements" and "relationships" are required keys, each a (possibly empty) list.
Only describe the new or changed elements/relationships the request asks for; refer to
elements already in the model by their existing id in "source"/"target" rather than
redeclaring them. The existing elements are listed below as "id | type | name": match what
the architect names to the closest element, even when they misspell it or give only part of
its name, and copy that id exactly. Never invent an id for an element that already exists.

If the architect instead asks for a way forward -- "what should I do about X", "suggest
options for Y", "how should I evolve Z" -- rather than describing one concrete change,
reply with JSON shaped exactly as:

{"options": [{"rationale": "<why this option, citing specific existing element ids and/or convention rule ids>",
              "convention_refs": ["<rule id from the list below, if any grounded this option>"],
              "elements": [...], "relationships": [...]}]}

Give 2-3 distinct options, each a complete, independently applicable candidate delta in the
same "elements"/"relationships" shape as above. Ground each rationale in the existing
elements and, where relevant, the enterprise convention rules listed below -- cite their
ids rather than describing them vaguely. Never invent a rule id that isn't listed.

If the request is a factual question about the model itself or its own vocabulary --
for example "what are my choices for context", "what contexts exist", "what tags/props
can I put on an element", "what element types are allowed", "what views/viewpoints are
available", "what standard ArchiMate views do I have" -- answer it directly in plain
text from the "Existing contexts", "Existing elements" and "Existing views" data given
below (and the ArchiMate 3.2 concept names for element/relationship types). This is not
a clarifying question: answer from the data you were given rather than asking the
architect to clarify a question that data already answers.

The same applies to a factual question about the model's connection graph -- for
example "what connects to this element", "is this element orphaned", "what capability
does X realize", "trace this element up to a stakeholder", "which elements mirror X's
structure on another path through the model" -- answer it by tracing the "Existing
relationships" data given below (each line is `type | source id | target id | label`;
resolve ids to names via "Existing elements"). Walk the graph as far as the question
needs -- multiple hops, either direction -- and show the chain of ids/names and
relationship types you followed, not just the endpoint. If the data given doesn't
contain a path that answers the question, say so plainly rather than guessing one.

If the request is too vague to form even one concrete option -- missing the subject,
scope, or enough detail to propose anything concrete -- reply with a short
plain-text message instead of JSON: one clarifying question for the architect to answer.

You can only ADD elements and relationships. If the request asks to rename, edit or remove
something that already exists, return {"elements": [], "relationships": []} rather than
re-declaring the existing element."""

# Models often wrap JSON output in a single ```json fence despite being told not to.
_SURROUNDING_FENCE = re.compile(r"\A\s*```[A-Za-z]*\n(.*?)\n```\s*\Z", re.DOTALL)


class DeltaProposalError(Exception):
    """Raised when the LLM call fails or returns an unparseable delta (contracts/api.md 502)."""


class LlmMessage(Exception):
    """The LLM answered in plain text instead of a delta -- a clarifying question or a
    suggestion (FR-001: ask, don't guess). Carries the text to show the architect; no
    Candidate Delta is created."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


class PiiReviewRequired(Exception):
    """`scrub()` flagged a PII/PHI match in the architect's request for review
    (ADR-0014 amendment, `conversational-authoring` context) rather than
    auto-redacting -- the LLM call must NOT proceed yet. Carries the
    `PendingConfirmation` the caller resolves (via `pii_gateway.Resolution`) before
    retrying with `resume_proposal()`. No Candidate Delta is created."""

    def __init__(self, pending_confirmation: PendingConfirmation) -> None:
        super().__init__("a PII/PHI match in the request needs the architect's review before the LLM call proceeds")
        self.pending_confirmation = pending_confirmation
        self.matches = pending_confirmation.matches


def _message_content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    message = getattr(choices[0], "message", None) if choices else None
    content = getattr(message, "content", None)
    return content if isinstance(content, str) else ""


def _catalogue_text(catalogue: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"{eid} | {etype} | {name}" for eid, etype, name in catalogue)


def _rules_text(rules: list[dict[str, Any]]) -> str:
    return "\n".join(f"{r['id']} | {r['kind']} | scope={r.get('scope', [])}" for r in rules)


def _contexts_text(contexts: list[str]) -> str:
    return "\n".join(sorted(contexts))


def _views_text(views: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"{vid} | {name} | viewpoint={viewpoint or 'custom'}" for vid, name, viewpoint in views)


def _relationships_text(relationships: list[tuple[str, str, str, str]]) -> str:
    return "\n".join(f"{rtype} | {source} | {target} | {label}" for rtype, source, target, label in relationships)


def _grounded_system_prompt(
    catalogue: list[tuple[str, str, str]] | None,
    contexts: list[str] | None,
    views: list[tuple[str, str, str]] | None,
    relationships: list[tuple[str, str, str, str]] | None,
    rules: list[dict[str, Any]] | None,
) -> str:
    """`SYSTEM_PROMPT` plus one labelled block per non-empty grounding input, in a
    fixed order -- factored out of `propose_delta` to keep its own branching under
    the complexity gate; each block is independently optional, so a caller can pass
    only the data it has."""
    blocks = [
        ("Existing elements", catalogue, _catalogue_text),
        ("Existing contexts", contexts, _contexts_text),
        ("Existing views", views, _views_text),
        ("Existing relationships", relationships, _relationships_text),
        ("Enterprise convention rules", rules, _rules_text),
    ]
    system = SYSTEM_PROMPT
    for label, data, render in blocks:
        if data:
            system += f"\n\n{label}:\n{render(data)}"
    return system


def _is_single_delta(payload: Any) -> bool:
    return isinstance(payload.get("elements"), list) and isinstance(payload.get("relationships"), list)


def _normalize_option(option: Any, model: str) -> dict[str, Any]:
    if (
        not isinstance(option, dict)
        or not isinstance(option.get("elements"), list)
        or not isinstance(option.get("relationships"), list)
    ):
        raise DeltaProposalError(
            f"The LLM returned an option missing the required 'elements'/'relationships' lists ({model})."
        )
    rationale = option.get("rationale")
    convention_refs = option.get("convention_refs")
    return {
        "rationale": rationale if isinstance(rationale, str) else "",
        "convention_refs": convention_refs if isinstance(convention_refs, list) else [],
        "elements": option["elements"],
        "relationships": option["relationships"],
    }


def propose_delta(
    request: str,
    catalogue: list[tuple[str, str, str]] | None = None,
    rules: list[dict[str, Any]] | None = None,
    contexts: list[str] | None = None,
    views: list[tuple[str, str, str]] | None = None,
    relationships: list[tuple[str, str, str, str]] | None = None,
) -> dict[str, Any]:
    """Call the configured LLM and return a candidate delta, in one of two shapes:
    a single concrete change, `{"elements": [...], "relationships": [...]}`; or, when
    the architect asked for a way forward rather than describing one change,
    `{"options": [{"rationale": ..., "convention_refs": [...], "elements": [...],
    "relationships": [...]}, ...]}` -- 2-3 alternatives, each independently a
    complete candidate delta (FR-001, "suggests ways forward" per GH #68).

    A factual question about the model's own vocabulary (e.g. "what are my choices
    for context", "what views/viewpoints are available") or its connection graph
    (e.g. "what connects to this element", "what capability does X realize", "trace
    this up to a stakeholder") is answered in plain text from
    `catalogue`/`contexts`/`rules`/`views`/`relationships` via the `LlmMessage` path
    below, same as a clarifying question.

    Raises `DeltaProposalError` for every way this can fail short of one of those
    shapes: no provider configured, no credential, the call itself failing, an empty
    response, or a response that is not the required JSON shape. None of these create
    a Candidate Delta -- the caller (router.py) maps this to a 502 with no write.

    Raises `PiiReviewRequired` when `scrub()` flags a PII/PHI match in `request` for
    the architect's review (ADR-0014 amendment) -- the LLM call is NOT made; the
    caller must resolve the flagged match (via `pii_gateway.Resolution`) and retry
    with `resume_proposal()`."""
    stripped = request.strip()
    if not stripped:
        raise DeltaProposalError("Cannot propose a delta from an empty request.")

    return resume_proposal(scrub_or_require_review(stripped), catalogue, rules, contexts, views, relationships)


def scrub_or_require_review(text: str) -> str:
    """Scrub `text` under the `conversational-authoring` context (ADR-0014
    amendment) and return the text to proceed with, or raise `PiiReviewRequired`
    if a match was flagged rather than auto-redacted.

    Used both by `propose_delta`'s own first pass and by the router's
    `resolve-pii` `edit` path: an architect-supplied replacement string is NOT
    assumed clean -- it is re-scrubbed exactly like any other request text, so a
    still-sensitive edit is re-flagged rather than ever reaching the LLM call
    unscrubbed (never auto-escalated to a different behaviour; the caller sees
    the same `pii_review_required` shape as a fresh `propose` would)."""
    result = scrub(text, context="conversational-authoring")
    if result.action == ScrubAction.FLAGGED_FOR_REVIEW:
        if result.pending_confirmation is None:  # pragma: no cover - scrub() always sets this when flagged
            raise DeltaProposalError("PII/PHI was flagged for review but no confirmation handle was returned.")
        raise PiiReviewRequired(result.pending_confirmation)
    return result.text


def resume_proposal(
    resolved_text: str,
    catalogue: list[tuple[str, str, str]] | None = None,
    rules: list[dict[str, Any]] | None = None,
    contexts: list[str] | None = None,
    views: list[tuple[str, str, str]] | None = None,
    relationships: list[tuple[str, str, str, str]] | None = None,
) -> dict[str, Any]:
    """Make the LLM call with text that has already been scrubbed or explicitly
    resolved by the architect (a `PiiReviewRequired` match the caller resolved via
    `pii_gateway.Resolution`, or `propose_delta`'s own non-flagged `scrub()` output).
    Never re-scrubs -- callers decide separately whether `resolved_text` still needs
    scrubbing. Same return shape and error behaviour as `propose_delta`."""
    try:
        call = resolve_call(COMPONENT_ID)
    except (NotConfiguredError, MissingCredentialError) as exc:
        raise DeltaProposalError(str(exc)) from exc

    system = _grounded_system_prompt(catalogue, contexts, views, relationships, rules)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": resolved_text}]
    try:
        response = completion(messages=messages, **call.completion_kwargs())
    except Exception as exc:  # noqa: BLE001 - litellm raises a wide family of provider/network errors
        # The router returns this message in the 502 body, so keep provider detail in
        # the server log only (CWE-209).
        logger.warning("LLM call to %s failed", call.model, exc_info=True)
        raise DeltaProposalError(f"The LLM call failed ({call.model}); see the server log for details.") from exc

    content = _message_content(response).strip()
    if not content:
        raise DeltaProposalError(f"The LLM returned an empty response ({call.model}).")

    fenced = _SURROUNDING_FENCE.match(content)
    text = fenced.group(1) if fenced else content
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LlmMessage(content) from exc

    return _parsed_proposal(payload, call.model)


def _parsed_proposal(payload: Any, model: str) -> dict[str, Any]:
    """`payload` must be a single delta or an "options" list (see `propose_delta`);
    anything else is a `DeltaProposalError` naming the model that returned it."""
    if isinstance(payload, dict) and _is_single_delta(payload):
        return {"elements": payload["elements"], "relationships": payload["relationships"]}

    if isinstance(payload, dict) and isinstance(payload.get("options"), list) and payload["options"]:
        return {"options": [_normalize_option(o, model) for o in payload["options"]]}

    raise DeltaProposalError(f"The LLM response is missing the required 'elements'/'relationships' lists ({model}).")


def _closest_known_id(wanted: str, names_by_id: dict[str, str]) -> str | None:
    """The one known element whose id or name is clearly closest to `wanted`, else
    `None` -- ambiguous or weak matches are left alone for validation to reject."""
    needle = wanted.lower()
    scored = sorted(
        (
            (
                max(
                    difflib.SequenceMatcher(None, needle, eid.lower()).ratio(),
                    difflib.SequenceMatcher(None, needle, name.lower()).ratio(),
                ),
                eid,
            )
            for eid, name in names_by_id.items()
        ),
        reverse=True,
    )
    if not scored or scored[0][0] < 0.7 or (len(scored) > 1 and scored[1][0] > scored[0][0] - 0.1):
        return None
    return scored[0][1]


def resolve_unknown_endpoints(
    relationships: list[dict[str, Any]], names_by_id: dict[str, str]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Repoint a relationship endpoint that names no known element (a misspelt or
    half-remembered id from the LLM) at its unambiguous nearest match, returning the
    corrected relationships and one human-readable note per correction. Nothing is
    written until the architect applies the delta, so every correction is reviewable."""
    notes: list[str] = []
    resolved: list[dict[str, Any]] = []
    for rel in relationships:
        fixed = dict(rel)
        for end in ("source", "target"):
            wanted = fixed.get(end)
            if isinstance(wanted, str) and wanted not in names_by_id:
                match = _closest_known_id(wanted, names_by_id)
                if match is not None:
                    notes.append(f"{end} {wanted!r} is not an element; using {match!r} ({names_by_id[match]})")
                    fixed[end] = match
        resolved.append(fixed)
    return resolved, notes


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "element"


def assign_missing_ids(elements: list[dict[str, Any]], existing_ids: set[str]) -> list[dict[str, Any]]:
    """Assign a stable id to any delta element missing one (data-model.md: "id absent
    until the LLM proposes one or validation assigns one") -- `<type>-<slugified
    name>`, de-duplicated against `existing_ids` (ids already on disk) and ids already
    assigned earlier in this same call. Elements that already carry an id pass through
    unchanged."""
    used = set(existing_ids)
    assigned: list[dict[str, Any]] = []
    for e in elements:
        if e.get("id"):
            used.add(e["id"])
            assigned.append(e)
            continue
        base = f"{str(e.get('type', 'element')).lower()}-{_slugify(str(e.get('name', '')))}"
        candidate, n = base, 2
        while candidate in used:
            candidate = f"{base}-{n}"
            n += 1
        used.add(candidate)
        assigned.append({**e, "id": candidate})
    return assigned
