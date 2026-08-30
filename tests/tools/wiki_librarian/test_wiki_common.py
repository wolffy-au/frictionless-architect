"""Unit tests for wiki_common: source resolution, fingerprints, staleness."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import wiki_common as wc
import yaml


def _write_sources(root: Path, topics: list[dict[str, Any]]) -> None:
    (root / "wiki" / "sources.yaml").write_text(yaml.safe_dump({"topics": topics}), encoding="utf-8")


# --------------------------------------------------------------------------
# source resolution
# --------------------------------------------------------------------------


def test_resolve_topic_expands_globs(wiki_repo: Path) -> None:
    resolved = wc.resolve_topic({"name": "t", "sources": [{"path": "docs/*.md"}]})
    assert resolved["files"] == ["docs/a.md", "docs/b.md"]
    assert resolved["unmatched"] == []
    assert resolved["urls"] == []


def test_resolve_topic_reports_unmatched_glob(wiki_repo: Path) -> None:
    resolved = wc.resolve_topic({"name": "t", "sources": [{"path": "docs/nope-*.md"}]})
    assert resolved["files"] == []
    assert resolved["unmatched"] == ["docs/nope-*.md"]


def test_resolve_topic_keeps_url_sources(wiki_repo: Path) -> None:
    resolved = wc.resolve_topic({"name": "t", "sources": [{"url": "https://example.com/x", "title": "X"}]})
    assert resolved["urls"] == [{"url": "https://example.com/x", "title": "X"}]


def test_resolve_all_reads_sources_yaml(wiki_repo: Path) -> None:
    _write_sources(wiki_repo, [{"name": "one", "sources": [{"path": "README.md"}]}])
    assert [r["name"] for r in wc.resolve_all()] == ["one"]
    assert wc.all_source_files() == ["README.md"]


# --------------------------------------------------------------------------
# fingerprints
# --------------------------------------------------------------------------


def test_sha256_file_matches_hashlib(wiki_repo: Path) -> None:
    expected = hashlib.sha256((wiki_repo / "docs" / "a.md").read_bytes()).hexdigest()
    assert wc.sha256_file("docs/a.md") == expected


def test_file_fingerprint_counts_lines(wiki_repo: Path) -> None:
    fp = wc.file_fingerprint("docs/a.md")
    assert fp is not None
    assert fp["lines"] == 3  # "# A\n\nalpha\n"
    assert fp["sha256"] == wc.sha256_file("docs/a.md")


def test_file_fingerprint_missing_file_is_none(wiki_repo: Path) -> None:
    assert wc.file_fingerprint("docs/gone.md") is None


# --------------------------------------------------------------------------
# staleness classification
# --------------------------------------------------------------------------


def _fresh_log(resolved: dict[str, Any]) -> dict[str, Any]:
    files = {p: wc.file_fingerprint(p) for p in resolved["files"]}
    return {"topics": {resolved["name"]: {"sources": {"files": files, "urls": {}}}}}


def test_topic_status_new_when_no_log_entry(wiki_repo: Path) -> None:
    resolved = wc.resolve_topic({"name": "t", "sources": [{"path": "docs/a.md"}]})
    status, reasons = wc.topic_status(resolved, {})
    assert status == "NEW"
    assert reasons == ["no build-log entry"]


def test_topic_status_fresh_then_stale_on_edit(wiki_repo: Path) -> None:
    resolved = wc.resolve_topic({"name": "t", "sources": [{"path": "docs/a.md"}]})
    (wiki_repo / "wiki" / "t.md").write_text("page\n", encoding="utf-8")
    log = _fresh_log(resolved)

    assert wc.topic_status(resolved, log) == ("FRESH", [])

    (wiki_repo / "docs" / "a.md").write_text("# A\n\nchanged\n", encoding="utf-8")
    status, reasons = wc.topic_status(resolved, log)
    assert status == "STALE"
    assert reasons == ["source changed: docs/a.md"]


def test_topic_status_stale_when_page_missing(wiki_repo: Path) -> None:
    resolved = wc.resolve_topic({"name": "t", "sources": [{"path": "docs/a.md"}]})
    status, reasons = wc.topic_status(resolved, _fresh_log(resolved))
    assert status == "STALE"
    assert "page file missing" in reasons


def test_orphan_topics(wiki_repo: Path) -> None:
    _write_sources(wiki_repo, [{"name": "live", "sources": [{"path": "README.md"}]}])
    log: dict[str, Any] = {"topics": {"live": {}, "dead": {}}}
    assert wc.orphan_topics(log) == ["dead"]
