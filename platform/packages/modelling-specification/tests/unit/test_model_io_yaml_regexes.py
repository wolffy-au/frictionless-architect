"""Pins the `views.yaml`/`elements.yaml` line-matching regexes in model_io.py to the
patterns they were rewritten from (spaces -> `{n}` quantifiers, possessive tail,
inline-comment strip anchored), so a refactor cannot silently change what they match."""

from __future__ import annotations

import itertools
import random
import re
import time

import pytest
from modelling_specification import model_io

_LEGACY = {
    "_MEMBERS_KEY_RE": (re.compile(r"^  members:\s*$"), "match"),
    "_MEMBERS_ITEM_RE": (re.compile(r"^    - (\S+)\s*$"), "match"),
    "_BLOCK_FIELD_RE": (re.compile(r"^  (\w+):\s*(\S.*)\s*$"), "match"),
    "_BLOCK_START_FIELD_RE": (re.compile(r"^- (\w+):\s*(\S.*)\s*$"), "match"),
}
_LEGACY_COMMENT = re.compile(r"\s+#.*$")
_ALPHABET = [" ", " ", "\t", "\r", "\n", "#", ":", "-", "a", "b", "x", "_", "'", '"', "{"]
_SAMPLES = [
    "",
    "  members:",
    "  members:  ",
    "   members:",
    " members:",
    "    - id-1",
    "    - id-1   ",
    "     - id-1",
    "   - id-1",
    "    -  id-1",
    "    - ",
    "  name: Foo",
    "  name:Foo",
    "  name:    Foo bar   ",
    "  name:",
    "  name:   ",
    "  name: Foo # note",
    "   name: Foo",
    "- type: Node",
    "- type:   Node  \r",
    "- type:",
    "- x: a\nb",
    "  x: a\n",
    "  x: a\n  ",
]


def _random_lines(count: int = 4000) -> list[str]:
    rng = random.Random(188)
    prefixes = ["  ", "    - ", "- ", "  k:", "- k:", "  members:", "    ", ""]
    return [rng.choice(prefixes) + "".join(rng.choices(_ALPHABET, k=rng.randint(0, 10))) for _ in range(count)]


def _result(pattern: re.Pattern[str], text: str) -> tuple[str, ...] | None:
    m = pattern.match(text)
    return None if m is None else (m.group(0), *m.groups())


@pytest.mark.parametrize("name", sorted(_LEGACY))
def test_rewritten_pattern_matches_exactly_what_the_legacy_one_did(name: str) -> None:
    legacy, _ = _LEGACY[name]
    current = getattr(model_io, name)
    for text in _SAMPLES + _random_lines():
        got, want = _result(current, text), _result(legacy, text)
        assert got == want, repr(text)


def test_block_field_keeps_trailing_whitespace_in_the_value() -> None:
    m = model_io._BLOCK_FIELD_RE.match("  desc: some text  ")
    assert m is not None
    assert m.groups() == ("desc", "some text  ")


@pytest.mark.parametrize(
    "raw",
    [
        "value",
        "value # comment",
        "value   #comment",
        "value\t# comment",
        "a#b",
        "a # b # c",
        " # leading",
        "# only",
        "  ",
        "x   ",
        "x \n# y",
        "x # y\n",
        "x # y\nz",
    ],
)
def test_inline_comment_strip_matches_legacy(raw: str) -> None:
    assert model_io._strip_inline_comment(raw) == _LEGACY_COMMENT.sub("", raw)


def test_inline_comment_strip_matches_legacy_on_random_input() -> None:
    for text in _random_lines():
        assert model_io._strip_inline_comment(text) == _LEGACY_COMMENT.sub("", text), repr(text)


def test_inline_comment_strip_matches_legacy_on_every_short_string() -> None:
    for length in range(7):
        for chars in itertools.product(" \n#a\u00a0", repeat=length):
            text = "".join(chars)
            assert model_io._strip_inline_comment(text) == _LEGACY_COMMENT.sub("", text), repr(text)


def test_block_field_value_strips_comment_except_for_quoted_scalars() -> None:
    assert model_io._block_field_value("abc  # note") == "abc"
    assert model_io._block_field_value('"abc # kept"') == '"abc # kept"'
    assert model_io._block_field_value("'a # kept'") == "'a # kept'"


def test_long_whitespace_runs_stay_linear() -> None:
    hostile = "k" + " " * 200_000
    start = time.perf_counter()
    assert model_io._strip_inline_comment(hostile) == hostile
    assert model_io._BLOCK_FIELD_RE.match("  k:" + " " * 200_000) is None
    assert model_io._BLOCK_START_FIELD_RE.match("- k:" + " " * 200_000) is None
    assert time.perf_counter() - start < 2.0
