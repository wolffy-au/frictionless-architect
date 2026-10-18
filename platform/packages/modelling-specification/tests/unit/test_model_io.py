"""Unit tests for model_io.py -- validation + view scoping.

Ported from `tests/tools/architecture_model/test_model_build.py` (ADR-0037, R2): the
logic these exercise moved from root's `build.py` into `model_io.py`, so the tests move
with it. The helpers are driven directly with dicts against a real pyArchimate Model,
so these never touch elements.yaml / the filesystem.
"""

from __future__ import annotations

from typing import Any

import pytest
from modelling_specification import model_io
from pyArchimate import ArchiType, Element, Model


def test_canon_resolves_case_and_separator_insensitively() -> None:
    errors: list[str] = []
    assert model_io.canon("application-component", errors, "ctx") == "ApplicationComponent"
    assert model_io.canon("APPLICATION_COMPONENT", errors, "ctx") == "ApplicationComponent"
    assert errors == []


def test_canon_reports_unknown_name_with_context() -> None:
    errors: list[str] = []
    assert model_io.canon("not-a-concept", errors, "element foo") is None
    assert errors == ["element foo: 'not-a-concept' is not an ArchiMate 3.2 concept name (pyArchimate.ArchiType)"]


def test_det_id_is_deterministic_and_distinct() -> None:
    first_call = model_io.det_id("x")
    second_call = model_io.det_id("x")
    assert first_call == second_call
    assert model_io.det_id("x", "y") != model_io.det_id("y", "x")


def test_add_elements_skips_duplicates_and_bad_types() -> None:
    model = Model("t")
    errors: list[str] = []
    elements = [
        {"id": "a", "type": "application-component", "name": "A"},
        {"id": "a", "type": "application-component", "name": "A-again"},
        {"id": "b", "type": "bogus-type", "name": "B"},
        {"id": "c", "name": "C"},  # missing type
    ]
    by_id, types = model_io.add_elements(model, elements, errors)

    assert set(by_id) == {"a"}
    assert types == {"a": "ApplicationComponent"}
    assert any("duplicate element id: a" in e for e in errors)
    assert any("bogus-type" in e for e in errors)
    assert any("missing id/type/name" in e for e in errors)


def test_add_relationships_reports_unknown_endpoint() -> None:
    model = Model("t")
    errors: list[str] = []
    by_id, _ = model_io.add_elements(model, [{"id": "a", "type": "application-component", "name": "A"}], errors)
    model_io.add_relationships(model, [{"type": "serving", "source": "a", "target": "ghost"}], by_id, errors)
    assert any("unknown id 'ghost'" in e for e in errors)
    assert model.relationships == []


def test_add_relationships_reports_missing_fields_and_bad_type() -> None:
    model = Model("t")
    errors: list[str] = []
    by_id, _ = model_io.add_elements(
        model,
        [
            {"id": "a", "type": "application-component", "name": "A"},
            {"id": "b", "type": "application-component", "name": "B"},
        ],
        errors,
    )
    model_io.add_relationships(
        model,
        [
            {"source": "a", "target": "b"},  # missing type
            {"type": "bogus-rel-type", "source": "a", "target": "b"},
        ],
        by_id,
        errors,
    )
    assert any("missing type/source/target" in e for e in errors)
    assert any("bogus-rel-type" in e for e in errors)
    assert model.relationships == []


def test_add_relationships_applies_access_type_and_extra_props() -> None:
    model = Model("t")
    errors: list[str] = []
    by_id, _ = model_io.add_elements(
        model,
        [
            {"id": "a", "type": "application-function", "name": "A"},
            {"id": "b", "type": "data-object", "name": "B"},
        ],
        errors,
    )
    model_io.add_relationships(
        model,
        [{"type": "access", "source": "a", "target": "b", "props": {"access_type": "Write", "note": "x"}}],
        by_id,
        errors,
    )
    assert errors == []
    (rel,) = model.relationships
    assert rel.prop("note") == "x"


def test_add_views_scopes_by_include_type_and_adds_in_scope_connections() -> None:
    model = Model("t")
    errors: list[str] = []
    elements = [
        {"id": "a", "type": "application-component", "name": "A"},
        {"id": "b", "type": "application-component", "name": "B"},
        {"id": "n", "type": "node", "name": "N"},
    ]
    by_id, types = model_io.add_elements(model, elements, errors)
    model_io.add_relationships(model, [{"type": "serving", "source": "a", "target": "b"}], by_id, errors)

    model_io.add_views(
        model,
        [{"id": "v1", "name": "V1", "include_types": ["application-component"]}],
        elements,
        by_id,
        types,
        errors,
    )

    assert errors == []
    view = model.views[0]
    assert len(view.nodes) == 2  # a and b, not the Node
    assert len(view.conns) == 1  # the a->b serving edge, both ends on the view


def test_add_views_reports_unknown_member_id() -> None:
    model = Model("t")
    errors: list[str] = []
    elements = [{"id": "a", "type": "application-component", "name": "A"}]
    by_id, types = model_io.add_elements(model, elements, errors)
    model_io.add_views(
        model,
        [{"id": "v1", "name": "V1", "members": ["a", "missing"]}],
        elements,
        by_id,
        types,
        errors,
    )
    assert any("references unknown ids: ['missing']" in e for e in errors)


def _model_with(
    elements: list[dict[str, Any]], rels: list[dict[str, Any]]
) -> tuple[Model, list[dict[str, Any]], dict[str, Element], dict[str, str], list[str]]:
    model = Model("t")
    errors: list[str] = []
    by_id, types = model_io.add_elements(model, elements, errors)
    model_io.add_relationships(model, rels, by_id, errors)
    assert errors == []
    return model, elements, by_id, types, errors


def test_add_views_passes_a_conforming_viewpoint() -> None:
    els = [
        {"id": "cap", "type": "capability", "name": "Cap"},
        {"id": "vs", "type": "value-stream", "name": "VS"},
    ]
    model, elements, by_id, types, errors = _model_with(els, [{"type": "serving", "source": "cap", "target": "vs"}])
    model_io.add_views(
        model,
        [{"id": "v1", "name": "V1", "members": ["cap", "vs"], "viewpoint": "value_stream"}],
        elements,
        by_id,
        types,
        errors,
    )
    assert errors == []


def test_add_views_flags_a_concept_outside_the_declared_viewpoint() -> None:
    els = [
        {"id": "cap", "type": "capability", "name": "Cap"},
        {"id": "goal", "type": "goal", "name": "Goal"},
    ]
    model, elements, by_id, types, errors = _model_with(els, [])
    model_io.add_views(
        model,
        [{"id": "v1", "name": "V1", "members": ["cap", "goal"], "viewpoint": "value_stream"}],
        elements,
        by_id,
        types,
        errors,
    )
    assert any("value_stream viewpoint" in e and "Goal" in e for e in errors)


def test_add_views_reports_an_unknown_viewpoint_slug() -> None:
    els = [{"id": "cap", "type": "capability", "name": "Cap"}]
    model, elements, by_id, types, errors = _model_with(els, [])
    model_io.add_views(
        model,
        [{"id": "v1", "name": "V1", "members": ["cap"], "viewpoint": "not-a-viewpoint"}],
        elements,
        by_id,
        types,
        errors,
    )
    assert any("unknown viewpoint 'not-a-viewpoint'" in e for e in errors)


def test_add_views_custom_viewpoint_skips_the_check() -> None:
    els = [
        {"id": "cap", "type": "capability", "name": "Cap"},
        {"id": "node", "type": "node", "name": "N"},
    ]
    model, elements, by_id, types, errors = _model_with(els, [])
    model_io.add_views(
        model,
        [{"id": "v1", "name": "V1", "members": ["cap", "node"], "viewpoint": "custom"}],
        elements,
        by_id,
        types,
        errors,
    )
    assert errors == []


def test_add_views_exclude_by_type_and_endpoint_types_suppresses_an_in_scope_edge() -> None:
    els = [
        {"id": "cap-a", "type": "capability", "name": "Cap A"},
        {"id": "cap-b", "type": "capability", "name": "Cap B"},
    ]
    rels = [
        {"type": "serving", "source": "cap-a", "target": "cap-b"},
        {"type": "triggering", "source": "cap-a", "target": "cap-b"},
    ]
    model, elements, by_id, types, errors = _model_with(els, rels)
    model_io.add_views(
        model,
        [
            {
                "id": "v1",
                "name": "V1",
                "members": ["cap-a", "cap-b"],
                "exclude": [{"type": "serving", "source_type": "capability", "target_type": "capability"}],
            }
        ],
        elements,
        by_id,
        types,
        errors,
    )

    assert errors == []
    view = model.views[0]
    # only the Triggering edge survives; the Serving edge matched the exclude pattern
    assert len(view.conns) == 1
    (rel,) = [model.rels_dict[c.ref] for c in view.conns]
    assert rel.type == "Triggering"


def test_add_views_exclude_by_specific_source_and_target_id() -> None:
    els = [
        {"id": "cap-a", "type": "capability", "name": "Cap A"},
        {"id": "cap-b", "type": "capability", "name": "Cap B"},
        {"id": "cap-c", "type": "capability", "name": "Cap C"},
    ]
    rels = [
        {"type": "serving", "source": "cap-a", "target": "cap-b"},
        {"type": "serving", "source": "cap-a", "target": "cap-c"},
    ]
    model, elements, by_id, types, errors = _model_with(els, rels)
    model_io.add_views(
        model,
        [
            {
                "id": "v1",
                "name": "V1",
                "members": ["cap-a", "cap-b", "cap-c"],
                "exclude": [{"source": "cap-a", "target": "cap-b"}],
            }
        ],
        elements,
        by_id,
        types,
        errors,
    )

    assert errors == []
    view = model.views[0]
    (rel,) = [model.rels_dict[c.ref] for c in view.conns]
    assert rel.target.uuid == by_id["cap-c"].uuid


def test_relationship_excluded_skips_a_pattern_whose_source_does_not_match() -> None:
    # The pattern names a specific source ("cap-a"); a relationship from a
    # different source must fall through that `continue` rather than match on
    # the (unset) target alone.
    els = [
        {"id": "cap-a", "type": "capability", "name": "Cap A"},
        {"id": "cap-b", "type": "capability", "name": "Cap B"},
        {"id": "cap-c", "type": "capability", "name": "Cap C"},
    ]
    rels = [{"type": "serving", "source": "cap-c", "target": "cap-b"}]
    model, _elements, by_id, types, errors = _model_with(els, rels)
    uuid_to_id = {el.uuid: eid for eid, el in by_id.items()}
    patterns = model_io._compile_exclude_patterns(
        {"id": "v1", "exclude": [{"source": "cap-a", "target": "cap-b"}]}, errors
    )
    (rel,) = model.relationships

    assert model_io._relationship_excluded(rel, patterns, uuid_to_id, types) is False


def test_view_scope_explicit_non_default_context_does_not_pull_in_platform() -> None:
    errors: list[str] = []
    scope = model_io._view_scope({"id": "v1", "context": "it4it"}, {"platform", "it4it"}, errors)
    assert scope == {"it4it"}
    assert errors == []


def test_add_views_reports_a_view_missing_id_or_name() -> None:
    model = Model("t")
    errors: list[str] = []
    elements = [{"id": "a", "type": "application-component", "name": "A"}]
    by_id, types = model_io.add_elements(model, elements, errors)

    model_io.add_views(model, [{"name": "No Id"}], elements, by_id, types, errors)

    assert any("view missing id/name" in e for e in errors)
    assert model.views == []


def test_add_views_reports_a_layout_failure(monkeypatch: Any) -> None:
    from pyArchimate.view.layout.core import LayoutResult

    model = Model("t")
    errors: list[str] = []
    elements = [{"id": "a", "type": "capability", "name": "A"}]
    by_id, types = model_io.add_elements(model, elements, errors)
    failure = LayoutResult(
        success=False,
        view_id="v1",
        algorithm_used="grid",
        elements_processed=0,
        connections_processed=0,
        layout_time_ms=0.0,
        error_message="boom",
    )
    monkeypatch.setattr(model_io, "apply_layout", lambda view, cfg: failure)

    model_io.add_views(model, [{"id": "v1", "name": "V1", "members": ["a"]}], elements, by_id, types, errors)

    assert any("view v1 grid failed: boom" in e for e in errors)


def test_assemble_skips_a_view_without_id_and_flags_a_duplicate_view_id() -> None:
    errors: list[str] = []
    model, errors, _warnings = model_io._assemble(
        "t", [], [], [{"name": "no id"}, {"id": "v1", "name": "V1"}, {"id": "v1", "name": "V1 dup"}], errors
    )
    assert model is None
    assert any("duplicate view id: v1" in e for e in errors)
    assert any("view missing id/name" in e for e in errors)


def test_existing_elements_and_types_skips_elements_with_no_id_or_an_unknown_type(monkeypatch: Any) -> None:
    fake_elements = [
        {"id": "", "type": "application-component", "name": "No Id"},
        {"id": "bad-type", "type": "not-a-real-type", "name": "Bad"},
        {"id": "good", "type": "application-component", "name": "Good"},
    ]
    monkeypatch.setattr(model_io, "load_all_elements", lambda errors: fake_elements)

    elements, types_by_id = model_io.existing_elements_and_types()

    assert elements == fake_elements
    assert types_by_id == {"good": "ApplicationComponent"}


def test_add_views_without_exclude_renders_every_in_scope_edge() -> None:
    els = [
        {"id": "cap-a", "type": "capability", "name": "Cap A"},
        {"id": "cap-b", "type": "capability", "name": "Cap B"},
    ]
    rels = [{"type": "serving", "source": "cap-a", "target": "cap-b"}]
    model, elements, by_id, types, errors = _model_with(els, rels)
    model_io.add_views(
        model,
        [{"id": "v1", "name": "V1", "members": ["cap-a", "cap-b"]}],
        elements,
        by_id,
        types,
        errors,
    )

    assert errors == []
    assert len(model.views[0].conns) == 1


def test_add_views_exclude_elements_by_id_prefix_overrides_include_types() -> None:
    els = [
        {"id": "cap-first-party", "type": "capability", "name": "First Party"},
        {"id": "it4it-vendored", "type": "capability", "name": "Vendored"},
    ]
    model, elements, by_id, types, errors = _model_with(els, [])
    model_io.add_views(
        model,
        [
            {
                "id": "v1",
                "name": "V1",
                "include_types": ["capability"],
                "exclude_elements": [{"id_prefix": "it4it-"}],
            }
        ],
        elements,
        by_id,
        types,
        errors,
    )

    assert errors == []
    view = model.views[0]
    assert len(view.nodes) == 1
    (node,) = view.nodes
    assert node.ref == by_id["cap-first-party"].uuid


def test_add_views_exclude_elements_by_type_and_id_both_must_match() -> None:
    els = [
        {"id": "cap-a", "type": "capability", "name": "Cap A"},
        {"id": "cap-b", "type": "capability", "name": "Cap B"},
        {"id": "vs-a", "type": "value-stream", "name": "VS A"},
    ]
    model, elements, by_id, types, errors = _model_with(els, [])
    model_io.add_views(
        model,
        [
            {
                "id": "v1",
                "name": "V1",
                "include_types": ["capability", "value-stream"],
                # neither key alone matches vs-a (wrong type) or cap-b (wrong id) --
                # only cap-a, which matches both, is excluded.
                "exclude_elements": [{"type": "capability", "id": "cap-a"}],
            }
        ],
        elements,
        by_id,
        types,
        errors,
    )

    assert errors == []
    view = model.views[0]
    on_view = {node.ref for node in view.nodes}
    assert on_view == {by_id["cap-b"].uuid, by_id["vs-a"].uuid}


def test_load_path_flags_flow_value_truncated_by_unquoted_comma(tmp_path: Any) -> None:
    f = tmp_path / "elements.yaml"
    f.write_text("- {type: DataObject, id: art-x, name: X, desc: first part, lost tail}\n")
    errors: list[str] = []
    data = model_io.load_path(f, errors)
    assert data[0]["desc"] == "first part"  # YAML really does truncate it
    assert errors == [
        f"{f}: art-x: key 'lost tail' has no value — likely an unquoted comma truncating a flow-style value; quote it"
    ]


def test_load_path_flags_truncated_relationship_label(tmp_path: Any) -> None:
    f = tmp_path / "relationships.yaml"
    f.write_text("- {type: Serving, source: a, target: b, label: one, two}\n")
    errors: list[str] = []
    model_io.load_path(f, errors)
    assert len(errors) == 1
    assert "a->b: key 'two'" in errors[0]


def test_load_path_accepts_quoted_commas(tmp_path: Any) -> None:
    f = tmp_path / "elements.yaml"
    f.write_text('- {type: DataObject, id: art-x, name: X, desc: "first part, kept tail"}\n')
    errors: list[str] = []
    assert model_io.load_path(f, errors)[0]["desc"] == "first part, kept tail"
    assert errors == []


def test_load_path_reports_a_missing_required_file(tmp_path: Any) -> None:
    missing = tmp_path / "elements.yaml"
    errors: list[str] = []
    assert model_io.load_path(missing, errors) == []
    assert errors == [f"{missing} is missing"]


def test_validate_model_accepts_an_in_memory_model() -> None:
    model, errors, _warnings = model_io.build_model()
    assert errors == []
    assert model is not None
    result = model_io.validate_model(model)
    assert result["path"] == "<in-memory>"
    assert result["clean"] is True
    assert result["findings"] == []


def test_check_motivation_conventions_flags_a_driver_bypassing_its_assessment() -> None:
    elements = [
        {"id": "d1", "type": "Driver", "name": "D"},
        {"id": "assess1", "type": "Assessment", "name": "Assess"},
        {"id": "goal1", "type": "Goal", "name": "Goal"},
    ]
    rels = [
        {"type": "Influence", "source": "d1", "target": "assess1"},
        {"type": "Influence", "source": "d1", "target": "goal1"},  # bypasses assess1
    ]
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    model_io.check_motivation_conventions(elements, rels, [], types_by_id, errors)
    assert any("bypassing Assessment" in e for e in errors)


def test_check_motivation_conventions_warns_on_a_derived_goal_edge() -> None:
    elements = [
        {"id": "a", "type": "Requirement", "name": "A"},
        {"id": "b", "type": "Requirement", "name": "B"},
        {"id": "goal1", "type": "Goal", "name": "Goal"},
    ]
    rels = [
        {"type": "Realization", "source": "a", "target": "b"},
        {"type": "Realization", "source": "b", "target": "goal1"},
        {"type": "Realization", "source": "a", "target": "goal1"},  # derived: a->b->goal1
    ]
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    warnings = model_io.check_motivation_conventions(elements, rels, [], types_by_id, errors, rules=[])
    assert errors == []
    assert any("looks derived" in w for w in warnings)


def test_check_motivation_conventions_keeps_a_view_only_reachable_edge() -> None:
    elements = [
        {"id": "a", "type": "Requirement", "name": "A"},
        {"id": "b", "type": "Requirement", "name": "B"},
        {"id": "goal1", "type": "Goal", "name": "Goal"},
    ]
    rels = [
        {"type": "Realization", "source": "a", "target": "b"},
        {"type": "Realization", "source": "b", "target": "goal1"},
        {"type": "Realization", "source": "a", "target": "goal1"},
    ]
    views = [{"id": "v1", "members": ["a", "goal1"]}]  # b not in scope on this view
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    warnings = model_io.check_motivation_conventions(elements, rels, views, types_by_id, errors, rules=[])
    assert errors == []
    assert any("keeping it" in w for w in warnings)


def test_check_motivation_conventions_flags_a_capability_with_no_requirement() -> None:
    elements = [
        {"id": "cap1", "type": "Capability", "name": "Cap"},
        {"id": "req1", "type": "Requirement", "name": "Req"},
    ]
    rels: list[dict[str, Any]] = []  # cap1 realizes nothing
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    model_io.check_motivation_conventions(elements, rels, [], types_by_id, errors)
    assert any("conv-capability-realizes-requirement" in e and "'cap1'" in e for e in errors)


def test_check_motivation_conventions_exempts_a_vendored_capability() -> None:
    elements = [{"id": "it4it-cap1", "type": "Capability", "name": "IT4IT: Cap"}]
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    model_io.check_motivation_conventions(elements, [], [], types_by_id, errors)
    assert errors == []


def test_check_motivation_conventions_surfaces_a_malformed_conventions_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from modelling_specification.validation import conventions

    def _raise(*_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        raise conventions.ConventionRuleError("conv-bad: unknown kind 'nope'")

    monkeypatch.setattr(conventions, "load_rules", _raise)
    errors: list[str] = []

    model_io.check_motivation_conventions([], [], [], {}, errors)

    assert errors == ["conv-bad: unknown kind 'nope'"]


def test_check_motivation_conventions_flags_an_outcome_missing_its_neighbours() -> None:
    elements = [{"id": "outcome1", "type": "Outcome", "name": "Outcome"}]
    rels: list[dict[str, Any]] = [
        {"type": "Influence", "source": "assess1", "target": "outcome1"}
    ]  # Influence from an Assessment does not replace the required Realization to a
    # Goal or the required Realization from a Requirement
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    model_io.check_motivation_conventions(elements, rels, [], types_by_id, errors)
    assert any("conv-outcome-realizes-goal" in e and "'outcome1'" in e for e in errors)
    assert any("conv-outcome-realized-by-requirement" in e and "'outcome1'" in e for e in errors)


def test_check_motivation_conventions_flags_a_driver_missing_its_neighbours() -> None:
    elements = [{"id": "driver1", "type": "Driver", "name": "Driver"}]
    rels: list[dict[str, Any]] = []  # no Stakeholder, no Assessment
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    model_io.check_motivation_conventions(elements, rels, [], types_by_id, errors)
    assert any("conv-driver-associated-with-assessment" in e and "'driver1'" in e for e in errors)
    assert any("conv-driver-held-by-stakeholder" in e and "'driver1'" in e for e in errors)


def test_check_motivation_conventions_flags_an_assessment_missing_its_neighbours() -> None:
    elements = [
        {"id": "assess1", "type": "Assessment", "name": "Assessment"},
        {"id": "goal1", "type": "Goal", "name": "Goal"},
    ]
    rels: list[dict[str, Any]] = [
        {"type": "Influence", "source": "assess1", "target": "goal1"}
    ]  # Influence to a Goal does not replace the required Association to a Goal
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    model_io.check_motivation_conventions(elements, rels, [], types_by_id, errors)
    assert any("conv-assessment-associated-with-driver" in e and "'assess1'" in e for e in errors)
    assert any("conv-assessment-associated-with-goal" in e and "'assess1'" in e for e in errors)


def test_check_motivation_conventions_passes_a_complete_association_chain() -> None:
    elements = [
        {"id": "stk1", "type": "Stakeholder", "name": "Stakeholder"},
        {"id": "driver1", "type": "Driver", "name": "Driver"},
        {"id": "assess1", "type": "Assessment", "name": "Assessment"},
        {"id": "outcome1", "type": "Outcome", "name": "Outcome"},
        {"id": "goal1", "type": "Goal", "name": "Goal"},
        {"id": "req1", "type": "Requirement", "name": "Req"},
        {"id": "cap1", "type": "Capability", "name": "Cap"},
    ]
    rels = [
        {"type": "Association", "source": "stk1", "target": "driver1"},
        {"type": "Association", "source": "driver1", "target": "assess1"},
        {"type": "Association", "source": "assess1", "target": "goal1"},
        {"type": "Realization", "source": "outcome1", "target": "goal1"},
        {"type": "Realization", "source": "req1", "target": "outcome1"},
        {"type": "Realization", "source": "cap1", "target": "req1"},
    ]
    types_by_id = {e["id"]: e["type"] for e in elements}
    errors: list[str] = []
    model_io.check_motivation_conventions(elements, rels, [], types_by_id, errors)
    assert errors == []


def test_validate_model_flags_an_illegal_relationship() -> None:
    model = Model("t")
    a = model.add(concept_type="BusinessActor", name="A")
    b = model.add(concept_type="Goal", name="B")
    model.add_relationship(rel_type="Composition", source=a, target=b, name=None)

    result = model_io.validate_model(model)

    assert result["clean"] is False
    checks = {f["check"] for f in result["findings"]}
    assert "illegal_relationship" in checks
    (finding,) = [f for f in result["findings"] if f["check"] == "illegal_relationship"]
    assert finding["rel_type"] == "Composition"
    assert finding["source_type"] == "BusinessActor"
    assert finding["target_type"] == "Goal"


def test_validate_model_flags_a_dangling_relationship_endpoint(monkeypatch: Any) -> None:
    # A relationship whose source/target no longer resolves to a live element --
    # unreachable via this module's own add_relationships (which refuses to create
    # one) or via Model.read() (which refuses to load one), so only reachable by
    # corrupting the private `_source` ref directly, the way a library bug or a
    # hand-edited XML file could. pyArchimate's own check_invalid_relationships()
    # does not guard against a None endpoint either (it would raise AttributeError
    # on r.source.type), so it is stubbed out here to isolate validate_model's own
    # dangling-relationship guard (the thing under test) from that unrelated crash.
    model = Model("t")
    a = model.add(concept_type="BusinessActor", name="A")
    b = model.add(concept_type="BusinessActor", name="B")
    rel = model.add_relationship(rel_type="Serving", source=a, target=b, name=None)
    rel._source = "does-not-exist"  # noqa: SLF001 - simulating a corrupt reference
    monkeypatch.setattr(model, "check_invalid_relationships", lambda: [])

    result = model_io.validate_model(model)

    assert result["clean"] is False
    (finding,) = result["findings"]
    assert finding == {"check": "dangling_relationship", "id": rel.uuid, "detail": "Serving has a missing endpoint"}


def test_validate_model_flags_a_broken_connection() -> None:
    model = Model("t")
    a = model.add(concept_type="BusinessActor", name="A")
    b = model.add(concept_type="BusinessActor", name="B")
    rel = model.add_relationship(rel_type="Serving", source=a, target=b, name=None)
    view: Any = model.add(ArchiType.View, name="V")
    view.add(ref=a)
    view.add(ref=b)
    view.add_connection(ref=rel)
    del model.rels_dict[rel.uuid]  # the connection now references a relationship that is gone

    result = model_io.validate_model(model)

    assert result["clean"] is False
    checks = {f["check"] for f in result["findings"]}
    assert checks == {"broken_connection"}


def test_validate_model_flags_an_orphan_view_node() -> None:
    model = Model("t")
    a = model.add(concept_type="BusinessActor", name="A")
    view: Any = model.add(ArchiType.View, name="V")
    view.add(ref=a)
    del model.elems_dict[a.uuid]  # the node now references an element that is gone

    result = model_io.validate_model(model)

    assert result["clean"] is False
    checks = {f["check"] for f in result["findings"]}
    assert checks == {"orphan_view_node"}


def test_validate_model_appends_an_invalid_relationship_finding_not_already_caught(monkeypatch: Any) -> None:
    # check_invalid_relationships() is documented as "catches anything the per-rel
    # loop missed" -- under the current pyArchimate version the two checks always
    # agree, so the only way to exercise the dedup-and-append branch is to stub the
    # library call to simulate it flagging something the per-rel loop did not.
    model = Model("t")
    a = model.add(concept_type="BusinessActor", name="A")
    b = model.add(concept_type="BusinessActor", name="B")
    rel = model.add_relationship(rel_type="Serving", source=a, target=b, name=None)
    monkeypatch.setattr(model, "check_invalid_relationships", lambda: [rel.uuid])

    result = model_io.validate_model(model)

    assert result["clean"] is False
    assert result["findings"] == [
        {"check": "invalid_relationship", "id": rel.uuid, "detail": "fails check_invalid_relationships()"}
    ]


def test_merge_candidate_validates_a_clean_delta_against_the_real_model() -> None:
    # sub-modelling is a real ApplicationComponent already in architecture/model/
    # elements.yaml -- merge_candidate must load it from disk, not just the delta,
    # for this Assignment to type-check (FR-002, R9).
    model, errors, _warnings = model_io.merge_candidate(
        [{"id": "fn-test-delta", "type": "application-function", "name": "Test Delta Fn"}],
        [{"type": "assignment", "source": "sub-modelling", "target": "fn-test-delta"}],
    )
    assert errors == []
    assert model is not None
    result = model_io.validate_model(model)
    assert result["clean"] is True


def test_merge_candidate_flags_an_illegal_relationship_against_a_real_existing_element() -> None:
    # Composition from an ApplicationComponent to an ApplicationFunction is not in the
    # ArchiMate 3.2 matrix -- a delta that only knew about its own new element could
    # not catch this; merge_candidate must check it against sub-modelling's *actual*
    # type as loaded from disk (FR-002's "whole resulting model", not the delta alone).
    model, errors, _warnings = model_io.merge_candidate(
        [{"id": "fn-test-delta", "type": "application-function", "name": "Test Delta Fn"}],
        [{"type": "composition", "source": "sub-modelling", "target": "fn-test-delta"}],
    )
    assert errors == []
    assert model is not None
    result = model_io.validate_model(model)
    assert result["clean"] is False
    assert any(f["check"] == "illegal_relationship" for f in result["findings"])


def test_merge_candidate_catches_a_delta_id_colliding_with_a_real_existing_element() -> None:
    # Proves the real model is loaded and merged in, not just the delta validated
    # in isolation: an id the delta re-declares is already on disk.
    model, errors, _warnings = model_io.merge_candidate(
        [{"id": "sub-modelling", "type": "application-component", "name": "Duplicate"}], []
    )
    assert model is None
    assert any("duplicate element id: sub-modelling" in e for e in errors)


def test_existing_element_ids_includes_a_real_element() -> None:
    assert "sub-modelling" in model_io.existing_element_ids()


def test_existing_element_types_maps_a_real_element_to_its_canonical_type() -> None:
    assert model_io.existing_element_types()["sub-modelling"] == "ApplicationComponent"


def test_append_delta_appends_flow_style_entries_without_disturbing_existing_content(
    tmp_path: Any, monkeypatch: Any
) -> None:
    elements_path = tmp_path / "elements.yaml"
    elements_path.write_text("- {type: ApplicationComponent, id: existing, name: Existing}\n")
    rels_path = tmp_path / "relationships.yaml"
    rels_path.write_text("- {type: Serving, source: existing, target: existing, label: self}\n")
    monkeypatch.setattr(model_io, "HERE", tmp_path)

    model_io.append_delta(
        [{"type": "ApplicationFunction", "id": "fn-new", "name": "New Fn"}],
        [{"type": "Assignment", "source": "existing", "target": "fn-new"}],
    )

    elements_text = elements_path.read_text()
    assert "{type: ApplicationComponent, id: existing, name: Existing}" in elements_text
    assert "{type: ApplicationFunction, id: fn-new, name: New Fn}" in elements_text
    rels_text = rels_path.read_text()
    assert "{type: Serving, source: existing, target: existing, label: self}" in rels_text
    assert "{type: Assignment, source: existing, target: fn-new}" in rels_text


def test_append_delta_quotes_values_containing_yaml_special_characters(tmp_path: Any, monkeypatch: Any) -> None:
    elements_path = tmp_path / "elements.yaml"
    elements_path.write_text("")
    (tmp_path / "relationships.yaml").write_text("")
    monkeypatch.setattr(model_io, "HERE", tmp_path)

    model_io.append_delta([{"type": "ApplicationFunction", "id": "fn-new", "name": "Has: a colon"}], [])

    assert "name: 'Has: a colon'" in elements_path.read_text()


def test_write_and_validate_against_the_real_repo_model() -> None:
    code, errors, _warnings, result = model_io.write_and_validate()
    assert errors == []
    assert code == 0
    assert result is not None
    assert result["clean"] is True
    assert result["elements"] > 0
    assert result["relationships"] > 0
