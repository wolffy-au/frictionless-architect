"""Turn an architect's natural-language request into a structured candidate delta
(FR-001), via `llm-provider-config`/`litellm` (ADR-0034, R4), component
`modelling-specification.conversational-authoring`. Mirrors
`controls-compliance-catalog.llm_client`'s own seam (same pattern, no new credential
path, plan.md Security).
"""

from __future__ import annotations

import difflib
import json
import re
from typing import Any

from litellm import completion
from llm_provider_config import MissingCredentialError, NotConfiguredError, resolve_call

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

You can only ADD elements and relationships. If the request asks to rename, edit or remove
something that already exists, return {"elements": [], "relationships": []} rather than
re-declaring the existing element."""

# Models often wrap JSON output in a single ```json fence despite being told not to.
_SURROUNDING_FENCE = re.compile(r"\A\s*```[A-Za-z]*\n(.*?)\n```\s*\Z", re.DOTALL)


class DeltaProposalError(Exception):
    """Raised when the LLM call fails or returns an unparseable delta (contracts/api.md 502)."""


def _message_content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    message = getattr(choices[0], "message", None) if choices else None
    content = getattr(message, "content", None)
    return content if isinstance(content, str) else ""


def _catalogue_text(catalogue: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"{eid} | {etype} | {name}" for eid, etype, name in catalogue)


def propose_delta(request: str, catalogue: list[tuple[str, str, str]] | None = None) -> dict[str, list[dict[str, Any]]]:
    """Call the configured LLM and return `{"elements": [...], "relationships": [...]}`.

    Raises `DeltaProposalError` for every way this can fail short of a well-formed
    delta: no provider configured, no credential, the call itself failing, an empty
    response, or a response that is not the required JSON shape. None of these create
    a Candidate Delta -- the caller (router.py) maps this to a 502 with no write."""
    stripped = request.strip()
    if not stripped:
        raise DeltaProposalError("Cannot propose a delta from an empty request.")

    try:
        call = resolve_call(COMPONENT_ID)
    except (NotConfiguredError, MissingCredentialError) as exc:
        raise DeltaProposalError(str(exc)) from exc

    system = SYSTEM_PROMPT + (f"\n\nExisting elements:\n{_catalogue_text(catalogue)}" if catalogue else "")
    messages = [{"role": "system", "content": system}, {"role": "user", "content": stripped}]
    try:
        response = completion(messages=messages, **call.completion_kwargs())
    except Exception as exc:  # noqa: BLE001 - litellm raises a wide family of provider/network errors
        raise DeltaProposalError(f"The LLM call failed ({call.model}): {exc}") from exc

    content = _message_content(response).strip()
    if not content:
        raise DeltaProposalError(f"The LLM returned an empty response ({call.model}).")

    fenced = _SURROUNDING_FENCE.match(content)
    text = fenced.group(1) if fenced else content
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DeltaProposalError(f"The LLM returned unparseable JSON ({call.model}): {exc}") from exc

    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("elements"), list)
        or not isinstance(payload.get("relationships"), list)
    ):
        raise DeltaProposalError(
            f"The LLM response is missing the required 'elements'/'relationships' lists ({call.model})."
        )

    return {"elements": payload["elements"], "relationships": payload["relationships"]}


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
