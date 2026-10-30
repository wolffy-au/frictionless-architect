"""Guard against unquoted ` #` in model YAML values, which YAML parses as a comment."""

import re
from pathlib import Path

import pytest

MODEL_DIR = Path(__file__).resolve().parents[3] / "architecture" / "model"

# `key: value #something` where the value is a plain (unquoted) scalar: YAML ends the value at ` #`.
UNQUOTED_HASH = re.compile(r"^\s*(?:- )?(?:desc|name|label|doc): +[^\"'|>\[{#\s][^\"']* #\S")

HAND_AUTHORED = ["elements.yaml", "relationships.yaml", "views.yaml", "views-viewpoints.yaml", "conventions.yaml"]


@pytest.mark.parametrize("filename", HAND_AUTHORED)
def test_text_values_with_hash_are_quoted(filename: str) -> None:
    """A plain scalar containing ` #` is silently truncated there; such values must be quoted."""
    path = MODEL_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not present")
    offenders = [
        f"{filename}:{number}: {line.strip()}"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if UNQUOTED_HASH.match(line)
    ]
    assert not offenders, "Quote these values; ` #` starts a YAML comment:\n" + "\n".join(offenders)
