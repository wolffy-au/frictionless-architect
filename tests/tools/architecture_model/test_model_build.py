"""Unit tests for architecture/model/build.py — validation + view scoping.

The helpers are driven directly with dicts against a real pyArchimate Model, so
these never touch elements.yaml / the filesystem.
"""

from __future__ import annotations

from pyArchimate import Model

import build


def test_canon_resolves_case_and_separator_insensitively() -> None:
    errors: list[str] = []
    assert build.canon("application-component", errors, "ctx") == "ApplicationComponent"
    assert build.canon("APPLICATION_COMPONENT", errors, "ctx") == "ApplicationComponent"
    assert errors == []


def test_canon_reports_unknown_name_with_context() -> None:
    errors: list[str] = []
    assert build.canon("not-a-concept", errors, "element foo") is None
    assert errors == ["element foo: 'not-a-concept' is not an ArchiMate 3.2 concept name (pyArchimate.ArchiType)"]


def test_det_id_is_deterministic_and_distinct() -> None:
    assert build.det_id("x") == build.det_id("x")
    assert build.det_id("x", "y") != build.det_id("y", "x")


def test_add_elements_skips_duplicates_and_bad_types() -> None:
    model = Model("t")
    errors: list[str] = []
    elements = [
        {"id": "a", "type": "application-component", "name": "A"},
        {"id": "a", "type": "application-component", "name": "A-again"},
        {"id": "b", "type": "bogus-type", "name": "B"},
        {"id": "c", "name": "C"},  # missing type
    ]
    by_id, types = build.add_elements(model, elements, errors)

    assert set(by_id) == {"a"}
    assert types == {"a": "ApplicationComponent"}
    assert any("duplicate element id: a" in e for e in errors)
    assert any("bogus-type" in e for e in errors)
    assert any("missing id/type/name" in e for e in errors)


def test_add_relationships_reports_unknown_endpoint() -> None:
    model = Model("t")
    errors: list[str] = []
    by_id, _ = build.add_elements(model, [{"id": "a", "type": "application-component", "name": "A"}], errors)
    build.add_relationships(model, [{"type": "serving", "source": "a", "target": "ghost"}], by_id, errors)
    assert any("unknown id 'ghost'" in e for e in errors)
    assert model.relationships == []


def test_add_views_scopes_by_include_type_and_adds_in_scope_connections() -> None:
    model = Model("t")
    errors: list[str] = []
    elements = [
        {"id": "a", "type": "application-component", "name": "A"},
        {"id": "b", "type": "application-component", "name": "B"},
        {"id": "n", "type": "node", "name": "N"},
    ]
    by_id, types = build.add_elements(model, elements, errors)
    build.add_relationships(model, [{"type": "serving", "source": "a", "target": "b"}], by_id, errors)

    build.add_views(
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
    by_id, types = build.add_elements(model, elements, errors)
    build.add_views(
        model,
        [{"id": "v1", "name": "V1", "members": ["a", "missing"]}],
        elements,
        by_id,
        types,
        errors,
    )
    assert any("references unknown ids: ['missing']" in e for e in errors)
