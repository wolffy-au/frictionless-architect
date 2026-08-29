"""Verify the generated wiki is structurally sound and honest about its sources.

Run at the end of every librarian run, alongside build_status.py:

    python tools/verify_wiki.py

Exit code is 0 when clean, 1 when there is at least one ERROR.

The wiki is a derived cache. build_status.py answers "is a page stale?"; this
answers the other seam -- "does what got generated hang together?":

ERROR   a topic in sources.yaml has no page file
ERROR   a page file exists for no topic (and is not index.md)
ERROR   a topic page is not linked from wiki/index.md
ERROR   a repo-file citation on a page points at a path that does not exist
ERROR   .build-log.yaml lists a topic that sources.yaml does not (orphan)
ERROR   .build-log.yaml has no entry for a topic that has a page
REVIEW  a page has no citations at all (synthesis with nothing cited)
REVIEW  a page frontmatter lists a source not in the topic's resolved set
REVIEW  a URL cache file on disk that no topic references
"""

from __future__ import annotations

import io
import os
import re
import sys

import wiki_common as wc

errors: list[tuple[str, str]] = []
reviews: list[tuple[str, str]] = []


def _read(path: str) -> str:
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _frontmatter_sources(text: str) -> list[str]:
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return []
    import yaml

    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return []
    out = []
    for s in fm.get("sources") or []:
        out.append(re.sub(r"\s*\(retrieved.*?\)\s*$", "", str(s)).strip())
    return out


def _check_topic_page_log(resolved: dict, pages: dict, log_topics: dict) -> None:
    for name in resolved:
        if name not in pages:
            errors.append((name, "topic has no page file wiki/%s.md" % name))
        elif name not in log_topics:
            errors.append((name, "page exists but no .build-log.yaml entry"))
    for name in pages:
        if name not in resolved:
            errors.append((name, "page wiki/%s.md has no topic in sources.yaml" % name))
    for name in log_topics:
        if name not in resolved:
            errors.append((name, "in .build-log.yaml but not sources.yaml (orphan)"))


def _check_index_links(resolved: dict, pages: dict) -> None:
    index_text = _read(wc.INDEX_FILE) if os.path.isfile(wc.INDEX_FILE) else ""
    linked = set(re.findall(r"\]\(\s*([A-Za-z0-9._-]+)\.md\s*\)", index_text))
    for name in resolved:
        if name in pages and name not in linked:
            errors.append((name, "not linked from wiki/index.md"))


def _check_page(name: str, path: str, resolved: dict) -> None:
    text = _read(path)
    cites = wc.CITE_FILE_RE.findall(text)
    if name in resolved and not cites:
        reviews.append((name, "page has no repo-file citations"))
    for rel in sorted(set(cites)):
        if not os.path.isfile(rel):
            errors.append((name, "citation points at missing path: %s" % rel))
    if name in resolved:
        declared_ok = set(resolved[name]["files"]) | {u["url"] for u in resolved[name]["urls"]}
        for s in _frontmatter_sources(text):
            if s not in declared_ok:
                reviews.append((name, "frontmatter source not in resolved set: %s" % s))


def _check_stray_caches(resolved: dict) -> None:
    if not os.path.isdir(wc.CACHE_DIR):
        return
    referenced = {wc.url_cache_path(u["url"]) for r in resolved.values() for u in r["urls"]}
    for f in sorted(os.listdir(wc.CACHE_DIR)):
        p = os.path.join(wc.CACHE_DIR, f)
        if p not in referenced:
            reviews.append(("(cache)", "unreferenced URL cache file: %s" % p))


def main() -> int:
    if not os.path.isdir(wc.WIKI_DIR):
        print("no wiki/ -- run from the repo root", file=sys.stderr)
        return 1

    resolved = {r["name"]: r for r in wc.resolve_all()}
    log_topics = wc.load_build_log().get("topics") or {}
    pages = {os.path.basename(p)[:-3]: p for p in wc.iter_wiki_pages()}

    _check_topic_page_log(resolved, pages, log_topics)
    _check_index_links(resolved, pages)
    for name, path in pages.items():
        _check_page(name, path, resolved)
    _check_stray_caches(resolved)

    print("topics: %d   pages: %d   build-log entries: %d" % (len(resolved), len(pages), len(log_topics)))
    print("=" * 72)
    print("ERRORS: %d     REVIEW: %d" % (len(errors), len(reviews)))
    print("=" * 72)
    for label, rows in (("ERROR ", errors), ("REVIEW", reviews)):
        for name, detail in rows:
            print("  %s %-22s %s" % (label, name, detail))
    if not errors and not reviews:
        print("  every topic has a linked page, and every citation resolves")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
