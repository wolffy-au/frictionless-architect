"""Unit tests for the visualiser sample XML parser."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from frictionless_architect.visualizer.namespaces import ArchimateNamespaceError
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


def test_parse_raises_when_sample_has_no_root(tmp_path: Path) -> None:
    sample_path = tmp_path / "rootless.xml"
    sample_path.write_text("<a/>", encoding="utf-8")
    rootless_tree = MagicMock(getroot=MagicMock(return_value=None))
    parser = SampleParser(sample_path)
    with patch("frictionless_architect.visualizer.sample_parser._safe_parse", return_value=rootless_tree):
        with pytest.raises(ValueError, match="no root element"):
            parser.parse()


def test_parse_raises_on_foreign_archimate_namespace(tmp_path: Path) -> None:
    sample_path = tmp_path / "archimate31.xml"
    sample_path.write_text(
        '<model xmlns="http://www.opengroup.org/xsd/archimate/3.1/" identifier="m-1">'
        '<elements><element identifier="e-1"/></elements></model>',
        encoding="utf-8",
    )
    with pytest.raises(ArchimateNamespaceError, match="archimate/3.1/"):
        SampleParser(sample_path).parse()
