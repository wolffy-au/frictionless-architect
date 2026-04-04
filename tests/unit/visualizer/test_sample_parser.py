"""Unit tests for the visualiser sample XML parser."""

from __future__ import annotations

from pathlib import Path

from frictionless_architect.visualizer.sample_parser import SampleParser, SampleParseResult


def test_sample_parser_reads_sample_file() -> None:
    sample_path = Path("sample-data/sample-00/Test Model Full.xml")
    parser = SampleParser(sample_path)
    result = parser.parse()
    assert result.model["identifier"] is not None
    assert result.elements
    assert result.relationships
    assert result.views
    node = result.views[0]["nodes"][0]
    assert node["bounds"]["x"] >= 0
    assert node["elementRef"]


def test_sample_parse_result_empty(tmp_path: Path) -> None:
    empty = SampleParseResult.empty(tmp_path / "missing.xml")
    assert empty.elements == {}
    assert empty.relationships == {}
    assert empty.views == []
