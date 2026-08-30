"""Fixtures for the wiki-librarian tooling tests.

The tools resolve every path relative to the current directory, so each test
runs inside a throwaway repo root built by `wiki_repo` (which also `chdir`s).
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def wiki_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A minimal repo root: `wiki/`, a couple of source docs, cwd set to it."""
    (tmp_path / "wiki").mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A\n\nalpha\n", encoding="utf-8")
    (docs / "b.md").write_text("# B\n\nbravo\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# readme\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path
