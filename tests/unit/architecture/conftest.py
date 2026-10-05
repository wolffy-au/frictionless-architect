"""Fixtures that load the architecture/model scripts by path (they are not a package)."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

MODEL_DIR = Path(__file__).resolve().parents[3] / "architecture" / "model"
FIXTURES = Path(__file__).parent / "fixtures"


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, MODEL_DIR / f"{name}.py")
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def importer() -> ModuleType:
    return load_script("import_gh_roadmap")


@pytest.fixture(scope="session")
def build_mod() -> ModuleType:
    return load_script("build")
