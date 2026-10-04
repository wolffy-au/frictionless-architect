#!/usr/bin/env python3
"""Check commit messages against the repo's commit-message standard.

The scope list is read from ``.claude/skills/commit-message/references/standard.md`` (area
scopes) and ``platform/packages/`` (package scopes), so the standard stays the single source.
Commitizen only checks the type and subject shape; this adds scope, length, case, trailing
period and breaking-change rules. Imperative mood and body quality stay with `commit-auditor`.

Usage:
    check_commit_messages.py --range develop..HEAD   # every non-merge commit in the range
    check_commit_messages.py --message-file FILE     # one message (commit-msg hook)
Exit 0 when clean, 1 when any message breaks a rule.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STANDARD = ROOT / ".claude/skills/commit-message/references/standard.md"
PACKAGES = ROOT / "platform/packages"

TYPES = {"feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"}
MAX_SUBJECT = 72
SUBJECT = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<desc>.+)$")
AUTO_PREFIXES = ("Merge ", "Revert \"", "fixup! ", "squash! ")


def area_scopes(standard: Path = STANDARD) -> set[str]:
    """Return the area scopes listed in the standard's "Area scopes" bullets."""
    text = standard.read_text(encoding="utf-8")
    block = text.split("**Area scopes**", 1)[1].split("Omit the scope", 1)[0]
    return set(re.findall(r"^- `([a-z0-9_-]+)`", block, re.M))


def package_scopes(packages: Path = PACKAGES) -> set[str]:
    """Return the directory names under ``platform/packages``."""
    return {p.name for p in packages.iterdir() if p.is_dir()} if packages.is_dir() else set()


def check_message(message: str, scopes: set[str]) -> list[str]:
    """Return the rules a commit message breaks (empty when it conforms)."""
    subject, _, rest = message.partition("\n")
    if subject.startswith(AUTO_PREFIXES):
        return []
    match = SUBJECT.match(subject)
    if not match:
        return [f"subject is not '<type>(<scope>)?!?: <description>': {subject!r}"]
    problems: list[str] = []
    if match["type"] not in TYPES:
        problems.append(f"unknown type {match['type']!r}")
    if match["scope"] is not None and match["scope"] not in scopes:
        problems.append(f"unknown scope {match['scope']!r}")
    if len(subject) > MAX_SUBJECT:
        problems.append(f"subject is {len(subject)} characters (max {MAX_SUBJECT})")
    if not match["desc"][0].islower() and not match["desc"][0].isdigit():
        problems.append("description must start lower-case")
    if subject.endswith("."):
        problems.append("subject must not end with a period")
    if match["bang"] and "BREAKING CHANGE:" not in rest:
        problems.append("'!' needs a 'BREAKING CHANGE:' footer")
    if match["type"] == "revert" and not re.search(r"^(Refs|Revert): ", rest, re.M):
        problems.append("revert needs a 'Refs: <sha>' or 'Revert: <sha>' footer")
    return problems


def commits_in_range(rev_range: str) -> list[tuple[str, str]]:
    """Return (short sha, full message) for each non-merge commit in the range."""
    out = subprocess.run(
        ["git", "log", "--no-merges", "--format=%h%x1f%B%x1e", rev_range],
        check=True, capture_output=True, text=True, cwd=ROOT,
    ).stdout
    pairs = (entry.strip("\n").partition("\x1f") for entry in out.split("\x1e") if entry.strip())
    return [(sha.strip(), body.strip()) for sha, _, body in pairs]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--range", dest="rev_range")
    group.add_argument("--message-file", type=Path)
    args = parser.parse_args(argv)

    scopes = area_scopes() | package_scopes()
    if args.message_file:
        items = [("message", args.message_file.read_text(encoding="utf-8").strip())]
    else:
        items = commits_in_range(args.rev_range)

    failed = 0
    for label, message in items:
        problems = check_message(message, scopes)
        if problems:
            failed += 1
            print(f"{label} {message.splitlines()[0] if message else ''}", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
    if failed:
        print(f"{failed} commit message(s) break the standard "
              "(.claude/skills/commit-message/references/standard.md).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
