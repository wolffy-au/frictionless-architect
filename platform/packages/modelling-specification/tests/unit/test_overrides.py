"""Unit tests for `authoring/overrides.py` -- Override Decision Record drafting
(FR-014, R7, data-model.md Override Decision Record).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from modelling_specification.authoring import overrides


@pytest.fixture
def isolated_adr_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(overrides, "ADR_DIR", tmp_path)
    return tmp_path


def test_draft_override_assigns_the_next_free_adr_number(isolated_adr_dir: Path) -> None:
    (isolated_adr_dir / "0040-something.md").write_text("x")

    record = overrides.draft_override(
        overridden_objection="rejection",
        objection_detail="illegal_relationship: Composition BusinessActor -> Goal",
        rationale="legacy naming predates the convention",
        applied_delta_summary="fn-example",
    )

    assert record["id"] == "0041"


def test_draft_override_starts_numbering_at_0001_when_the_dir_is_empty(isolated_adr_dir: Path) -> None:
    record = overrides.draft_override(
        overridden_objection="duplicate", objection_detail="d1", rationale=None, applied_delta_summary="x"
    )
    assert record["id"] == "0001"


def test_draft_override_records_a_null_rationale_when_none_given(isolated_adr_dir: Path) -> None:
    record = overrides.draft_override(
        overridden_objection="pattern", objection_detail="p1", rationale=None, applied_delta_summary="x"
    )

    assert record["rationale"] is None
    (adr_path,) = isolated_adr_dir.glob("*.md")
    assert "none given" in adr_path.read_text().lower()


def test_draft_override_writes_a_status_proposed_adr_stub(isolated_adr_dir: Path) -> None:
    record = overrides.draft_override(
        overridden_objection="rejection",
        objection_detail="illegal_relationship: Composition BusinessActor -> Goal",
        rationale="legacy naming predates the convention",
        applied_delta_summary="fn-example",
    )

    (adr_path,) = isolated_adr_dir.glob("*.md")
    text = adr_path.read_text()
    assert "Status:** Proposed" in text
    assert "illegal_relationship" in text
    assert "legacy naming predates the convention" in text
    assert "fn-example" in text
    assert record["overridden_objection"] == "rejection"
    assert record["objection_detail"] == "illegal_relationship: Composition BusinessActor -> Goal"
    assert record["applied_delta_summary"] == "fn-example"
    assert record["timestamp"]
