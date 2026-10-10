"""Fixtures that load `architecture/model/import_gh_roadmap.py` by path.

It stays a loose root script (R2 only ports `build.py`/`render_diagrams.py`/the skill's
`validate.py` into this package), so tests that need it load it the same way root's own
`tests/unit/architecture/conftest.py` does."""

import importlib.util
import sys
from types import ModuleType

import pytest
from modelling_specification.model_io import REPO_ROOT

MODEL_DIR = REPO_ROOT / "architecture" / "model"


@pytest.fixture(scope="session")
def importer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("import_gh_roadmap", MODEL_DIR / "import_gh_roadmap.py")
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["import_gh_roadmap"] = mod
    spec.loader.exec_module(mod)
    return mod
