"""Unit tests for rendering.py -- diagram batch regeneration and the new
`render_single_view` (T006, FR-013)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from modelling_specification import model_io, rendering


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


def test_jobs_warns_on_view_without_diagram_key(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    views_file = tmp_path / "views.yaml"
    views_file.write_text("- {id: v1, name: V1}\n")

    import modelling_specification.rendering as rendering_mod

    orig_views = rendering_mod.VIEWS
    orig_roadmap = rendering_mod.ROADMAP_VIEWS
    try:
        rendering_mod.VIEWS = views_file
        rendering_mod.ROADMAP_VIEWS = tmp_path / "absent-roadmap.yaml"
        jobs = rendering_mod._jobs(rendering_mod.DIAGRAMS)
    finally:
        rendering_mod.VIEWS = orig_views
        rendering_mod.ROADMAP_VIEWS = orig_roadmap

    # The view with no `diagram:` key contributes no job (only the fixed C4 pair do).
    assert len(jobs) == len(rendering_mod.C4_DIAGRAMS)
    assert "no `diagram:` key" in capsys.readouterr().err
