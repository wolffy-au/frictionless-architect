"""build.py merges optional model layers (vendored models and the generated gh-roadmap layer)."""

from pathlib import Path
from types import ModuleType

import pytest
from pyArchimate import Model

ELEMENT = "- {type: Plateau, id: plat-x-1, name: X}\n"


def write_layer(layer: Path, elements: str = ELEMENT) -> None:
    layer.mkdir(parents=True)
    (layer / "elements.yaml").write_text(elements)


def test_gh_roadmap_is_a_model_layer(build_mod: ModuleType) -> None:
    assert build_mod.HERE / "gh-roadmap" in build_mod.MODEL_LAYERS
    assert set(build_mod.VENDORED_MODELS) <= set(build_mod.MODEL_LAYERS)


def test_missing_layer_dir_is_skipped_silently(
    build_mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(build_mod, "MODEL_LAYERS", [tmp_path / "absent"])
    errors: list[str] = []
    assert build_mod.load_layers("elements.yaml", errors) == []
    assert errors == []


def test_present_layer_is_merged_through_det_id(
    build_mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_layer(tmp_path / "layer")
    monkeypatch.setattr(build_mod, "MODEL_LAYERS", [tmp_path / "layer"])
    errors: list[str] = []
    elements = build_mod.load_layers("elements.yaml", errors)
    by_id, _ = build_mod.add_elements(Model("t"), elements, errors)
    assert errors == []
    assert by_id["plat-x-1"].uuid == build_mod.det_id("plat-x-1")


def test_malformed_layer_file_is_a_build_error(
    build_mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_layer(tmp_path / "layer", "type: Plateau\n")
    monkeypatch.setattr(build_mod, "MODEL_LAYERS", [tmp_path / "layer"])
    errors: list[str] = []
    assert build_mod.load_layers("elements.yaml", errors) == []
    assert any("must be a YAML list" in e for e in errors)


def test_duplicate_id_across_layers_errors(
    build_mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    write_layer(tmp_path / "a")
    write_layer(tmp_path / "b")
    monkeypatch.setattr(build_mod, "MODEL_LAYERS", [tmp_path / "a", tmp_path / "b"])
    errors: list[str] = []
    build_mod.add_elements(Model("t"), build_mod.load_layers("elements.yaml", errors), errors)
    assert errors == ["duplicate element id: plat-x-1"]


def build_with(build_mod: ModuleType, monkeypatch: pytest.MonkeyPatch, layers: list[Path]) -> int:
    out = build_mod.HERE.parents[1] / "build" / "test-layers-model.xml"  # build.py prints OUT relative to the repo
    out.parent.mkdir(exist_ok=True)
    monkeypatch.setattr(build_mod, "MODEL_LAYERS", [*build_mod.VENDORED_MODELS, *layers])
    monkeypatch.setattr(build_mod, "OUT", out)
    try:
        return int(build_mod.main())
    finally:
        out.unlink(missing_ok=True)


def test_committed_layer_replaces_the_runtime_plateaus(
    build_mod: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert build_with(build_mod, monkeypatch, [build_mod.HERE / "gh-roadmap"]) == 0
    assert "VALID" in capsys.readouterr().out
    for name in ("elements.yaml", "relationships.yaml", "views.yaml"):
        assert "plat-runtime" not in (build_mod.HERE / name).read_text()
        assert "gap-runtime" not in (build_mod.HERE / name).read_text()


def test_removed_plateau_names_each_dangling_hand_authored_id(
    build_mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_layer(tmp_path / "layer")  # a layer without the generated Plateaus
    assert build_with(build_mod, monkeypatch, [tmp_path / "layer"]) != 0
    output = capsys.readouterr()
    text = output.out + output.err
    assert "plat-policy-to-oscal-mvp-1" in text
    assert "plat-multi-user-collaboration-2" in text
