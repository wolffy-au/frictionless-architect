"""Load and evaluate Enterprise Convention Rules (`architecture/model/conventions.yaml`,
FR-003/R6/R13, data-model.md). Element rules and whole-model relationship-shape rules
are checked here; `interposed-pattern` is `patterns.py`'s concern (FR-008).
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

from modelling_specification import model_io

_VALID_KINDS = {
    "naming",
    "altitude",
    "allowed-subset",
    "interposed-pattern",
    "required-neighbour",
    "no-bypass",
    "no-restatement",
}
_DEFAULT_MIN_SHARED_WORDS = 6
CONVENTIONS_PATH = model_io.HERE / "conventions.yaml"


class ConventionRuleError(Exception):
    """A malformed `conventions.yaml` entry -- never silently skipped (FR-007's
    "never silently" posture)."""


def load_rules(path: Path | None = None) -> list[dict[str, Any]]:
    """Load and validate every rule's shape. Raises `ConventionRuleError` naming the
    offending `id` (or the whole entry, if even `id` is missing) rather than skipping
    a malformed entry."""
    path = path if path is not None else CONVENTIONS_PATH
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text()) or []
    if not isinstance(data, list):
        raise ConventionRuleError(f"{path} must be a YAML list of convention rules")
    for entry in data:
        if not isinstance(entry, dict) or "id" not in entry or "kind" not in entry:
            raise ConventionRuleError(f"convention rule missing id/kind: {entry!r}")
        if entry["kind"] not in _VALID_KINDS:
            raise ConventionRuleError(f"{entry['id']}: unknown kind {entry['kind']!r}")
        _validate_relationship_rule(entry)
    return data


def _validate_relationship_rule(rule: dict[str, Any]) -> None:
    if rule["kind"] == "required-neighbour":
        _validate_scoped_neighbour_rule(rule, "required-neighbour")
        _validate_exclude_ids(rule)
    elif rule["kind"] == "no-bypass":
        _validate_no_bypass_params(rule)
    elif rule["kind"] == "no-restatement":
        _validate_scoped_neighbour_rule(rule, "no-restatement")
        _validate_min_shared_words(rule)


def _validate_exclude_ids(rule: dict[str, Any]) -> None:
    params = rule["params"]
    if "exclude_ids" in params and (
        not isinstance(params["exclude_ids"], list) or not all(isinstance(item, str) for item in params["exclude_ids"])
    ):
        raise ConventionRuleError(f"{rule['id']}: exclude_ids must be a list of strings")


def _validate_no_bypass_params(rule: dict[str, Any]) -> None:
    params = rule.get("params")
    if not isinstance(params, dict) or not {"source_type", "intermediary_type"} <= params.keys():
        raise ConventionRuleError(f"{rule['id']}: no-bypass needs source_type and intermediary_type params")
    if not isinstance(params["source_type"], str) or not isinstance(params["intermediary_type"], str):
        raise ConventionRuleError(f"{rule['id']}: source_type and intermediary_type must be strings")


def _validate_min_shared_words(rule: dict[str, Any]) -> None:
    params = rule["params"]
    if "min_shared_words" in params and not isinstance(params["min_shared_words"], int):
        raise ConventionRuleError(f"{rule['id']}: min_shared_words must be an int")


def _validate_scoped_neighbour_rule(rule: dict[str, Any], kind: str) -> None:
    """Shared shape check for `required-neighbour` and `no-restatement`: both need a
    scope list and a `{relationship_type, direction, neighbour_type}` params mapping."""
    params = rule.get("params")
    if (
        not isinstance(rule.get("scope"), list)
        or not all(isinstance(item, str) for item in rule["scope"])
        or not isinstance(params, dict)
    ):
        raise ConventionRuleError(f"{rule['id']}: {kind} needs a scope list and params mapping")
    missing = {"relationship_type", "direction", "neighbour_type"} - params.keys()
    if missing:
        raise ConventionRuleError(f"{rule['id']}: {kind} missing params {sorted(missing)}")
    if not isinstance(params["direction"], str) or params["direction"] not in {"incoming", "outgoing"}:
        raise ConventionRuleError(f"{rule['id']}: direction must be 'incoming' or 'outgoing'")
    if not isinstance(params["relationship_type"], str) or not isinstance(params["neighbour_type"], str):
        raise ConventionRuleError(f"{rule['id']}: relationship_type and neighbour_type must be strings")


def _in_scope(rule: dict[str, Any], element_type: str | None) -> bool:
    scope = rule.get("scope") or []
    return "*" in scope or element_type in scope


def _violation(rule: dict[str, Any], element: dict[str, Any]) -> str | None:
    kind = rule["kind"]
    params = rule.get("params", {})
    if kind == "naming":
        name = str(element.get("name", ""))
        if not re.match(params["pattern"], name):
            return f"name {name!r} does not match the required pattern {params['pattern']!r}"
    elif kind == "altitude":
        text = f"{element.get('name', '')} {element.get('desc', '')}".lower()
        for term in params.get("banned_terms", []):
            if term.lower() in text:
                return f"name/desc contains the banned term {term!r}"
    elif kind == "allowed-subset":
        if element.get("type") not in params.get("allowed_types", []):
            return f"type {element.get('type')!r} is not in the allowed subset {params['allowed_types']!r}"
    return None


def check_elements(elements: list[dict[str, Any]], rules: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Return a `validation_result.findings[]`-shaped entry (FR-004) per violated
    `naming`/`altitude`/`allowed-subset` rule. `rules` defaults to the real
    `conventions.yaml`; tests inject an explicit rule list."""
    rules = rules if rules is not None else load_rules()
    findings: list[dict[str, Any]] = []
    for rule in rules:
        if not rule.get("enabled", True) or rule["kind"] in {
            "interposed-pattern",
            "required-neighbour",
            "no-bypass",
            "no-restatement",
        }:
            continue
        for element in elements:
            if not _in_scope(rule, str(element.get("type", ""))):
                continue
            detail = _violation(rule, element)
            if detail:
                findings.append({"check": rule["id"], "id": element.get("id"), "detail": detail})
    return findings


def check_relationships(
    elements: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    types_by_id: dict[str, str],
    rules: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Validate configured whole-model relationship conventions."""
    rules = rules if rules is not None else load_rules()
    findings: list[str] = []
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        if rule["kind"] == "required-neighbour":
            findings.extend(_check_required_neighbour(rule, elements, relationships, types_by_id))
        elif rule["kind"] == "no-bypass":
            findings.extend(_check_no_bypass(rule, relationships, types_by_id))
        elif rule["kind"] == "no-restatement":
            findings.extend(_check_no_restatement(rule, elements, relationships, types_by_id))
    return findings


def _check_required_neighbour(
    rule: dict[str, Any],
    elements: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    types_by_id: dict[str, str],
) -> list[str]:
    params = rule["params"]
    direction = params["direction"]
    findings: list[str] = []
    excluded_ids = set(params.get("exclude_ids", []))
    for element in elements:
        element_id = element["id"]
        element_type = types_by_id.get(element_id)
        if not _in_scope(rule, element_type):
            continue
        if element_id in excluded_ids or _is_excluded_first_party(rule, element_id):
            continue
        if not any(
            rel["type"] == params["relationship_type"]
            and _has_neighbour(rel, element_id, direction, params["neighbour_type"], types_by_id)
            for rel in relationships
        ):
            findings.append(
                f"{rule['id']}: {element_type} {element_id!r} has no {direction} "
                f"{params['relationship_type']} relationship to {params['neighbour_type']}"
            )
    return findings


def _has_neighbour(
    relationship: dict[str, Any],
    element_id: str,
    direction: str,
    neighbour_type: str,
    types_by_id: dict[str, str],
) -> bool:
    if direction == "outgoing":
        return relationship["source"] == element_id and types_by_id.get(relationship["target"]) == neighbour_type
    return relationship["target"] == element_id and types_by_id.get(relationship["source"]) == neighbour_type


def _check_no_bypass(
    rule: dict[str, Any], relationships: list[dict[str, Any]], types_by_id: dict[str, str]
) -> list[str]:
    params = rule["params"]
    source_type, intermediary_type = params["source_type"], params["intermediary_type"]
    findings: list[str] = []
    for rel in relationships:
        source_id = rel["source"]
        if types_by_id.get(source_id) != source_type or _is_excluded_first_party(rule, source_id):
            continue
        if types_by_id.get(rel["target"]) != intermediary_type:
            findings.append(
                f"{rule['id']}: {source_type} {source_id!r} has a {rel['type']} relationship "
                f"directly to {rel['target']!r}, bypassing {intermediary_type}"
            )
    return findings


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _longest_shared_run(a: list[str], b: list[str]) -> list[str]:
    """The longest contiguous word run common to both token lists (order-preserving,
    not just a shared vocabulary) -- a word-level longest-common-substring."""
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    match = matcher.find_longest_match(0, len(a), 0, len(b))
    return a[match.a : match.a + match.size]


def _matching_neighbour_ids(
    relationships: list[dict[str, Any]],
    element_id: str,
    direction: str,
    relationship_type: str,
    neighbour_type: str,
    types_by_id: dict[str, str],
) -> Iterator[str]:
    """Ids of neighbours related to `element_id` by a `relationship_type` relationship
    matching `direction`/`neighbour_type` (the generator form of `_has_neighbour`)."""
    for rel in relationships:
        if rel["type"] == relationship_type and _has_neighbour(rel, element_id, direction, neighbour_type, types_by_id):
            yield rel["target"] if direction == "outgoing" else rel["source"]


def _neighbour_restatement(
    rule: dict[str, Any],
    element_id: str,
    element_type: str | None,
    element_words: list[str],
    neighbour: dict[str, Any],
    neighbour_id: str,
    min_shared_words: int,
) -> str | None:
    """A finding string if `neighbour`'s `desc` shares `min_shared_words`+ verbatim
    words with `element_words`, else `None`."""
    shared = _longest_shared_run(element_words, _tokenize(str(neighbour.get("desc", ""))))
    if len(shared) < min_shared_words:
        return None
    return (
        f"{rule['id']}: {element_type} {element_id!r} restates {min_shared_words}+ words verbatim "
        f"from {rule['params']['neighbour_type']} {neighbour_id!r}: {' '.join(shared)!r}"
    )


def _check_no_restatement(
    rule: dict[str, Any],
    elements: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    types_by_id: dict[str, str],
) -> list[str]:
    """Flag an element whose `desc` shares a long verbatim run with the `desc` of a
    neighbour it's related to (e.g. a Requirement restating the Outcome it realizes
    instead of stating the capability-level contract that delivers it)."""
    params = rule["params"]
    direction = params["direction"]
    min_shared_words = params.get("min_shared_words", _DEFAULT_MIN_SHARED_WORDS)
    by_id = {element["id"]: element for element in elements}
    findings: list[str] = []
    for element in elements:
        element_id = element["id"]
        element_type = types_by_id.get(element_id)
        if not _in_scope(rule, element_type) or _is_excluded_first_party(rule, element_id):
            continue
        element_words = _tokenize(str(element.get("desc", "")))
        if not element_words:
            continue
        for neighbour_id in _matching_neighbour_ids(
            relationships, element_id, direction, params["relationship_type"], params["neighbour_type"], types_by_id
        ):
            finding = _neighbour_restatement(
                rule,
                element_id,
                element_type,
                element_words,
                by_id.get(neighbour_id, {}),
                neighbour_id,
                min_shared_words,
            )
            if finding:
                findings.append(finding)
    return findings


def _is_excluded_first_party(rule: dict[str, Any], element_id: str) -> bool:
    return bool(rule["params"].get("first_party_only")) and element_id.startswith("it4it-")
