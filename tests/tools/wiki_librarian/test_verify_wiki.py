"""Unit tests for verify_wiki's check functions (now that they return findings)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import verify_wiki as vw


def _topic(name: str, files: list[str] | None = None, urls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"name": name, "files": files or [], "urls": urls or []}


def test_missing_page_is_an_error() -> None:
    found = vw.check_topic_page_log({"a": _topic("a")}, pages={}, log_topics={})
    assert ("ERROR", "a", "topic has no page file wiki/a.md") in found


def test_page_without_topic_is_an_error() -> None:
    found = vw.check_topic_page_log({}, pages={"stray": "wiki/stray.md"}, log_topics={})
    assert any(level == "ERROR" and "no topic in sources.yaml" in detail for level, _, detail in found)


def test_orphan_build_log_entry_is_an_error() -> None:
    found = vw.check_topic_page_log({}, pages={}, log_topics={"gone": {}})
    assert ("ERROR", "gone", "in .build-log.yaml but not sources.yaml (orphan)") in found


def test_page_present_but_no_log_entry() -> None:
    found = vw.check_topic_page_log({"a": _topic("a")}, pages={"a": "wiki/a.md"}, log_topics={})
    assert ("ERROR", "a", "page exists but no .build-log.yaml entry") in found


def test_unlinked_page_is_an_error(wiki_repo: Path) -> None:
    (wiki_repo / "wiki" / "index.md").write_text("# Index\n\n(no links)\n", encoding="utf-8")
    found = vw.check_index_links({"a": _topic("a")}, pages={"a": "wiki/a.md"})
    assert found == [("ERROR", "a", "not linked from wiki/index.md")]


def test_linked_page_is_clean(wiki_repo: Path) -> None:
    (wiki_repo / "wiki" / "index.md").write_text("# Index\n\n- [A](a.md)\n", encoding="utf-8")
    assert vw.check_index_links({"a": _topic("a")}, pages={"a": "wiki/a.md"}) == []


def test_page_with_no_citations_is_a_review(wiki_repo: Path) -> None:
    page = wiki_repo / "wiki" / "a.md"
    page.write_text("# A\n\nprose with no citations\n", encoding="utf-8")
    found = vw.check_page("a", str(page), {"a": _topic("a", files=["docs/a.md"])})
    assert ("REVIEW", "a", "page has no repo-file citations") in found


def test_page_with_dead_citation_is_an_error(wiki_repo: Path) -> None:
    page = wiki_repo / "wiki" / "a.md"
    page.write_text("# A\n\nsee (`docs/ghost.md`) for detail\n", encoding="utf-8")
    found = vw.check_page("a", str(page), {"a": _topic("a", files=["docs/a.md"])})
    assert ("ERROR", "a", "citation points at missing path: docs/ghost.md") in found


def test_page_with_live_citation_is_clean(wiki_repo: Path) -> None:
    page = wiki_repo / "wiki" / "a.md"
    page.write_text("# A\n\nsee (`docs/a.md`) for detail\n", encoding="utf-8")
    assert vw.check_page("a", str(page), {"a": _topic("a", files=["docs/a.md"])}) == []
