"""`architecture/model/conventions.yaml` round-trips through `yaml.safe_load`/`safe_dump`
with no information loss (data-model.md Invariant 5). The dedicated `conventions.py`
loader that enforces "a malformed entry fails naming the offending `id`" (FR-007) is
Phase 4/US2 scope (T041) -- this only guards the file's own shape and round-trip."""

from __future__ import annotations

import yaml
from modelling_specification.model_io import REPO_ROOT

CONVENTIONS = REPO_ROOT / "architecture" / "model" / "conventions.yaml"

REQUIRED_FIELDS = {"id", "kind", "scope", "params", "enabled"}
VALID_KINDS = {
    "naming",
    "altitude",
    "allowed-subset",
    "interposed-pattern",
    "required-neighbour",
    "no-bypass",
    "no-restatement",
}


def _load() -> list[dict[str, object]]:
    return yaml.safe_load(CONVENTIONS.read_text()) or []


def test_conventions_file_is_a_list_of_rules() -> None:
    rules = _load()
    assert isinstance(rules, list)
    assert rules, "expected at least the seeded interposed-pattern rule"


def test_every_rule_has_the_required_fields_and_a_known_kind() -> None:
    for rule in _load():
        assert REQUIRED_FIELDS <= set(rule), rule
        assert rule["kind"] in VALID_KINDS, rule


def test_seeded_interposed_pattern_rule_matches_the_sw_neo4j_precedent() -> None:
    (rule,) = [r for r in _load() if r["id"] == "conv-interposed-neo4j-volume"]
    assert rule["kind"] == "interposed-pattern"
    assert rule["enabled"] is True
    params: dict[str, object] = rule["params"]  # type: ignore[assignment]
    assert params["source_type"] == "SystemSoftware"
    assert params["relationship_type"] == "Assignment"
    assert params["target_type"] == "DataObject"
    assert params["intermediary_types"] == ["Artifact"]
    assert params["target_relationship_type"] == "Realization"


def test_motivation_relationship_policies_are_configured_as_conventions() -> None:
    rules = _load()
    ids = {str(rule["id"]) for rule in rules}
    assert {
        "conv-driver-associated-with-assessment",
        "conv-assessment-associated-with-goal",
        "conv-goal-associated-with-assessment",
        "conv-outcome-realizes-goal",
        "conv-outcome-realized-by-requirement",
        "conv-capability-realizes-requirement",
        "conv-driver-routes-through-assessment",
    } <= ids
    for rule in rules:
        if rule["kind"] == "required-neighbour":
            params: dict[str, object] = rule["params"]  # type: ignore[assignment]
            assert params["relationship_type"] in {"Association", "Realization"}
            assert params["direction"] in {"incoming", "outgoing"}


def test_round_trips_through_safe_load_and_safe_dump_with_no_information_loss() -> None:
    original = _load()
    dumped = yaml.safe_dump(original)
    reloaded = yaml.safe_load(dumped)
    assert reloaded == original
