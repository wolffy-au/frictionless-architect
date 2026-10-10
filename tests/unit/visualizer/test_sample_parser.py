"""Unit tests for the visualiser sample XML parser."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import ParseError

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
    parser = SampleParser(sample_path)
    with pytest.raises(ArchimateNamespaceError, match="archimate/3.1/"):
        parser.parse()


NS = 'xmlns="http://www.opengroup.org/xsd/archimate/3.0/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'


def _parse(tmp_path: Path, body: str) -> SampleParseResult:
    sample = tmp_path / "sample.xml"
    sample.write_text(f'<model {NS} identifier="m-1"><name> Model </name>{body}</model>', encoding="utf-8")
    return SampleParser(sample).parse()


def test_model_metadata_is_extracted_and_name_stripped(tmp_path: Path) -> None:
    assert _parse(tmp_path, "").model == {"identifier": "m-1", "name": "Model"}


def test_elements_without_an_identifier_are_skipped(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        '<elements><element xsi:type="BusinessActor"><name>Orphan</name></element>'
        '<element identifier="e-1" xsi:type="BusinessActor"><name>Kept</name></element></elements>',
    )
    assert list(result.elements) == ["e-1"]
    assert result.elements["e-1"] == {"identifier": "e-1", "type": "BusinessActor", "name": "Kept"}


def test_element_without_type_or_name_gets_defaults(tmp_path: Path) -> None:
    result = _parse(tmp_path, '<elements><element identifier="e-1"/></elements>')
    assert result.elements["e-1"] == {"identifier": "e-1", "type": "Element", "name": None}


def test_blank_name_is_none(tmp_path: Path) -> None:
    result = _parse(tmp_path, '<elements><element identifier="e-1"><name>   </name></element></elements>')
    assert result.elements["e-1"]["name"] is None


def test_relationships_without_an_identifier_are_skipped(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        '<relationships><relationship source="a" target="b"/>'
        '<relationship identifier="r-1" xsi:type="Flow" source="a" target="b" accessType="Read"/></relationships>',
    )
    assert list(result.relationships) == ["r-1"]
    assert result.relationships["r-1"] == {
        "identifier": "r-1",
        "type": "Flow",
        "source": "a",
        "target": "b",
        "properties": {"accessType": "Read"},
    }


def test_relationship_without_type_defaults_and_has_no_properties(tmp_path: Path) -> None:
    result = _parse(tmp_path, '<relationships><relationship identifier="r-1"/></relationships>')
    assert result.relationships["r-1"]["type"] == "Relationship"
    assert result.relationships["r-1"]["properties"] == {}
    assert result.relationships["r-1"]["source"] is None


def test_model_without_views_yields_no_views(tmp_path: Path) -> None:
    assert _parse(tmp_path, '<elements><element identifier="e-1"/></elements>').views == []


def test_views_without_an_identifier_are_skipped(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        "<views><diagrams><view><name>Anonymous</name></view>"
        '<view identifier="v-1" xsi:type="Diagram"><name>Kept</name></view></diagrams></views>',
    )
    assert [view["identifier"] for view in result.views] == ["v-1"]
    assert result.views[0]["name"] == "Kept"
    assert result.views[0]["nodes"] == []
    assert result.views[0]["connections"] == []


def test_view_without_type_defaults_to_diagram(tmp_path: Path) -> None:
    result = _parse(tmp_path, '<views><diagrams><view identifier="v-1"/></diagrams></views>')
    assert result.views[0]["type"] == "Diagram"


def test_view_nodes_take_their_label_from_the_referenced_element(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        '<elements><element identifier="e-1"><name>Actor</name></element></elements>'
        '<views><diagrams><view identifier="v-1">'
        '<node identifier="n-1" elementRef="e-1" x="10" y="20" w="30" h="40"/>'
        '<node identifier="n-2" elementRef="e-missing" x="1" y="2" w="3" h="4"/>'
        '<node identifier="n-3" x="1" y="2" w="3" h="4"/>'
        "</view></diagrams></views>",
    )
    n1, n2, n3 = result.views[0]["nodes"]
    assert n1 == {
        "identifier": "n-1",
        "elementRef": "e-1",
        "bounds": {"x": 10, "y": 20, "w": 30, "h": 40},
        "label": "Actor",
    }
    assert n2["label"] is None  # reference to an element that does not exist
    assert n3["label"] is None  # no reference at all
    assert n3["elementRef"] is None


def test_node_bounds_are_truncated_to_ints_and_unparseable_values_dropped(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        '<views><diagrams><view identifier="v-1">'
        '<node identifier="n-1" x="10.9" y="not-a-number" w="30"/>'
        "</view></diagrams></views>",
    )
    assert result.views[0]["nodes"][0]["bounds"] == {"x": 10, "w": 30}


def test_view_connections_keep_their_references(tmp_path: Path) -> None:
    result = _parse(
        tmp_path,
        '<views><diagrams><view identifier="v-1">'
        '<connection identifier="c-1" relationshipRef="r-1" source="n-1" target="n-2"/>'
        "</view></diagrams></views>",
    )
    assert result.views[0]["connections"] == [
        {"identifier": "c-1", "relationshipRef": "r-1", "source": "n-1", "target": "n-2"}
    ]


def test_malformed_xml_raises_parse_error(tmp_path: Path) -> None:
    sample = tmp_path / "broken.xml"
    sample.write_text("<model", encoding="utf-8")
    with pytest.raises(ParseError):
        SampleParser(sample).parse()


def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        SampleParser(tmp_path / "absent.xml").parse()


DUPLICATE_MODEL_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<model xmlns="http://www.opengroup.org/xsd/archimate/3.0/"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" identifier="m1">
  <name xml:lang="en">M</name>
  <elements>{elements}</elements>
  <relationships>{relationships}</relationships>
  <views><diagrams>{views}</diagrams></views>
</model>
"""


def _parse_sections(tmp_path: Path, elements: str = "", relationships: str = "", views: str = "") -> SampleParseResult:
    sample = tmp_path / "model.xml"
    sample.write_text(
        DUPLICATE_MODEL_TEMPLATE.format(elements=elements, relationships=relationships, views=views), encoding="utf-8"
    )
    return SampleParser(sample).parse()


def test_clean_sample_has_no_parse_warnings(tmp_path: Path) -> None:
    result = _parse_sections(
        tmp_path, elements='<element identifier="e1" xsi:type="BusinessActor"><name>A</name></element>'
    )
    assert result.warnings == []


def test_duplicate_element_identifier_is_reported_and_the_last_definition_wins(tmp_path: Path) -> None:
    result = _parse_sections(
        tmp_path,
        elements=(
            '<element identifier="e1" xsi:type="BusinessActor"><name>First</name></element>'
            '<element identifier="e1" xsi:type="BusinessRole"><name>Second</name></element>'
        ),
    )
    assert result.elements["e1"]["name"] == "Second"
    assert result.warnings == ["Duplicate element identifier e1 in the sample; the last definition is used"]


def test_duplicate_relationship_identifier_is_reported(tmp_path: Path) -> None:
    rel = '<relationship identifier="r1" source="a" target="b" xsi:type="Association"/>'
    result = _parse_sections(tmp_path, relationships=rel + rel)
    assert len(result.relationships) == 1
    assert result.warnings == ["Duplicate relationship identifier r1 in the sample; the last definition is used"]


def test_duplicate_view_identifier_is_reported_and_both_views_are_kept(tmp_path: Path) -> None:
    view = '<view identifier="v1" xsi:type="Diagram"><name>V</name></view>'
    result = _parse_sections(tmp_path, views=view + view)
    assert len(result.views) == 2
    assert result.warnings == ["Duplicate view identifier v1 in the sample"]


def test_parallel_relationships_with_distinct_identifiers_are_not_duplicates(tmp_path: Path) -> None:
    """Two associations between the same pair are legitimate; only a repeated identifier is a problem."""
    result = _parse_sections(
        tmp_path,
        relationships=(
            '<relationship identifier="r1" source="a" target="b" xsi:type="Association"/>'
            '<relationship identifier="r2" source="a" target="b" xsi:type="Association"/>'
        ),
    )
    assert set(result.relationships) == {"r1", "r2"}
    assert result.warnings == []
