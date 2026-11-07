"""modelling_specification.puml: ArchiMate-to-PlantUML projection (ADR-0045).

Rendering runs this module as a subprocess, so these call it in-process. The golden
test pins it to the diagrams committed under architecture/model/diagrams/.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from modelling_specification import model_io, puml, rendering
from modelling_specification.model_io import REPO_ROOT
from pyArchimate import ArchiType, Model

BUILT_MODEL = REPO_ROOT / "architecture" / "model" / "frictionless-architect.xml"
DIAGRAMS = REPO_ROOT / "architecture" / "model" / "diagrams"


def _write(model: Model, tmp_path: Path) -> str:
    path = tmp_path / "m.xml"
    model.write(str(path))
    return str(path)


def _on_view(model: Model, name: str, *elements: Any) -> Any:
    view: Any = model.add(ArchiType.View, name)
    nodes = [view.add(ref=e.uuid, x=10 + 150 * i, y=10, w=120, h=55) for i, e in enumerate(elements)]
    return view, nodes


def test_committed_diagram_is_reproduced_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    view = next(v for v in yaml.safe_load((model_io.HERE / "views.yaml").read_text()) if not v.get("split_by"))
    monkeypatch.chdir(REPO_ROOT)
    args = {"no_direction": set(view.get("no_direction", [])), "max_width": view.get("max_width")}
    text, _ = puml.generate(rendering.MODEL_REL, view["name"], **args)
    assert text.rstrip("\n") + "\n" == (DIAGRAMS / f"{view['diagram']}.puml").read_text()


def test_whole_model_without_a_view_lists_every_element(tmp_path: Path) -> None:
    model = Model("whole")
    model.add(ArchiType.Goal, 'Say "hi"')
    text, warnings = puml.generate(_write(model, tmp_path), None)
    assert "Motivation_Goal" in text
    assert "Say 'hi'" in text
    assert "title whole" in text
    assert not warnings


def test_closed_work_package_is_struck_through(tmp_path: Path) -> None:
    model = Model("m")
    model.add(ArchiType.WorkPackage, "Done").prop("gh-state", "closed")
    text, _ = puml.generate(_write(model, tmp_path), None)
    assert " --Done--" in text


def test_composition_nests_and_other_relationships_stay_arrows(tmp_path: Path) -> None:
    model = Model("m")
    whole = model.add(ArchiType.ApplicationComponent, "Whole")
    part = model.add(ArchiType.ApplicationComponent, "Part")
    service = model.add(ArchiType.ApplicationService, "Service")
    model.add_relationship(ArchiType.Composition, whole, part)
    model.add_relationship(ArchiType.Realization, part, service, name='the "real" one')
    text, _ = puml.generate(_write(model, tmp_path), None)
    assert text.index("Whole") < text.index("Part") < text.index("}")
    assert "Rel_Composition" not in text
    assert "Rel_Realization" in text
    assert "the 'real' one" in text


def test_competing_parents_prefer_the_lone_composition(tmp_path: Path) -> None:
    model = Model("m")
    owner = model.add(ArchiType.ApplicationComponent, "Owner")
    sharer = model.add(ArchiType.ApplicationComponent, "Sharer")
    part = model.add(ArchiType.ApplicationComponent, "Part")
    model.add_relationship(ArchiType.Aggregation, sharer, part)
    model.add_relationship(ArchiType.Composition, owner, part)
    text, _ = puml.generate(_write(model, tmp_path), None)
    assert "Rel_Aggregation" in text
    assert "Rel_Composition" not in text


def test_ambiguous_parents_stay_arrows(tmp_path: Path) -> None:
    model = Model("m")
    first = model.add(ArchiType.ApplicationComponent, "First")
    second = model.add(ArchiType.ApplicationComponent, "Second")
    part = model.add(ArchiType.ApplicationComponent, "Part")
    model.add_relationship(ArchiType.Aggregation, first, part)
    model.add_relationship(ArchiType.Aggregation, second, part)
    text, _ = puml.generate(_write(model, tmp_path), None)
    assert text.count("Rel_Aggregation") == 2


def test_containment_cycle_keeps_one_arrow(tmp_path: Path) -> None:
    model = Model("m")
    a = model.add(ArchiType.ApplicationComponent, "A")
    b = model.add(ArchiType.ApplicationComponent, "B")
    model.add_relationship(ArchiType.Aggregation, a, b)
    model.add_relationship(ArchiType.Aggregation, b, a)
    text, _ = puml.generate(_write(model, tmp_path), None)
    assert text.count("Rel_Aggregation") == 1


def test_access_type_picks_its_macro_suffix(tmp_path: Path) -> None:
    model = Model("m")
    app = model.add(ArchiType.ApplicationComponent, "App")
    data = model.add(ArchiType.DataObject, "Data")
    model.add_relationship(ArchiType.Access, app, data, access_type="Read")
    text, _ = puml.generate(_write(model, tmp_path), None)
    assert "Rel_Access_r" in text


def test_no_direction_drops_the_layout_hint(tmp_path: Path) -> None:
    model = Model("m")
    a = model.add(ArchiType.ApplicationComponent, "A")
    b = model.add(ArchiType.ApplicationService, "B")
    model.add_relationship(ArchiType.Serving, b, a)
    path = _write(model, tmp_path)
    hinted, _ = puml.generate(path, None)
    plain, _ = puml.generate(path, None, no_direction={"Serving"})
    assert "Rel_Serving_" in hinted
    assert "Rel_Serving_" not in plain
    assert "Rel_Serving(" in plain


def test_max_width_scales(tmp_path: Path) -> None:
    model = Model("m")
    model.add(ArchiType.Goal, "G")
    text, _ = puml.generate(_write(model, tmp_path), None, max_width=800)
    assert "scale max 800 width" in text


def _context_model(tmp_path: Path) -> str:
    model = Model("m")
    mine = model.add(ArchiType.ApplicationComponent, "Mine")
    mine.prop("context", "billing")
    neighbour = model.add(ArchiType.ApplicationService, "Neighbour")
    neighbour.prop("context", "other")
    stranger = model.add(ArchiType.ApplicationService, "Stranger")
    stranger.prop("context", "other")
    other = model.add(ArchiType.ApplicationComponent, "Other")
    other.prop("context", "other")
    near = model.add_relationship(ArchiType.Serving, neighbour, mine)
    far = model.add_relationship(ArchiType.Serving, stranger, other)
    view, nodes = _on_view(model, "Everything", mine, neighbour, stranger, other)
    view.add_connection(ref=near.uuid, source=nodes[1], target=nodes[0])
    view.add_connection(ref=far.uuid, source=nodes[2], target=nodes[3])
    return _write(model, tmp_path)


def test_context_keeps_its_neighbourhood_only(tmp_path: Path) -> None:
    text, _ = puml.generate(_context_model(tmp_path), "Everything", context="billing")
    assert "title Everything — billing" in text
    assert "Mine" in text
    assert "Neighbour" in text
    assert "Stranger" not in text


def test_view_without_context_keeps_everything(tmp_path: Path) -> None:
    text, _ = puml.generate(_context_model(tmp_path), "Everything")
    assert "Stranger" in text


def test_context_requires_a_view(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--context requires --view"):
        puml.generate(str(tmp_path / "unused.xml"), None, context="billing")


def _cli(monkeypatch: pytest.MonkeyPatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["puml", *argv])
    return puml.main()


def test_view_concepts_skips_nodes_without_a_concept_and_walks_nested_ones() -> None:
    nested = SimpleNamespace(concept=SimpleNamespace(uuid="inner"), nodes=[])
    outer = SimpleNamespace(concept=None, nodes=[nested])
    assert puml._view_concepts(SimpleNamespace(nodes=[outer])) == {"inner"}


def test_nesting_ignores_self_loops_and_elements_off_the_diagram() -> None:
    element = SimpleNamespace(uuid="a")
    off_diagram = SimpleNamespace(uuid="b")
    self_loop = SimpleNamespace(type="Composition", source=element, target=element)
    outward = SimpleNamespace(type="Composition", source=element, target=off_diagram)
    assert puml._nest_tree([element], [self_loop, outward]) == ({}, set(), set())


def test_access_without_a_type_uses_the_plain_macro(tmp_path: Path) -> None:
    model = Model("m")
    app = model.add(ArchiType.ApplicationComponent, "App")
    data = model.add(ArchiType.DataObject, "Data")
    model.add_relationship(ArchiType.Access, app, data)
    text, _ = puml.generate(_write(model, tmp_path), None)
    assert "Rel_Access" in text
    assert "Rel_Access_r" not in text


def test_cli_prints_to_stdout_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    model = Model("m")
    model.add(ArchiType.Goal, "G")
    assert _cli(monkeypatch, _write(model, tmp_path)) == 0
    assert "@enduml" in capsys.readouterr().out


def test_cli_reports_an_unknown_view(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    model = Model("m")
    model.add(ArchiType.Goal, "G")
    assert _cli(monkeypatch, _write(model, tmp_path), "--view", "Nope") == 2
    assert "no view named" in capsys.readouterr().err


def test_unmapped_types_fall_back_and_warn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delitem(puml.ELEMENT_MACRO, "Goal")
    monkeypatch.delitem(puml.REL_MACRO, "Association")
    model = Model("m")
    goal = model.add(ArchiType.Goal, "G")
    other = model.add(ArchiType.Outcome, "O")
    model.add_relationship(ArchiType.Association, goal, other)
    text, warnings = puml.generate(_write(model, tmp_path), None)
    assert 'rectangle "G"' in text
    assert " --> " in text
    assert len(warnings) == 2
    assert _cli(monkeypatch, str(tmp_path / "m.xml")) == 0
    assert "warning: unmapped" in capsys.readouterr().err


def test_cli_has_no_file_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """The package only prints; the repo's skill wrappers own `-o` (ADR-0045)."""
    with pytest.raises(SystemExit) as exit_info:
        _cli(monkeypatch, "model.xml", "-o", "x.puml")
    assert exit_info.value.code == 2
