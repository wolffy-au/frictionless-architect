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
from pii_gateway import scrub

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


def _message_content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    message = getattr(choices[0], "message", None) if choices else None
    content = getattr(message, "content", None)
    return content if isinstance(content, str) else ""


def _catalogue_text(catalogue: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"{eid} | {etype} | {name}" for eid, etype, name in catalogue)


def _rules_text(rules: list[dict[str, Any]]) -> str:
    return "\n".join(f"{r['id']} | {r['kind']} | scope={r.get('scope', [])}" for r in rules)


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
) -> dict[str, Any]:
    """Call the configured LLM and return a candidate delta, in one of two shapes:
    a single concrete change, `{"elements": [...], "relationships": [...]}`; or, when
    the architect asked for a way forward rather than describing one change,
    `{"options": [{"rationale": ..., "convention_refs": [...], "elements": [...],
    "relationships": [...]}, ...]}` -- 2-3 alternatives, each independently a
    complete candidate delta (FR-001, "suggests ways forward" per GH #68).

    Raises `DeltaProposalError` for every way this can fail short of one of those
    shapes: no provider configured, no credential, the call itself failing, an empty
    response, or a response that is not the required JSON shape. None of these create
    a Candidate Delta -- the caller (router.py) maps this to a 502 with no write."""
    stripped = request.strip()
    if not stripped:
        raise DeltaProposalError("Cannot propose a delta from an empty request.")

    scrubbed = scrub(stripped, context="spec-generator").text

    try:
        call = resolve_call(COMPONENT_ID)
    except (NotConfiguredError, MissingCredentialError) as exc:
        raise DeltaProposalError(str(exc)) from exc

    system = SYSTEM_PROMPT
    if catalogue:
        system += f"\n\nExisting elements:\n{_catalogue_text(catalogue)}"
    if rules:
        system += f"\n\nEnterprise convention rules:\n{_rules_text(rules)}"
    messages = [{"role": "system", "content": system}, {"role": "user", "content": scrubbed}]
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
