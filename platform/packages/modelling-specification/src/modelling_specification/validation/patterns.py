"""Flag a proposed direct relationship that matches an established interposed-
element pattern (FR-008): `conventions.yaml`'s `interposed-pattern` rules
(R6). When no rule matches the proposed shape, nothing is raised -- the absence of a
pattern is not itself grounds to flag (Edge Case 4, data-model.md Invariant 4).
"""

from __future__ import annotations

from typing import Any

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
                        "established_pattern": {"intermediary_types": params["intermediary_types"]},
                        "decision": None,
                    }
                )
    return suggestions
