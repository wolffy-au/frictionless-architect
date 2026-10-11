"""Flag a proposed direct relationship that matches an established interposed-
element pattern (FR-008): `conventions.yaml`'s `interposed-pattern` rules
(R6). When no rule matches the proposed shape, nothing is raised -- the absence of a
pattern is not itself grounds to flag (Edge Case 4, data-model.md Invariant 4).

Also synthesizes the intermediary form on `accept-pattern` (2026-10-11 clarify):
the agent builds the intermediary element(s) and the two-leg relationship chain
itself, rather than discarding the candidate and asking the architect to re-describe
it -- router.py's `_accept_pattern` is the only caller of `synthesize_intermediaries`.
"""

from __future__ import annotations

import re
from typing import Any

from modelling_specification.authoring.delta import assign_missing_ids
from modelling_specification.validation import conventions


def find_pattern_suggestions(
    relationships: list[dict[str, Any]],
    types_by_id: dict[str, str],
    rules: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """`rules` defaults to the real `conventions.yaml`; tests inject an explicit list."""
    rules = rules if rules is not None else conventions.load_rules()
    interposed = [r for r in rules if r.get("kind") == "interposed-pattern" and r.get("enabled", True)]

    suggestions: list[dict[str, Any]] = []
    for rel in relationships:
        source_type = types_by_id.get(rel.get("source", ""))
        target_type = types_by_id.get(rel.get("target", ""))
        if source_type is None or target_type is None:
            continue
        for rule in interposed:
            params = rule["params"]
            if (
                rel.get("type") == params["relationship_type"]
                and source_type == params["source_type"]
                and target_type == params["target_type"]
            ):
                suggestions.append(
                    {
                        "proposed_relationship": {
                            "type": rel["type"],
                            "source": rel["source"],
                            "target": rel["target"],
                        },
                        "established_pattern": {
                            "intermediary_types": params["intermediary_types"],
                            "target_relationship_type": params["target_relationship_type"],
                        },
                        "decision": None,
                    }
                )
    return suggestions


def _humanize_type(archimate_type: str) -> str:
    """`ApplicationService` -> `Application Service`, for a synthesized element's
    auto-generated name."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", archimate_type)


def synthesize_intermediaries(
    suggestion: dict[str, Any], name_by_id: dict[str, str], existing_ids: set[str]
) -> dict[str, list[dict[str, Any]]]:
    """Build the intermediary element(s) `suggestion["established_pattern"]` implies
    and the relationship chain that replaces the original direct relationship:
    `source --[direct type]--> intermediary_1 --[direct type]--> ... -->
    intermediary_n --[target_relationship_type]--> target`. The direct relationship's
    own type is reused for every source-to-intermediary leg (the real
    `conv-interposed-neo4j-volume` precedent: `sw-neo4j --Assignment--> art-tech-
    neo4j-volume`, the same `Assignment` as the discouraged direct form); only the
    final, intermediary-to-target leg gets the rule's own `target_relationship_type`
    (`...--Realization--> store-akg` in that precedent). Returns new elements/
    relationships only -- the caller splices them into the Candidate Delta in place
    of the matched direct relationship (FR-008, 2026-10-11 clarify)."""
    proposed = suggestion["proposed_relationship"]
    established = suggestion["established_pattern"]
    direct_type = proposed["type"]
    source_id, target_id = proposed["source"], proposed["target"]
    source_name = name_by_id.get(source_id, source_id)

    used_ids = set(existing_ids)
    new_elements: list[dict[str, Any]] = []
    chain_ids = [source_id]
    for intermediary_type in established["intermediary_types"]:
        name = f"{source_name} {_humanize_type(intermediary_type)}"
        (element,) = assign_missing_ids([{"type": intermediary_type, "name": name}], used_ids)
        new_elements.append(element)
        used_ids.add(element["id"])
        chain_ids.append(element["id"])
    chain_ids.append(target_id)

    new_relationships = [
        {
            "type": established["target_relationship_type"] if i == len(chain_ids) - 2 else direct_type,
            "source": chain_ids[i],
            "target": chain_ids[i + 1],
        }
        for i in range(len(chain_ids) - 1)
    ]
    return {"elements": new_elements, "relationships": new_relationships}
