"""Unit tests for rendering.py -- diagram batch regeneration and the new
`render_single_view` (T006, FR-013)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from modelling_specification import model_io, rendering


def test_capture_exits_and_writes_stderr_when_the_subprocess_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = subprocess.CompletedProcess(args=["x"], returncode=1, stdout="partial out\n", stderr="boom\n")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)

    with pytest.raises(SystemExit) as exc_info:
        rendering._capture(["x"])

    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert "partial out" in err
    assert "boom" in err


def test_capture_writes_unmapped_type_warnings_but_still_returns_stdout(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = subprocess.CompletedProcess(args=["x"], returncode=0, stdout="@startuml\n@enduml", stderr="note: heads up\n")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)

    out = rendering._capture(["x"])

    assert out == "@startuml\n@enduml\n"
    assert "note: heads up" in capsys.readouterr().err


def test_run_exits_and_writes_stderr_when_the_subprocess_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = subprocess.CompletedProcess(args=["plantuml"], returncode=1, stdout="partial\n", stderr="plantuml died\n")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)

    with pytest.raises(SystemExit) as exc_info:
        rendering._run(["plantuml"])

    assert exc_info.value.code == 2
    err = capsys.readouterr().err
    assert "partial" in err
    assert "plantuml died" in err


def test_run_writes_stderr_warnings_on_success(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = subprocess.CompletedProcess(args=["plantuml"], returncode=0, stdout="", stderr="unmapped type: Foo\n")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)

    rendering._run(["plantuml"])

    assert "unmapped type: Foo" in capsys.readouterr().err


def test_render_diagrams_check_against_the_real_repo_is_up_to_date() -> None:
    code, stale, orphan = rendering.render_diagrams(check=True, svg=True)
    assert (code, stale, orphan) == (0, [], [])


def test_render_diagrams_missing_model_is_an_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rendering, "OUT", tmp_path / "absent.xml")
    code, stale, orphan = rendering.render_diagrams(check=True, svg=True)
    assert (code, stale, orphan) == (2, [], [])


def test_render_single_view_against_a_real_view() -> None:
    svg = rendering.render_single_view("view-stakeholder")
    assert svg.lstrip().startswith("<svg") or svg.lstrip().startswith("<?xml")
    assert "</svg>" in svg


def test_render_single_view_unknown_id_raises() -> None:
    with pytest.raises(rendering.ViewNotFoundError, match="not-a-real-view"):
        rendering.render_single_view("not-a-real-view")


def test_render_single_view_missing_model_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rendering, "OUT", tmp_path / "absent.xml")
    with pytest.raises(rendering.ViewNotFoundError, match="missing"):
        rendering.render_single_view("view-stakeholder")


def test_refresh_model_when_yaml_source_is_newer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    model = tmp_path / "model.xml"
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    model.write_text("<model />")
    source = source_dir / "views.yaml"
    source.write_text("- id: view-stakeholder\n")
    monkeypatch.setattr(rendering, "OUT", model)
    monkeypatch.setattr(model_io, "HERE", source_dir)
    monkeypatch.setattr(model_io, "MODEL_LAYERS", [])
    builds: list[bool] = []

    def rebuild() -> tuple[int, list[str], list[str], dict[str, Any]]:
        builds.append(True)
        model.touch()
        return 0, [], [], {"clean": True, "findings": []}

    monkeypatch.setattr(model_io, "write_and_validate", rebuild)
    rendering._refresh_model_if_sources_changed()

    assert builds == [True]


def test_find_view_falls_through_to_roadmap_and_vendored_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    # The first-party VIEWS file is checked first; a view id that only exists in a
    # later source (or nowhere at all) still raises cleanly rather than matching the
    # wrong entry.
    with pytest.raises(rendering.ViewNotFoundError):
        rendering._find_view("definitely-not-a-view-id")


def test_render_writes_stale_puml_and_renders_svg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive `render()` directly (not via the real views.yaml) to exercise the
    write=True / stale / orphan branches without touching committed diagram files.

    `render()`'s returned paths are always repo-relative (`relative_to(REPO_ROOT)`),
    so the throwaway diagram root must live under the repo, not pytest's `tmp_path`."""
    diagram_root = model_io.REPO_ROOT / "build" / "test_render_rendering_py"
    diagram_root.mkdir(parents=True, exist_ok=True)
    orphan_puml = diagram_root / "orphan.puml"
    orphan_svg = diagram_root / "orphan.svg"
    orphan_puml.write_text("@startuml\nold\n@enduml\n")
    orphan_svg.write_text("<svg></svg>")

    wanted_puml = diagram_root / "fresh.puml"

    def fake_jobs(root: Path) -> list[tuple[Path, list[str]]]:
        assert root == diagram_root
        return [(wanted_puml, ["true"])]  # placeholder cmd; _capture is faked below

    def fake_capture(cmd: list[str]) -> str:
        return "@startuml\nAlice -> Bob: hi\n@enduml\n"

    monkeypatch.setattr(rendering, "_jobs", fake_jobs)
    monkeypatch.setattr(rendering, "_capture", fake_capture)

    try:
        stale, orphan = rendering.render([diagram_root], svg=True, write=True)

        assert stale == [str(wanted_puml.relative_to(model_io.REPO_ROOT))]
        # _orphans() reports (and deletes) the .puml and .svg independently.
        assert set(orphan) == {
            str(orphan_puml.relative_to(model_io.REPO_ROOT)),
            str(orphan_svg.relative_to(model_io.REPO_ROOT)),
        }
        assert wanted_puml.read_text() == "@startuml\nAlice -> Bob: hi\n@enduml\n"
        assert wanted_puml.with_suffix(".svg").exists()
        assert wanted_puml.with_suffix(".svg").read_text().endswith("\n")
        assert not orphan_puml.exists()
        assert not orphan_svg.exists()
    finally:
        shutil.rmtree(diagram_root, ignore_errors=True)


def test_orphans_reports_without_deleting_when_write_is_false() -> None:
    root = model_io.REPO_ROOT / "build" / "test_orphans_write_false"
    root.mkdir(parents=True, exist_ok=True)
    stale_puml = root / "stale.puml"
    stale_puml.write_text("@startuml\n@enduml\n")

    try:
        found = rendering._orphans(root, wanted=set(), write=False)

        assert found == [str(stale_puml.relative_to(model_io.REPO_ROOT))]
        assert stale_puml.exists()  # reported, but not deleted
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_orphans_on_a_missing_root_reports_nothing(tmp_path: Path) -> None:
    assert rendering._orphans(tmp_path / "does-not-exist", wanted=set(), write=True) == []


def test_render_reports_stale_without_writing_when_write_is_false(monkeypatch: pytest.MonkeyPatch) -> None:
    diagram_root = model_io.REPO_ROOT / "build" / "test_render_write_false"
    diagram_root.mkdir(parents=True, exist_ok=True)
    wanted_puml = diagram_root / "fresh.puml"

    def fake_jobs(root: Path) -> list[tuple[Path, list[str]]]:
        return [(wanted_puml, ["true"])]

    def fake_capture(cmd: list[str]) -> str:
        return "@startuml\nAlice -> Bob: hi\n@enduml\n"

    monkeypatch.setattr(rendering, "_jobs", fake_jobs)
    monkeypatch.setattr(rendering, "_capture", fake_capture)

    try:
        stale, orphan = rendering.render([diagram_root], svg=True, write=False)

        assert stale == [str(wanted_puml.relative_to(model_io.REPO_ROOT))]
        assert orphan == []
        assert not wanted_puml.exists()  # write=False never touches disk
    finally:
        shutil.rmtree(diagram_root, ignore_errors=True)


def test_render_skips_svg_normalisation_when_the_svg_was_not_produced(monkeypatch: pytest.MonkeyPatch) -> None:
    """write=True, svg=True, with a stale .puml -- but `_run` (plantuml) is faked as a
    no-op, so the corresponding `.svg` never appears. Exercises the `if svg_path.exists()`
    guard's false branch without depending on a real plantuml invocation's output."""
    diagram_root = model_io.REPO_ROOT / "build" / "test_render_svg_not_produced"
    diagram_root.mkdir(parents=True, exist_ok=True)
    wanted_puml = diagram_root / "fresh.puml"

    def fake_jobs(root: Path) -> list[tuple[Path, list[str]]]:
        return [(wanted_puml, ["true"])]

    def fake_capture(cmd: list[str]) -> str:
        return "@startuml\nAlice -> Bob: hi\n@enduml\n"

    monkeypatch.setattr(rendering, "_jobs", fake_jobs)
    monkeypatch.setattr(rendering, "_capture", fake_capture)
    monkeypatch.setattr(rendering, "_run", lambda cmd: None)

    try:
        stale, _orphan = rendering.render([diagram_root], svg=True, write=True)

        assert stale == [str(wanted_puml.relative_to(model_io.REPO_ROOT))]
        assert wanted_puml.exists()
        assert not wanted_puml.with_suffix(".svg").exists()
    finally:
        shutil.rmtree(diagram_root, ignore_errors=True)


def test_find_view_skips_a_missing_views_file_before_falling_through(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # VIEWS is checked first; "view-stakeholder" actually lives in VIEWPOINT_VIEWS --
    # proves a missing first-choice file is skipped, not treated as a failure.
    monkeypatch.setattr(rendering, "VIEWS", tmp_path / "absent-first-party-views.yaml")

    view = rendering._find_view("view-stakeholder")

    assert view["id"] == "view-stakeholder"


def test_all_views_skips_a_views_file_that_does_not_exist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rendering, "ROADMAP_VIEWS", tmp_path / "absent-roadmap-views.yaml")

    views = rendering._all_views()

    assert any(v.get("id") == "view-stakeholder" for v in views)


def test_refresh_model_is_a_noop_when_the_model_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(rendering, "OUT", tmp_path / "absent.xml")
    rendering._refresh_model_if_sources_changed()  # does not raise


def _stale_model_and_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Common setup for `_refresh_model_if_sources_changed` tests: an existing (stale)
    model plus a newer YAML source, so the function always decides a rebuild is due."""
    model = tmp_path / "model.xml"
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    model.write_text("<model />")
    (source_dir / "views.yaml").write_text("- id: view-stakeholder\n")
    monkeypatch.setattr(rendering, "OUT", model)
    monkeypatch.setattr(model_io, "HERE", source_dir)
    monkeypatch.setattr(model_io, "MODEL_LAYERS", [])
    return model


def test_refresh_model_prints_warnings_from_a_successful_rebuild(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    model = _stale_model_and_sources(monkeypatch, tmp_path)

    def rebuild() -> tuple[int, list[str], list[str], dict[str, Any]]:
        model.touch()
        return 0, [], ["heads up: something to check"], {"clean": True, "findings": []}

    monkeypatch.setattr(model_io, "write_and_validate", rebuild)

    rendering._refresh_model_if_sources_changed()

    assert "warning: heads up: something to check" in capsys.readouterr().err


def test_refresh_model_raises_with_errors_and_findings_when_the_rebuild_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    model = _stale_model_and_sources(monkeypatch, tmp_path)

    def rebuild() -> tuple[int, list[str], list[str], dict[str, Any]]:
        model.touch()
        return 1, ["bad element"], [], {"clean": False, "findings": [{"check": "c1", "detail": "d1"}]}

    monkeypatch.setattr(model_io, "write_and_validate", rebuild)

    with pytest.raises(RuntimeError, match="bad element; c1: d1"):
        rendering._refresh_model_if_sources_changed()


def test_refresh_model_raises_a_fallback_message_when_the_rebuild_gives_no_detail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    model = _stale_model_and_sources(monkeypatch, tmp_path)

    def rebuild() -> tuple[int, list[str], list[str], dict[str, Any] | None]:
        model.touch()
        return 3, [], [], None

    monkeypatch.setattr(model_io, "write_and_validate", rebuild)

    with pytest.raises(RuntimeError, match="model build exited with code 3"):
        rendering._refresh_model_if_sources_changed()


def test_render_single_view_with_max_width_and_no_direction_against_a_real_view() -> None:
    # view-application-structure sets both `no_direction:` and `max_width:` --
    # exercises the `--max-width` branch `_render_svg` otherwise never takes.
    svg = rendering.render_single_view("view-application-structure")
    assert svg.lstrip().startswith("<svg")
    assert "</svg>" in svg


def test_render_svg_raises_runtime_error_when_plantuml_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rendering, "_capture", lambda cmd: "@startuml\n@enduml\n")
    fake = subprocess.CompletedProcess(args=["plantuml"], returncode=1, stdout="", stderr="plantuml blew up")
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: fake)

    with pytest.raises(RuntimeError, match=r"plantuml failed rendering view 'view-stakeholder': plantuml blew up"):
        rendering._render_svg({"id": "view-stakeholder", "name": "Stakeholder"}, "model.xml")


def test_render_candidate_view_raises_preview_error_when_the_model_cannot_be_assembled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(model_io, "preview_model", lambda elements, rels, view: (None, ["boom"]))

    with pytest.raises(rendering.PreviewError, match="boom"):
        rendering.render_candidate_view("view-stakeholder", [], [])


def test_resolve_view_request_by_exact_view_id() -> None:
    result = rendering.resolve_view_request(object_id="view-stakeholder", description=None)
    assert result == {"resolved_view_id": "view-stakeholder", "ambiguous_candidates": []}


def test_resolve_view_request_by_element_id_contained_in_exactly_one_view(monkeypatch: pytest.MonkeyPatch) -> None:
    # Synthetic views/elements -- deliberately decoupled from the real, evolving
    # model so this test doesn't depend on exactly which views a given real id
    # happens to be in scope for today.
    monkeypatch.setattr(
        rendering,
        "_all_views",
        lambda: [
            {"id": "view-a", "name": "A", "members": ["el-1"]},
            {"id": "view-b", "name": "B", "members": ["el-2"]},
        ],
    )
    elements = [{"id": "el-1", "type": "Capability"}, {"id": "el-2", "type": "Capability"}]
    monkeypatch.setattr(model_io, "existing_elements_and_types", lambda: (elements, {"el-1": "Capability"}))

    result = rendering.resolve_view_request(object_id="el-1", description=None)

    assert result == {"resolved_view_id": "view-a", "ambiguous_candidates": []}


def test_resolve_view_request_by_element_id_in_several_views_is_ambiguous(monkeypatch: pytest.MonkeyPatch) -> None:
    # An element included via `include_types` on more than one view is a genuine
    # ambiguity (FR-016) -- "what's on a view" must match add_views's own
    # members/include_types rule, not a narrower members-only one.
    monkeypatch.setattr(
        rendering,
        "_all_views",
        lambda: [
            {"id": "view-a", "name": "A", "include_types": ["Capability"]},
            {"id": "view-b", "name": "B", "include_types": ["Capability"]},
        ],
    )
    elements = [{"id": "cap-1", "type": "Capability"}]
    monkeypatch.setattr(model_io, "existing_elements_and_types", lambda: (elements, {"cap-1": "Capability"}))

    result = rendering.resolve_view_request(object_id="cap-1", description=None)

    assert result["resolved_view_id"] is None
    assert set(result["ambiguous_candidates"]) == {"view-a", "view-b"}


def test_resolve_view_request_by_object_id_with_no_match() -> None:
    result = rendering.resolve_view_request(object_id="not-a-real-id", description=None)
    assert result == {"resolved_view_id": None, "ambiguous_candidates": []}


def test_resolve_view_request_by_description_substring_match() -> None:
    # "stakeholder" alone is ambiguous with the vendored `view-it4it-stakeholder`
    # ("IT4IT: Stakeholder") -- correct FR-016 behaviour, not a bug; "goal
    # realization" is unique to the first-party view.
    result = rendering.resolve_view_request(object_id=None, description="goal realization")
    assert result == {"resolved_view_id": "view-goal-realization", "ambiguous_candidates": []}


def test_resolve_view_request_by_description_ambiguous_across_several_views() -> None:
    result = rendering.resolve_view_request(object_id=None, description="value stream")

    assert result["resolved_view_id"] is None
    assert len(result["ambiguous_candidates"]) > 1
    assert "view-value-stream" in result["ambiguous_candidates"]


def test_resolve_view_request_by_description_with_no_match() -> None:
    result = rendering.resolve_view_request(object_id=None, description="definitely not a real view name")
    assert result == {"resolved_view_id": None, "ambiguous_candidates": []}


def test_resolve_view_request_with_neither_object_id_nor_description() -> None:
    result = rendering.resolve_view_request(object_id=None, description=None)
    assert result == {"resolved_view_id": None, "ambiguous_candidates": []}


def test_jobs_warns_on_view_without_diagram_key(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    views_file = tmp_path / "views.yaml"
    views_file.write_text("- {id: v1, name: V1}\n")

    import modelling_specification.rendering as rendering_mod

    orig_views = rendering_mod.VIEWS
    orig_roadmap = rendering_mod.ROADMAP_VIEWS
    orig_viewpoints = rendering_mod.VIEWPOINT_VIEWS
    try:
        rendering_mod.VIEWS = views_file
        rendering_mod.ROADMAP_VIEWS = tmp_path / "absent-roadmap.yaml"
        rendering_mod.VIEWPOINT_VIEWS = tmp_path / "absent-viewpoints.yaml"
        jobs = rendering_mod._jobs(rendering_mod.DIAGRAMS)
    finally:
        rendering_mod.VIEWS = orig_views
        rendering_mod.ROADMAP_VIEWS = orig_roadmap
        rendering_mod.VIEWPOINT_VIEWS = orig_viewpoints

    # The view with no `diagram:` key contributes no job (only the fixed C4 pair do).
    assert len(jobs) == len(rendering_mod.C4_DIAGRAMS)
    assert "no `diagram:` key" in capsys.readouterr().err


_DIRTY_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" onload="alert(1)">'
    "<script>alert(1)</script><foreignObject><div>x</div></foreignObject>"
    '<a xlink:href="javascript:alert(1)"><text onclick="alert(1)">Safe Label</text></a></svg>'
)


def test_sanitize_svg_strips_active_content_and_keeps_the_drawing() -> None:
    from modelling_specification.rendering import sanitize_svg

    cleaned = sanitize_svg(_DIRTY_SVG)

    for bad in ("script", "foreignObject", "onload", "onclick", "javascript:"):
        assert bad not in cleaned
    assert "Safe Label" in cleaned
    assert cleaned.startswith("<svg")
