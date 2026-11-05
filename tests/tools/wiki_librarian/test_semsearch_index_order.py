"""semsearch's indexing order: a file's digest must never exist ahead of its chunks,
or an interrupted run leaves it marked as indexed with nothing behind it."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
import semsearch
from semsearch import Chunk


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(semsearch, "REPO", tmp_path)
    monkeypatch.setattr(semsearch, "DB_PATH", tmp_path / "index.sqlite")
    return tmp_path


def _chunk(path: str, line: int) -> Chunk:
    return Chunk(path, line, line, "", f"text {line}")


def _files(db: sqlite3.Connection) -> set[str]:
    return {row[0] for row in db.execute("SELECT path FROM files")}


def _dying_after(count: int) -> Iterator[bytes]:
    yield from [b"v"] * count
    raise KeyboardInterrupt


def test_only_files_with_all_their_chunks_get_a_digest(repo: Path) -> None:
    db = semsearch.connect()
    chunks = [_chunk("a.md", 1), _chunk("a.md", 2), _chunk("b.md", 1), _chunk("b.md", 2)]

    with pytest.raises(KeyboardInterrupt):
        semsearch._store_embedded(db, chunks, _dying_after(3), {"a.md": "da", "b.md": "db"})
    db.commit()

    assert _files(db) == {"a.md"}


def test_a_file_left_incomplete_is_forgotten_and_redone(repo: Path) -> None:
    page = repo / "a.md"
    page.write_text("## Section\n\nbody\n", encoding="utf-8")
    db = semsearch.connect()
    db.execute("INSERT INTO files(path, digest) VALUES('a.md', 'old')")
    db.execute("INSERT INTO chunks(path, start_line, end_line, heading, text, vector) VALUES('a.md',1,1,'','x',x'00')")

    semsearch._clear_for_reindex(db, [(page, "new")], [_chunk("a.md", 1)])

    assert _files(db) == set()
    assert db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0


def test_a_file_with_nothing_to_embed_is_recorded_straight_away(repo: Path) -> None:
    page = repo / "__init__.py"
    page.write_text("", encoding="utf-8")
    db = semsearch.connect()

    semsearch._clear_for_reindex(db, [(page, "digest")], [])

    assert _files(db) == {"__init__.py"}


def test_a_recorded_file_with_no_chunks_but_real_content_needs_indexing(repo: Path) -> None:
    page = repo / "a.md"
    page.write_text("## Section\n\nbody\n", encoding="utf-8")

    assert semsearch._needs_index(page, "a.md", "same", {"a.md": "same"}, set(), force=False)


def test_a_legitimately_empty_file_is_not_reindexed_forever(repo: Path) -> None:
    page = repo / "__init__.py"
    page.write_text("", encoding="utf-8")

    assert not semsearch._needs_index(page, "__init__.py", "same", {"__init__.py": "same"}, set(), force=False)
