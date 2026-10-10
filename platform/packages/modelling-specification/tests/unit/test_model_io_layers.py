"""model_io.py merges optional model layers (vendored models and the generated
gh-roadmap layer).

Ported from `tests/unit/architecture/test_build_layers.py` (ADR-0037, R2): the logic
these exercise moved from root's `build.py` into `model_io.py`, so the tests move with
it. `model_io` is a real installed module here, so no `importlib`-by-path loading is
needed (unlike the original fixture, which loaded `build.py` as a loose script)."""

from __future__ import annotations

from pathlib import Path

import pytest
from modelling_specification import model_io

ELEMENT = "- {type: Plateau, id: plat-x-1, name: X}\n"


def write_layer(layer: Path, elements: str = ELEMENT) -> None:
    layer.mkdir(parents=True)
    (layer / "elements.yaml").write_text(elements)


def test_gh_roadmap_is_a_model_layer() -> None:
    assert model_io.HERE / "gh-roadmap" in model_io.MODEL_LAYERS
    assert set(model_io.VENDORED_MODELS) <= set(model_io.MODEL_LAYERS)


def test_missing_layer_dir_is_skipped_silently(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(model_io, "MODEL_LAYERS", [tmp_path / "absent"])
    errors: list[str] = []
    assert model_io.load_layers("elements.yaml", errors) == []
    assert errors == []


def test_present_layer_is_merged_through_det_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from pyArchimate import Model

    write_layer(tmp_path / "layer")
    monkeypatch.setattr(model_io, "MODEL_LAYERS", [tmp_path / "layer"])
    errors: list[str] = []
    elements = model_io.load_layers("elements.yaml", errors)
    by_id, _ = model_io.add_elements(Model("t"), elements, errors)
    assert errors == []
    assert by_id["plat-x-1"].uuid == model_io.det_id("plat-x-1")


def test_malformed_layer_file_is_a_build_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_layer(tmp_path / "layer", "type: Plateau\n")
    monkeypatch.setattr(model_io, "MODEL_LAYERS", [tmp_path / "layer"])
    errors: list[str] = []
    assert model_io.load_layers("elements.yaml", errors) == []
    assert any("must be a YAML list" in e for e in errors)


def test_duplicate_id_across_layers_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from pyArchimate import Model

    write_layer(tmp_path / "a")
    write_layer(tmp_path / "b")
    monkeypatch.setattr(model_io, "MODEL_LAYERS", [tmp_path / "a", tmp_path / "b"])
    errors: list[str] = []
    model_io.add_elements(Model("t"), model_io.load_layers("elements.yaml", errors), errors)
    assert errors == ["duplicate element id: plat-x-1"]


def build_with(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, layers: list[Path]) -> tuple[int, list[str]]:
    out = tmp_path / "test-layers-model.xml"
    monkeypatch.setattr(model_io, "MODEL_LAYERS", [*model_io.VENDORED_MODELS, *layers])
    monkeypatch.setattr(model_io, "OUT", out)
    code, errors, _warnings, _result = model_io.write_and_validate()
    return code, errors


def test_committed_layer_replaces_the_runtime_plateaus(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    code, errors = build_with(monkeypatch, tmp_path, [model_io.HERE / "gh-roadmap"])
    assert code == 0
    assert errors == []
    for name in ("elements.yaml", "relationships.yaml", "views.yaml"):
        assert "plat-runtime" not in (model_io.HERE / name).read_text()
        assert "gap-runtime" not in (model_io.HERE / name).read_text()


def test_removed_plateau_names_each_dangling_hand_authored_id(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    write_layer(tmp_path / "layer")  # a layer without the generated Plateaus
    code, errors = build_with(monkeypatch, tmp_path, [tmp_path / "layer"])
    assert code != 0
    text = "\n".join(errors)
    assert "plat-policy-to-oscal-mvp-1" in text
    assert "plat-multi-user-collaboration-2" in text
