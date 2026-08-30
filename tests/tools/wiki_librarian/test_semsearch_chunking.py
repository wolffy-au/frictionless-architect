"""Unit tests for semsearch's pure chunking helpers (no embedding / DB)."""

from __future__ import annotations

from pathlib import Path

import pytest
import semsearch


@pytest.mark.parametrize(
    "line, expected",
    [
        ("2026-08-30", "2026-08-30"),
        ("15 Nov 2024", "15 Nov 2024"),
        ("2/1/25, 4:27 pm - Someone", "2/1/25"),
        ("just prose", None),
    ],
)
def test_sniff_date(line: str, expected: str | None) -> None:
    assert semsearch._sniff_date(line) == expected


def test_chunk_markdown_carries_heading_stack(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(semsearch, "REPO", tmp_path)
    page = tmp_path / "page.md"
    page.write_text(
        "# Title\n\n## Section one\n\nbody of one\n\n### Sub A\n\nbody of sub a\n",
        encoding="utf-8",
    )
    chunks = semsearch.chunk_markdown(page)
    headings = {c.heading for c in chunks}
    assert "Title > Section one" in headings
    assert "Title > Section one > Sub A" in headings
    assert all(c.path == "page.md" for c in chunks)


def test_split_long_breaks_oversized_run() -> None:
    # One word per line, so a piece can overshoot MAX_WORDS by at most one line.
    lines = [(i, "word") for i in range(1, semsearch.MAX_WORDS * 3)]  # no blank lines
    pieces = semsearch._split_long(lines)
    assert len(pieces) > 1
    for piece in pieces:
        assert len(piece) <= semsearch.MAX_WORDS
