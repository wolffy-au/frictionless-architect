"""Unit tests for the model-archimate skill's viewpoints.py.

Authority is reference/archi-viewpoints.xml (verbatim Archi viewpoint file);
these lock in the parse + Archi allow-list semantics.
"""

from __future__ import annotations

import pytest
import viewpoints


def test_parses_the_archi_viewpoint_file() -> None:
    vps = viewpoints.load_viewpoints()
    # Archi's ids (not the spec's prose names).
    for slug in ("stakeholder", "strategy", "capability", "value_stream", "application_cooperation", "layered"):
        assert slug in vps, slug
    assert viewpoints.get_viewpoint("value_stream")["name"] == "Value Stream"


def test_value_stream_allow_set_matches_archi() -> None:
    vp = viewpoints.get_viewpoint("value_stream")
    assert vp["elements"] == {"Capability", "Outcome", "Stakeholder", "ValueStream"}
    assert vp["relationships_unrestricted"] is True


def test_collection_tokens_are_expanded() -> None:
    # application_cooperation = $ApplicationElements$ + Location
    vp = viewpoints.get_viewpoint("application_cooperation")
    assert {"ApplicationComponent", "ApplicationFunction", "DataObject", "Location"} <= vp["elements"]
    assert "$ApplicationElements$" not in vp["elements"]
    # strategy = $StrategyElements$ + Outcome
    assert viewpoints.get_viewpoint("strategy")["elements"] == {
        "Resource",
        "Capability",
        "ValueStream",
        "CourseOfAction",
        "Outcome",
    }


def test_layered_is_unrestricted() -> None:
    vp = viewpoints.get_viewpoint("layered")
    assert vp["elements_unrestricted"] and vp["relationships_unrestricted"]
    assert viewpoints.check_conformance(vp, ["BusinessActor", "Node", "Gap"], ["Flow"]) == []


def test_get_viewpoint_unknown_is_none() -> None:
    assert viewpoints.get_viewpoint("capability_map") is None  # spec name, not Archi's slug
    assert viewpoints.get_viewpoint("nope") is None


def test_check_conformance_clean_and_dirty() -> None:
    vp = viewpoints.get_viewpoint("value_stream")
    assert viewpoints.check_conformance(vp, ["Capability", "ValueStream", "Outcome"], ["Serving"]) == []
    findings = viewpoints.check_conformance(vp, ["Capability", "Goal"], ["Serving"])
    assert any("Goal" in f for f in findings)


def test_junction_and_grouping_always_allowed() -> None:
    vp = viewpoints.get_viewpoint("stakeholder")  # a restricted element set
    assert not vp["elements_unrestricted"]
    assert viewpoints.check_conformance(vp, ["Stakeholder", "Grouping", "Junction"], []) == []


def test_guidance_overlay_is_attached() -> None:
    vp = viewpoints.get_viewpoint("value_stream")
    assert vp.get("abstraction") == "overview"
    assert "deciding" in vp.get("purpose", [])


@pytest.mark.parametrize("cmd", [["list"], ["show", "value_stream"]])
def test_cli_smoke(capsys: pytest.CaptureFixture[str], cmd: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["viewpoints.py", *cmd])
    assert viewpoints.main() == 0
    assert capsys.readouterr().out.strip()
