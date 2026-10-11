"""Load and evaluate Enterprise Convention Rules (`architecture/model/conventions.yaml`,
FR-003/R6/R13, data-model.md). The generic `naming`/`altitude`/`allowed-subset` kinds
are checked here; `interposed-pattern` is `patterns.py`'s concern (FR-008) -- this
module skips those entries rather than evaluating them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from modelling_specification import model_io

_VALID_KINDS = {"naming", "altitude", "allowed-subset", "interposed-pattern"}
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
        if "id" not in entry or "kind" not in entry:
            raise ConventionRuleError(f"convention rule missing id/kind: {entry!r}")
        if entry["kind"] not in _VALID_KINDS:
            raise ConventionRuleError(f"{entry['id']}: unknown kind {entry['kind']!r}")
    return data


def _in_scope(rule: dict[str, Any], element_type: str) -> bool:
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
        if not rule.get("enabled", True) or rule["kind"] == "interposed-pattern":
            continue
        for element in elements:
            if not _in_scope(rule, str(element.get("type", ""))):
                continue
            detail = _violation(rule, element)
            if detail:
                findings.append({"check": rule["id"], "id": element.get("id"), "detail": detail})
    return findings
