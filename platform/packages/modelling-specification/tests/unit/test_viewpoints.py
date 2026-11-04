"""Unit tests for modelling_specification.viewpoints (ADR-0045).

Authority is reference/archi-viewpoints.xml (verbatim Archi viewpoint file);
these lock in the parse + Archi allow-list semantics.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from modelling_specification import viewpoints
from modelling_specification.model_io import REPO_ROOT
from pyArchimate import ArchiType, Model


def test_parses_the_archi_viewpoint_file() -> None:
    vps = viewpoints.load_viewpoints()
    # Archi's ids (not the spec's prose names).
    for slug in ("stakeholder", "strategy", "capability", "value_stream", "application_cooperation", "layered"):
        assert slug in vps, slug
    vp = viewpoints.get_viewpoint("value_stream")
    assert vp is not None
    assert vp["name"] == "Value Stream"


def test_value_stream_allow_set_matches_archi() -> None:
    vp = viewpoints.get_viewpoint("value_stream")
    assert vp is not None
    assert vp["elements"] == {"Capability", "Outcome", "Stakeholder", "ValueStream"}
    assert vp["relationships_unrestricted"] is True


def test_collection_tokens_are_expanded() -> None:
    # application_cooperation = $ApplicationElements$ + Location
    vp = viewpoints.get_viewpoint("application_cooperation")
    assert vp is not None
    assert {"ApplicationComponent", "ApplicationFunction", "DataObject", "Location"} <= vp["elements"]
    assert "$ApplicationElements$" not in vp["elements"]
    # strategy = $StrategyElements$ + Outcome
    strategy_vp = viewpoints.get_viewpoint("strategy")
    assert strategy_vp is not None
    assert strategy_vp["elements"] == {
        "Resource",
        "Capability",
        "ValueStream",
        "CourseOfAction",
        "Outcome",
    }


def test_layered_is_unrestricted() -> None:
    vp = viewpoints.get_viewpoint("layered")
    assert vp is not None
    assert vp["elements_unrestricted"]
    assert vp["relationships_unrestricted"]
    assert viewpoints.check_conformance(vp, ["BusinessActor", "Node", "Gap"], ["Flow"]) == []


def test_get_viewpoint_unknown_is_none() -> None:
    assert viewpoints.get_viewpoint("capability_map") is None  # spec name, not Archi's slug
    assert viewpoints.get_viewpoint("nope") is None


def test_check_conformance_clean_and_dirty() -> None:
    vp = viewpoints.get_viewpoint("value_stream")
    assert vp is not None
    assert viewpoints.check_conformance(vp, ["Capability", "ValueStream", "Outcome"], ["Serving"]) == []
    findings = viewpoints.check_conformance(vp, ["Capability", "Goal"], ["Serving"])
    assert any("Goal" in f for f in findings)


def test_junction_and_grouping_always_allowed() -> None:
    vp = viewpoints.get_viewpoint("stakeholder")  # a restricted element set
    assert vp is not None
    assert not vp["elements_unrestricted"]
    assert viewpoints.check_conformance(vp, ["Stakeholder", "Grouping", "Junction"], []) == []


def test_guidance_overlay_is_attached() -> None:
    vp = viewpoints.get_viewpoint("value_stream")
    assert vp is not None
    assert vp.get("abstraction") == "overview"
    assert "deciding" in vp.get("purpose", [])


@pytest.mark.parametrize("cmd", [["list"], ["show", "value_stream"]])
def test_cli_smoke(capsys: pytest.CaptureFixture[str], cmd: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["viewpoints.py", *cmd])
    assert viewpoints.main() == 0
    assert capsys.readouterr().out.strip()


def test_every_view_in_this_repos_model_declares_a_known_viewpoint() -> None:
    known = {*viewpoints.known_slugs(), viewpoints.UNRESTRICTED}
    model_dir = REPO_ROOT / "architecture" / "model"
    views = [
        v for name in ("views.yaml", "views-viewpoints.yaml") for v in yaml.safe_load((model_dir / name).read_text())
    ]
    unknown = {v["id"]: v["viewpoint"] for v in views if v.get("viewpoint") and v["viewpoint"] not in known}
    assert not unknown


def test_unknown_collection_token_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown collection token"):
        viewpoints._expand("$NotACollection$")


def test_plain_concept_expands_to_itself() -> None:
    assert viewpoints._expand("Capability") == ["Capability"]


def test_guidance_is_empty_when_the_overlay_file_is_absent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    viewpoints._load_guidance.cache_clear()
    monkeypatch.setattr(viewpoints, "GUIDANCE_YAML", tmp_path / "absent.yaml")
    try:
        assert viewpoints._load_guidance() == {}
    finally:
        viewpoints._load_guidance.cache_clear()


def test_a_rootless_viewpoint_entry_without_id_is_skipped(tmp_path: Path) -> None:
    xml = tmp_path / "vp.xml"
    xml.write_text('<viewpoints><viewpoint><name>None</name></viewpoint><viewpoint id="ok"/></viewpoints>')
    viewpoints.load_viewpoints.cache_clear()
    try:
        assert viewpoints.known_slugs(str(xml)) == ["ok"]
        assert viewpoints.get_viewpoint("ok", str(xml))["name"] == "ok"  # type: ignore[index]
    finally:
        viewpoints.load_viewpoints.cache_clear()


def test_restricted_relationship_set_flags_a_stray_relationship() -> None:
    vp = {"slug": "x", "elements": set(), "relationships": {"Serving"}}
    assert viewpoints.check_conformance(vp, ["Goal"], ["Serving", "Flow"]) == [
        "relationship type 'Flow' is not part of the 'x' viewpoint"
    ]


def _cli(monkeypatch: pytest.MonkeyPatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["viewpoints", *argv])
    return viewpoints.main()


def test_cli_list(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert _cli(monkeypatch, "list") == 0
    assert "value_stream" in capsys.readouterr().out


def test_cli_show(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert _cli(monkeypatch, "show", "value_stream") == 0
    out = capsys.readouterr().out
    assert "Value Stream" in out
    assert "always allowed" in out


def test_cli_show_unknown_slug(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert _cli(monkeypatch, "show", "nope") == 2
    assert "unknown viewpoint" in capsys.readouterr().err


@pytest.fixture
def model_with_goal_view(tmp_path: Path) -> str:
    model = Model("m")
    goal = model.add(ArchiType.Goal, "Be good")
    view: Any = model.add(ArchiType.View, "Goals")
    view.add(ref=goal.uuid, x=10, y=10, w=120, h=55)
    path = tmp_path / "m.xml"
    model.write(str(path))
    return str(path)


@pytest.mark.parametrize(
    ("viewpoint", "code", "expected"),
    [("motivation", 0, "conforms"), ("value_stream", 1, "does NOT conform"), ("nope", 2, "")],
)
def test_cli_check(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    model_with_goal_view: str,
    viewpoint: str,
    code: int,
    expected: str,
) -> None:
    assert _cli(monkeypatch, "check", model_with_goal_view, "--view", "Goals", "--viewpoint", viewpoint) == code
    assert expected in capsys.readouterr().out


def test_cli_check_unknown_view(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], model_with_goal_view: str
) -> None:
    assert _cli(monkeypatch, "check", model_with_goal_view, "--view", "Nope", "--viewpoint", "motivation") == 2
    assert "no view named" in capsys.readouterr().err
