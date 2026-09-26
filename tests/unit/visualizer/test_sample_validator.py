"""Unit tests for the sample-vs-schema validator (xmlschema XSD validation, ADR-0022)."""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from xmlschema.exceptions import XMLSchemaKeyError

from frictionless_architect.visualizer.sample_validator import (
    MAX_XSD_ISSUES,
    _load_schema,
    validate_sample_against_schema,
)

SAMPLE_PATH = Path("sample-data/sample-00/Test Model Full.xml")
SCHEMA_PATH = Path("sample-data/schema/archimate3_Diagram.xsd")

MODEL_OPEN = """<?xml version="1.0" encoding="UTF-8"?>
<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" identifier="m-1">
  <name>Model</name>
"""

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


def _write(tmp_path: Path, body: str, name: str = "sample.xml") -> Path:
    sample = tmp_path / name
    sample.write_text(body, encoding="utf-8")
    return sample


def _elements(count: int, xsi_type: str = "BusinessActor", named: bool = True) -> str:
    name = "<name>A</name>" if named else ""
    items = "".join(f'<element identifier="e-{i}" xsi:type="{xsi_type}">{name}</element>' for i in range(count))
    return f"<elements>{items}</elements>"


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
    issues = validate_sample_against_schema(_write(tmp_path, BROKEN_SAMPLE), SCHEMA_PATH)
    assert any("target e-missing is missing" in issue for issue in issues)
    assert any("missing relationship r-missing" in issue for issue in issues)


def test_structural_violation_is_reported_with_its_path(tmp_path: Path) -> None:
    sample = _write(tmp_path, MODEL_OPEN + "  <bogus/>\n</model>\n")
    issues = validate_sample_against_schema(sample, SCHEMA_PATH)
    assert len(issues) == 1
    assert issues[0].startswith("XSD: ")
    assert "bogus" in issues[0]
    assert "(at /model)" in issues[0]


def test_missing_required_child_is_reported(tmp_path: Path) -> None:
    sample = _write(tmp_path, MODEL_OPEN + _elements(1, named=False) + "</model>\n")
    issues = validate_sample_against_schema(sample, SCHEMA_PATH)
    assert len(issues) == 1
    assert issues[0].startswith("XSD: ")
    assert "/model/elements/element" in issues[0]


def test_undeclared_type_is_reported_without_crashing(tmp_path: Path) -> None:
    sample = _write(tmp_path, MODEL_OPEN + _elements(1, xsi_type="NotAType") + "</model>\n")
    issues = validate_sample_against_schema(sample, SCHEMA_PATH)
    assert issues == ["Types not defined in schema: NotAType"]


def test_prefixed_type_resolves_against_archimate_namespace(tmp_path: Path) -> None:
    body = MODEL_OPEN.replace("<model ", '<model xmlns:archimate="http://www.opengroup.org/xsd/archimate/3.0/" ')
    sample = _write(tmp_path, body + _elements(1, xsi_type="archimate:BusinessActor") + "</model>\n")
    assert validate_sample_against_schema(sample, SCHEMA_PATH) == []


def test_xsd_issues_are_capped(tmp_path: Path) -> None:
    sample = _write(tmp_path, MODEL_OPEN + _elements(MAX_XSD_ISSUES + 10, named=False) + "</model>\n")
    issues = validate_sample_against_schema(sample, SCHEMA_PATH)
    assert len(issues) == MAX_XSD_ISSUES + 1
    assert "further XSD issues suppressed" in issues[-1]


def test_foreign_namespace_is_reported_instead_of_passing(tmp_path: Path) -> None:
    sample = _write(tmp_path, BROKEN_SAMPLE.replace("archimate/3.0/", "archimate/3.1/"), "archimate31.xml")
    issues = validate_sample_against_schema(sample, SCHEMA_PATH)
    assert len(issues) == 1
    assert "archimate/3.1/" in issues[0]


def test_validate_sample_reports_when_sample_has_no_root(tmp_path: Path) -> None:
    sample = _write(tmp_path, BROKEN_SAMPLE, "rootless.xml")
    rootless_tree = MagicMock(getroot=MagicMock(return_value=None))
    with patch("frictionless_architect.visualizer.sample_validator._safe_parse", return_value=rootless_tree):
        issues = validate_sample_against_schema(sample, SCHEMA_PATH)
    assert issues == [f"Sample XML {sample} has no root element"]


def test_unloadable_schema_is_reported(tmp_path: Path) -> None:
    schema = _write(tmp_path, "<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'><bogus/></xs:schema>", "bad.xsd")
    issues = validate_sample_against_schema(SAMPLE_PATH, schema)
    assert len(issues) == 1
    assert issues[0].startswith(f"Schema XSD at {schema} could not be loaded:")


def test_validation_error_mid_run_is_reported(tmp_path: Path) -> None:
    schema = MagicMock()
    schema.maps.types = _load_schema(SCHEMA_PATH.resolve()).maps.types
    schema.iter_errors.side_effect = XMLSchemaKeyError("boom")
    with patch("frictionless_architect.visualizer.sample_validator._load_schema", return_value=schema):
        issues = validate_sample_against_schema(SAMPLE_PATH, SCHEMA_PATH)
    assert len(issues) == 1
    assert issues[0].startswith("XSD validation aborted:")
    assert "boom" in issues[0]


def test_schema_loads_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: Any, **__: Any) -> None:
        raise AssertionError("schema loading attempted network access")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    _load_schema.cache_clear()
    assert validate_sample_against_schema(SAMPLE_PATH, SCHEMA_PATH) == []


def test_schema_is_built_once_per_path() -> None:
    _load_schema.cache_clear()
    validate_sample_against_schema(SAMPLE_PATH, SCHEMA_PATH)
    validate_sample_against_schema(SAMPLE_PATH, SCHEMA_PATH)
    info = _load_schema.cache_info()
    assert info.misses == 1
    assert info.hits == 1
