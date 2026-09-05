"""Unit tests for the sample-vs-schema consistency validator."""

from __future__ import annotations

from pathlib import Path

from frictionless_architect.visualizer.sample_validator import validate_sample_against_schema

SAMPLE_PATH = Path("sample-data/sample-00/Test Model Full.xml")
SCHEMA_PATH = Path("sample-data/schema/archimate3_Model.xsd")

BROKEN_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <elements>
    <element identifier="e-1" xsi:type="BusinessActor"/>
  </elements>
  <relationships>
    <relationship identifier="r-1" xsi:type="Association" source="e-1" target="e-missing"/>
  </relationships>
  <views>
    <diagrams>
      <view identifier="v-1">
        <node identifier="n-1" elementRef="e-1"/>
        <connection identifier="c-1" relationshipRef="r-missing"/>
      </view>
    </diagrams>
  </views>
</model>
"""


def test_real_sample_is_consistent_with_schema() -> None:
    assert validate_sample_against_schema(SAMPLE_PATH, SCHEMA_PATH) == []


def test_missing_sample_reports_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xml"
    issues = validate_sample_against_schema(missing, SCHEMA_PATH)
    assert issues == [f"Sample XML missing at {missing}"]


def test_missing_schema_reports_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.xsd"
    issues = validate_sample_against_schema(SAMPLE_PATH, missing)
    assert issues == [f"Schema XSD missing at {missing}"]


def test_dangling_references_are_flagged(tmp_path: Path) -> None:
    sample = tmp_path / "broken.xml"
    sample.write_text(BROKEN_SAMPLE, encoding="utf-8")
    issues = validate_sample_against_schema(sample, SCHEMA_PATH)
    assert any("target e-missing is missing" in issue for issue in issues)
    assert any("missing relationship r-missing" in issue for issue in issues)
