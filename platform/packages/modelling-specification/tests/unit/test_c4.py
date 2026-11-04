"""modelling_specification.c4: ArchiMate-to-C4 projection (ADR-0045).

Rendering runs this module as a subprocess, so these call it in-process. The golden
test pins it to the C4 diagrams committed under architecture/model/diagrams/c4/.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from modelling_specification import c4, rendering
from modelling_specification.model_io import REPO_ROOT
from pyArchimate import ArchiType, Model

SYSTEM = "Acme System"


def _write(model: Model, tmp_path: Path) -> str:
    path = tmp_path / "m.xml"
    model.write(str(path))
    return str(path)


def _system_model() -> tuple[Model, Any, Any]:
    """A system containing a service component and a database."""
    model = Model("m")
    system = model.add(ArchiType.Grouping, SYSTEM, desc="The system")
    service = model.add(ArchiType.ApplicationComponent, "Service", desc="Does things")
    store = model.add(ArchiType.DataObject, "Store")
    model.add_relationship(ArchiType.Composition, system, service)
    model.add_relationship(ArchiType.Composition, system, store)
    model.add_relationship(ArchiType.Access, service, store, access_type="Read")
    return model, service, store


@pytest.mark.parametrize(("slug", "level", "layout"), rendering.C4_DIAGRAMS)
def test_committed_diagram_is_reproduced_exactly(
    monkeypatch: pytest.MonkeyPatch, slug: str, level: str, layout: str
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    text, _ = c4.generate(rendering.MODEL_REL, rendering.SYSTEM, level, layout)
    assert text.rstrip("\n") + "\n" == (REPO_ROOT / "architecture/model/diagrams" / f"{slug}.puml").read_text()


def test_container_level_draws_the_boundary(tmp_path: Path) -> None:
    model, _, _ = _system_model()
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "container", "LEFT_RIGHT")
    assert "!include <C4/C4_Container>" in text
    assert "LAYOUT_LEFT_RIGHT()" in text
    assert "System_Boundary(" in text
    assert "Container(n_" in text
    assert "ContainerDb(n_" in text
    assert "reads from" in text


def test_context_level_folds_inside_elements_onto_the_system(tmp_path: Path) -> None:
    model, service, _ = _system_model()
    person = model.add(ArchiType.BusinessActor, "User")
    model.add_relationship(ArchiType.Flow, person, service)
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "context", "WITH_LEGEND")
    assert "!include <C4/C4_Context>" in text
    assert "System(n_" in text
    assert "Person(n_" in text
    assert "sends data to" in text
    assert "Container(" not in text


def test_system_falls_back_to_the_c4_system_prop(tmp_path: Path) -> None:
    model = Model("m")
    model.add(ArchiType.ApplicationComponent, "Marked").prop("c4", "system")
    text, _ = c4.generate(_write(model, tmp_path), "Some Other Name", "context", "WITH_LEGEND")
    assert "Marked" in text


def test_unknown_system_is_an_error(tmp_path: Path) -> None:
    model = Model("m")
    model.add(ArchiType.Goal, "G")
    path = _write(model, tmp_path)
    with pytest.raises(KeyError, match="no element named"):
        c4.generate(path, SYSTEM, "context", "WITH_LEGEND")


def test_system_kind_prop_picks_the_macro(tmp_path: Path) -> None:
    model = Model("m")
    model.add(ArchiType.ApplicationComponent, SYSTEM).prop("c4-kind", "db")
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "context", "WITH_LEGEND")
    assert "SystemDb(" in text


@pytest.mark.parametrize(
    ("override", "expected"), [("containerQueue", "ContainerQueue("), ("containerDb", "ContainerDb(")]
)
def test_c4_prop_overrides_classification(tmp_path: Path, override: str, expected: str) -> None:
    model, service, _ = _system_model()
    service.prop("c4", override)
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "container", "WITH_LEGEND")
    assert expected in text


@pytest.mark.parametrize(
    ("kind", "level", "expected"),
    [
        (ArchiType.ApplicationService, "context", "System_Ext("),
        (ArchiType.BusinessObject, "context", "SystemDb_Ext("),
        (ArchiType.BusinessService, "context", "System_Ext("),
        (ArchiType.BusinessObject, "container", None),
        (ArchiType.Node, "context", None),
    ],
)
def test_outside_elements_classify_by_type_and_level(
    tmp_path: Path, kind: ArchiType, level: str, expected: str | None
) -> None:
    model, _, _ = _system_model()
    model.add(kind, "Outside")
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, level, "WITH_LEGEND")
    if expected:
        assert expected in text
    assert ("Outside" in text) is bool(expected)


def test_ignored_inside_element_is_not_a_container(tmp_path: Path) -> None:
    model, _, _ = _system_model()
    system = next(e for e in model.elements if e.name == SYSTEM)
    function = model.add(ArchiType.ApplicationFunction, "Fn")
    model.add_relationship(ArchiType.Composition, system, function)
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "container", "WITH_LEGEND")
    assert "Fn" not in text


def test_data_object_contents_do_not_expand_into_the_boundary(tmp_path: Path) -> None:
    model, _, store = _system_model()
    nested = model.add(ArchiType.DataObject, "Nested")
    model.add_relationship(ArchiType.Aggregation, store, nested)
    inside = c4.contained_by_system(model, next(e.uuid for e in model.elements if e.name == SYSTEM))
    assert store.uuid in inside
    assert nested.uuid not in inside


def _two_externals(tmp_path: Path, rel: ArchiType, **props: str) -> tuple[str, Any]:
    """A person interacting with an inside service through `rel`, carrying `props`."""
    model, service, _ = _system_model()
    person = model.add(ArchiType.BusinessActor, "User")
    relationship = model.add_relationship(rel, person, service)
    for key, value in props.items():
        relationship.prop(key.replace("_", "-"), value)
    return _write(model, tmp_path), relationship


@pytest.mark.parametrize(
    ("rel", "label"),
    [
        (ArchiType.Serving, '"uses"'),
        (ArchiType.Triggering, '"triggers"'),
        (ArchiType.Association, '"related to"'),
    ],
)
def test_relationship_default_labels(tmp_path: Path, rel: ArchiType, label: str) -> None:
    path, _ = _two_externals(tmp_path, rel)
    text, _ = c4.generate(path, SYSTEM, "container", "WITH_LEGEND")
    assert label in text


def test_unmapped_relationship_warns_and_is_generic(tmp_path: Path) -> None:
    path, _ = _two_externals(tmp_path, ArchiType.Influence)
    text, warnings = c4.generate(path, SYSTEM, "container", "WITH_LEGEND")
    assert '"influence"' in text
    assert any("not in C4 mapping" in w for w in warnings)


def test_relationship_props_override_label_direction_and_technology(tmp_path: Path) -> None:
    path, _ = _two_externals(tmp_path, ArchiType.Flow, c4_label="custom", c4_direction="r", c4_technology="HTTPS")
    text, _ = c4.generate(path, SYSTEM, "container", "WITH_LEGEND")
    assert "Rel_R(" in text
    assert '"custom", "HTTPS"' in text


@pytest.mark.parametrize("level", ["container", "context"])
def test_birel_prop(tmp_path: Path, level: str) -> None:
    path, _ = _two_externals(tmp_path, ArchiType.Flow, c4_birel="true", c4_technology="HTTPS")
    text, _ = c4.generate(path, SYSTEM, level, "WITH_LEGEND")
    assert "BiRel(" in text


def test_context_level_merges_parallel_relationships(tmp_path: Path) -> None:
    model, service, store = _system_model()
    person = model.add(ArchiType.BusinessActor, "User")
    model.add_relationship(ArchiType.Flow, person, service, name="first")
    model.add_relationship(ArchiType.Flow, person, store, name="first")
    other = model.add_relationship(ArchiType.Flow, person, store, name="second")
    other.prop("c4-direction", "U")
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "context", "WITH_LEGEND")
    assert 'first\\nsecond"' in text
    assert "Rel_U(" in text


def test_container_level_drops_exact_duplicates_only(tmp_path: Path) -> None:
    model, service, _ = _system_model()
    person = model.add(ArchiType.BusinessActor, "User")
    model.add_relationship(ArchiType.Flow, person, service, name="same")
    model.add_relationship(ArchiType.Flow, person, service, name="same")
    model.add_relationship(ArchiType.Flow, person, service, name="different")
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "container", "WITH_LEGEND")
    assert text.count('"same"') == 1
    assert text.count('"different"') == 1


def test_enterprise_boundary_wraps_the_diagram(tmp_path: Path) -> None:
    model, _, _ = _system_model()
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "container", "WITH_LEGEND", "Acme Corp")
    assert 'Enterprise_Boundary(enterprise_AcmeCorp, "Acme Corp") {' in text


def test_context_level_keeps_the_first_technology_when_merging(tmp_path: Path) -> None:
    model, service, store = _system_model()
    person = model.add(ArchiType.BusinessActor, "User")
    model.add_relationship(ArchiType.Flow, person, service, name="plain")
    model.add_relationship(ArchiType.Flow, person, store, name="secure").prop("c4-technology", "HTTPS")
    text, _ = c4.generate(_write(model, tmp_path), SYSTEM, "context", "WITH_LEGEND")
    assert 'plain\\nsecure", "HTTPS"' in text


@pytest.mark.parametrize("obj", [object(), SimpleNamespace(props=None)])
def test_prop_without_usable_props_is_none(obj: object) -> None:
    assert c4.prop(obj, "c4") is None


def _cli(monkeypatch: pytest.MonkeyPatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["c4", *argv])
    return c4.main()


def test_cli_prints_warnings_and_stdout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path, _ = _two_externals(tmp_path, ArchiType.Influence)
    assert _cli(monkeypatch, path, "--system", SYSTEM) == 0
    captured = capsys.readouterr()
    assert "@enduml" in captured.out
    assert "warning:" in captured.err


def test_cli_reports_an_unknown_system(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    model = Model("m")
    model.add(ArchiType.Goal, "G")
    assert _cli(monkeypatch, _write(model, tmp_path), "--system", SYSTEM) == 2
    assert "no element named" in capsys.readouterr().err


def test_cli_has_no_file_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """The package only prints; the repo's skill wrappers own `-o` (ADR-0045)."""
    with pytest.raises(SystemExit) as exit_info:
        _cli(monkeypatch, "model.xml", "--system", "S", "-o", "x.puml")
    assert exit_info.value.code == 2
