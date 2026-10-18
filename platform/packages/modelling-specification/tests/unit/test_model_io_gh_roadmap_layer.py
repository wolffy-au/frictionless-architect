"""model_io.py builds and validates against the generated gh-roadmap layer.

Ported from `tests/unit/architecture/test_import_gh_roadmap.py`'s two `build_mod`-based
tests (ADR-0037, R2): in-process building-and-validating a layer only works from inside
this package now that `build.py`'s logic lives here, not in a root-importable module
(`architecture/model/build.py` is a thin wrapper with no `MODEL_LAYERS`/`OUT` globals to
monkeypatch any more) -- so the "does the importer's output build cleanly" assertion
moved with it. `import_gh_roadmap.py` itself stays a root script (out of this feature's
scope) and is loaded by path, same as root's own test suite does.

Fixture JSON lives at the repo root (`tests/unit/architecture/fixtures/`) and is read
directly rather than copied, to avoid two copies of the same GH API fixture data."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from modelling_specification import model_io
from modelling_specification.model_io import REPO_ROOT

FIXTURES = REPO_ROOT / "tests" / "unit" / "architecture" / "fixtures"
REPO = "o/r"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text()


def make_stub(
    milestones: str | None = None,
    releases: str | None = None,
    issues: list[str] | None = None,
) -> Callable[[list[str]], str]:
    """A `run_gh` stand-in answering from recorded payloads; issue pages are served in order."""
    pages = iter(issues if issues is not None else [fixture_text("gh_issues.json")])

    def stub(args: list[str]) -> str:
        joined = " ".join(args)
        if "graphql" in args:
            return next(pages)
        if "milestones" in joined:
            return milestones if milestones is not None else fixture_text("gh_milestones.json")
        if "releases" in joined:
            return releases if releases is not None else fixture_text("gh_releases.json")
        raise AssertionError(f"unexpected gh call: {args}")

    return stub


def issues_with_milestone_7_issue() -> list[str]:
    """gh_issues.json plus one issue under milestone 7, so the importer emits
    del-architecture-strategy-mvp-7-unreleased (needed by the hand-authored
    wp-vendor-it4it Realization onto that Deliverable)."""
    page = json.loads(fixture_text("gh_issues.json"))
    page["data"]["repository"]["issues"]["nodes"].append(
        {
            "number": 200,
            "title": "Architecture strategy placeholder",
            "state": "CLOSED",
            "closedAt": "2026-09-30T10:00:00Z",
            "url": "https://github.com/o/r/issues/200",
            "milestone": {"number": 7},
            "parent": None,
            "blockedBy": {"nodes": []},
        }
    )
    return [json.dumps(page)]


def issues_with_dependencies() -> list[str]:
    page = json.loads(fixture_text("gh_issues_dependencies.json"))
    page["data"]["repository"]["issues"]["nodes"].append(
        {
            "number": 200,
            "title": "Architecture strategy placeholder",
            "state": "CLOSED",
            "closedAt": "2026-09-30T10:00:00Z",
            "url": "https://github.com/o/r/issues/200",
            "milestone": {"number": 7},
            "parent": None,
            "blockedBy": {"nodes": []},
        }
    )
    return [json.dumps(page)]


def _build_layer_and_check(
    importer: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    stub: Callable[[list[str]], str],
) -> tuple[int, list[str]]:
    layer_dir = tmp_path / "gh-roadmap"
    assert importer.main(["--repo", REPO], run_gh=stub, layer_dir=layer_dir) == 0
    monkeypatch.setattr(model_io, "MODEL_LAYERS", [*model_io.VENDORED_MODELS, layer_dir])
    monkeypatch.setattr(model_io, "OUT", tmp_path / "test-gh-roadmap-model.xml")
    code, errors, _warnings, _result = model_io.write_and_validate()
    return code, errors


def test_fixture_layer_builds_and_validates(
    importer: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The hand-authored layer references plat-architecture-strategy-mvp-7 and
    # plat-solution-design-mvp-8 (and their -unreleased Deliverables) directly, plus
    # plat-architecture-strategy-future-13 (the Gap to architecture-strategy-future), so
    # the stubbed milestone set must cover those numbers too, not just 1 and 2, and at
    # least one in-scope issue must target milestone 7 so its Deliverable is created.
    stub = make_stub(milestones=fixture_text("gh_milestones_full.json"), issues=issues_with_milestone_7_issue())
    code, errors = _build_layer_and_check(importer, monkeypatch, tmp_path, stub)
    assert errors == []
    assert code == 0


def test_dependency_layer_still_validates(
    importer: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    stub = make_stub(milestones=fixture_text("gh_milestones_full.json"), issues=issues_with_dependencies())
    code, errors = _build_layer_and_check(importer, monkeypatch, tmp_path, stub)
    assert errors == []
    assert code == 0
