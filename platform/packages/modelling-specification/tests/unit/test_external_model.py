"""The package against a model that is not this repo's own (ADR-0045).

Paths resolve once, at import, so each test runs the real CLI in a fresh interpreter
with the environment a consuming repo would have.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from modelling_specification import model_io
from modelling_specification.authoring import overrides
from modelling_specification.validation import conventions

ELEMENTS = [
    {"id": "app", "type": "ApplicationComponent", "name": "Acme App"},
    {"id": "svc", "type": "ApplicationService", "name": "Acme Service"},
]
RELATIONSHIPS = [{"type": "Realization", "source": "app", "target": "svc"}]
VIEWS = [{"id": "view-acme", "name": "Acme", "diagram": "acme", "members": ["app", "svc"]}]


def _environ(**overrides_: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("FRICTIONLESS_")}
    return {**env, **overrides_}


def _write_model(model_dir: Path) -> None:
    model_dir.mkdir(parents=True)
    (model_dir / "elements.yaml").write_text(yaml.safe_dump(ELEMENTS))
    (model_dir / "relationships.yaml").write_text(yaml.safe_dump(RELATIONSHIPS))
    (model_dir / "views.yaml").write_text(yaml.safe_dump(VIEWS))


def _cli(env: dict[str, str], cwd: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "modelling_specification.cli", *argv],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    path = tmp_path / "acme" / "model"
    _write_model(path)
    return path


def test_build_validate_and_render_stay_inside_the_other_model(model_dir: Path) -> None:
    env = _environ(FRICTIONLESS_MODEL_DIR=str(model_dir))

    build = _cli(env, model_dir, "build")
    assert build.returncode == 0, build.stderr
    assert "model/frictionless-architect.xml  (2 elements, 1 relationships)" in build.stdout

    render = _cli(env, model_dir, "render", "--no-svg")
    assert render.returncode == 0, render.stderr
    assert (model_dir / "diagrams" / "acme.puml").read_text().count("Acme App") == 1

    assert _cli(env, model_dir, "render", "--check").returncode == 0
    assert _cli(env, model_dir, "validate", str(model_dir / "frictionless-architect.xml")).returncode == 0


def test_no_c4_diagrams_unless_a_system_is_named(model_dir: Path) -> None:
    env = _environ(FRICTIONLESS_MODEL_DIR=str(model_dir))
    assert _cli(env, model_dir, "build").returncode == 0
    assert _cli(env, model_dir, "render", "--no-svg").returncode == 0
    assert not (model_dir / "diagrams" / "c4").exists()


def test_naming_a_system_turns_c4_on_and_names_the_model(model_dir: Path) -> None:
    env = _environ(
        FRICTIONLESS_MODEL_DIR=str(model_dir),
        FRICTIONLESS_C4_SYSTEM="Acme App",
        FRICTIONLESS_MODEL_NAME="acme",
    )
    assert _cli(env, model_dir, "build").returncode == 0
    render = _cli(env, model_dir, "render", "--no-svg")
    assert render.returncode == 0, render.stderr
    assert (model_dir / "acme.xml").exists()
    assert not (model_dir / "frictionless-architect.xml").exists()
    assert "Acme App" in (model_dir / "diagrams" / "c4" / "context.puml").read_text()


def test_this_repos_vendored_models_do_not_leak_in(model_dir: Path) -> None:
    env = _environ(FRICTIONLESS_MODEL_DIR=str(model_dir))
    result = _cli(env, model_dir, "build")
    assert "2 elements" in result.stdout
    assert "it4it" not in (model_dir / "frictionless-architect.xml").read_text()


def test_a_vendored_model_is_discovered_from_its_own_directory(model_dir: Path, tmp_path: Path) -> None:
    vendored = tmp_path / "elsewhere" / "acme-vendor"
    vendored.mkdir(parents=True)
    (vendored / "elements.yaml").write_text(
        yaml.safe_dump([{"id": "acme-vendor-x", "type": "ApplicationComponent", "name": "Vendored"}])
    )
    (vendored / "views.yaml").write_text(
        yaml.safe_dump([{"id": "view-v", "name": "Vendored View", "diagram": "v", "members": ["acme-vendor-x"]}])
    )
    env = _environ(FRICTIONLESS_MODEL_DIR=str(model_dir), FRICTIONLESS_THIRD_PARTY_DIR=str(vendored.parent))
    assert "3 elements" in _cli(env, model_dir, "build").stdout
    render = _cli(env, model_dir, "render", "--no-svg")
    assert render.returncode == 0, render.stderr
    assert (vendored / "diagrams" / "v.puml").exists()
    assert str(vendored / "diagrams" / "v.puml") in render.stdout


def test_defaults_are_this_repos_own_layout() -> None:
    assert model_io.IS_HOME_MODEL
    assert model_io.PROJECT_ROOT == model_io.REPO_ROOT
    assert model_io.HERE == model_io.REPO_ROOT / "architecture" / "model"
    assert model_io.OUT == model_io.HERE / "frictionless-architect.xml"
    assert [p.name for p in model_io.VENDORED_MODELS] == ["it4it"]


def test_source_checkout_is_none_outside_a_checkout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        model_io, "__file__", str(tmp_path / "site-packages" / "modelling_specification" / "model_io.py")
    )
    assert model_io._source_checkout() is None


def test_env_path_prefers_the_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FRICTIONLESS_TEST_PATH", str(tmp_path))
    assert model_io._env_path("FRICTIONLESS_TEST_PATH", Path("/fallback")) == tmp_path.resolve()


@pytest.mark.parametrize("value", [None, ""])
def test_env_path_falls_back(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    monkeypatch.delenv("FRICTIONLESS_TEST_PATH", raising=False)
    if value is not None:
        monkeypatch.setenv("FRICTIONLESS_TEST_PATH", value)
    assert model_io._env_path("FRICTIONLESS_TEST_PATH", Path("/fallback")) == Path("/fallback")


def test_project_relative_keeps_a_path_outside_the_project_whole(tmp_path: Path) -> None:
    assert model_io.project_relative(model_io.PROJECT_ROOT / "a" / "b") == str(Path("a") / "b")
    assert model_io.project_relative(tmp_path) == str(tmp_path)


def test_first_party_exclusion_follows_the_vendored_directories(monkeypatch: pytest.MonkeyPatch) -> None:
    rule = {"params": {"first_party_only": True}}
    monkeypatch.setattr(model_io, "VENDORED_MODELS", [Path("third_party/acme")])
    assert conventions._is_excluded_first_party(rule, "acme-thing")
    assert not conventions._is_excluded_first_party(rule, "it4it-thing")
    monkeypatch.setattr(model_io, "VENDORED_MODELS", [])
    assert not conventions._is_excluded_first_party(rule, "acme-thing")


def test_override_adr_creates_a_missing_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    adr_dir = tmp_path / "docs" / "adr"
    monkeypatch.setattr(overrides, "ADR_DIR", adr_dir)
    assert overrides.draft_override("duplicate", "detail", None, "summary")["id"] == "0001"
    assert len(list(adr_dir.glob("0001-*.md"))) == 1
