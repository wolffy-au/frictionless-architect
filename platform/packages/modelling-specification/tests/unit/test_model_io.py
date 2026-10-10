"""Unit tests for model_io.py -- validation + view scoping.

Ported from `tests/tools/architecture_model/test_model_build.py` (ADR-0037, R2): the
logic these exercise moved from root's `build.py` into `model_io.py`, so the tests move
with it. The helpers are driven directly with dicts against a real pyArchimate Model,
so these never touch elements.yaml / the filesystem.
"""

from __future__ import annotations

from typing import Any

from modelling_specification import model_io
from pyArchimate import Element, Model


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
    assert any("bypassing its own Assessment" in e for e in errors)


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
    warnings = model_io.check_motivation_conventions(elements, rels, [], types_by_id, errors)
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
    warnings = model_io.check_motivation_conventions(elements, rels, views, types_by_id, errors)
    assert errors == []
    assert any("keeping it" in w for w in warnings)


def test_validate_model_flags_an_illegal_relationship() -> None:
    model = Model("t")
    a = model.add(concept_type="BusinessActor", name="A")
    b = model.add(concept_type="Goal", name="B")
    model.add_relationship(rel_type="Composition", source=a, target=b, name=None)

    result = model_io.validate_model(model)

    assert result["clean"] is False
    checks = {f["check"] for f in result["findings"]}
    assert "illegal_relationship" in checks


def test_write_and_validate_against_the_real_repo_model() -> None:
    code, errors, _warnings, result = model_io.write_and_validate()
    assert errors == []
    assert code == 0
    assert result is not None
    assert result["clean"] is True
    assert result["elements"] > 0
    assert result["relationships"] > 0
