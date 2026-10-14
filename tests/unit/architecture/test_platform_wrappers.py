"""build.py and render_diagrams.py shell into the platform venv, never root's (ADR-0002, ADR-0037)."""

import subprocess
import sys
from collections.abc import Callable
from types import ModuleType
from typing import Any

import pytest


@pytest.mark.parametrize("name", ["build", "render_diagrams"])
def test_wrapper_drops_the_root_virtualenv(
    name: str, model_script: Callable[[str], ModuleType], monkeypatch: pytest.MonkeyPatch
) -> None:
    wrapper = model_script(name)
    seen: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.update(kwargs, argv=argv)
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setenv("VIRTUAL_ENV", "/root-venv")
    monkeypatch.setenv("KEEP_ME", "1")
    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", [name])
    assert wrapper.main() == 0
    assert seen["cwd"] == wrapper.PLATFORM
    assert "VIRTUAL_ENV" not in seen["env"]
    assert seen["env"]["KEEP_ME"] == "1"
    assert seen["argv"][:5] == ["poetry", "run", "python", "-m", "modelling_specification.cli"]
