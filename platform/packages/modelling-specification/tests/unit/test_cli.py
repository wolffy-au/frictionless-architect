"""Unit tests for cli.py -- the entry point root's build.py/render_diagrams.py and the
model-archimate skill's validate.py now shell into (ADR-0037, R2)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from modelling_specification import cli, model_io, rendering


def test_build_against_the_real_repo_model_is_valid(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["build"]) == 0
    out = capsys.readouterr().out
    assert "VALID" in out
    assert "elements" in out


def test_build_reports_errors_without_writing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(model_io, "write_and_validate", lambda: (2, ["boom"], [], None))
    assert cli.main(["build"]) == 2
    assert "error: boom" in capsys.readouterr().err


def test_build_prints_findings_when_invalid(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    result = {
        "elements": 1,
        "relationships": 0,
        "findings": [{"check": "illegal_relationship", "id": "x", "detail": "bad"}],
        "clean": False,
    }
    monkeypatch.setattr(model_io, "write_and_validate", lambda: (1, [], ["a warning"], result))
    assert cli.main(["build"]) == 1
    out = capsys.readouterr().out
    assert "a warning" in out
    assert "INVALID — 1 finding(s)" in out
    assert "[illegal_relationship] x: bad" in out


def test_render_check_reports_up_to_date(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["render", "--check"]) == 0
    assert "diagrams up to date" in capsys.readouterr().out


def test_render_missing_model_is_an_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(rendering, "render_diagrams", lambda check, svg: (2, [], []))
    assert cli.main(["render", "--check"]) == 2
    assert "missing" in capsys.readouterr().err


def test_render_check_lists_stale_and_orphan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(rendering, "render_diagrams", lambda check, svg: (1, ["a.puml"], ["b.puml"]))
    assert cli.main(["render", "--check"]) == 1
    out = capsys.readouterr().out
    assert "STALE   a.puml" in out
    assert "ORPHAN  b.puml" in out
    assert "run: poetry run python" in out


def test_render_without_check_reports_regenerated_and_removed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(rendering, "render_diagrams", lambda check, svg: (0, ["a.puml"], ["b.puml"]))
    assert cli.main(["render", "--no-svg"]) == 0
    out = capsys.readouterr().out
    assert "regenerated a.puml" in out
    assert "removed b.puml" in out


def test_render_without_check_reports_nothing_to_do(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(rendering, "render_diagrams", lambda check, svg: (0, [], []))
    assert cli.main(["render"]) == 0
    assert "nothing regenerated" in capsys.readouterr().out


def test_validate_json_against_the_real_repo_model(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["validate", str(model_io.OUT), "--json"]) == 0
    payload: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert payload["clean"] is True
    assert payload["elements"] > 0


def test_validate_text_against_the_real_repo_model(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["validate", str(model_io.OUT)]) == 0
    assert "VALID" in capsys.readouterr().out


def test_validate_text_reports_findings(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    result = {
        "path": "x",
        "elements": 1,
        "relationships": 1,
        "views": 0,
        "clean": False,
        "findings": [{"check": "broken_connection", "id": "c1", "detail": "bad ref"}],
    }
    monkeypatch.setattr(model_io, "validate_model", lambda path: result)
    assert cli.main(["validate", "whatever"]) == 1
    out = capsys.readouterr().out
    assert "INVALID — 1 finding(s)" in out
    assert "[broken_connection] c1: bad ref" in out


def test_validate_unreadable_model_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["validate", "/no/such/model.xml", "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["clean"] is False
    assert "error" in payload


def test_validate_unreadable_model_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["validate", "/no/such/model.xml"]) == 2
    assert "could not load" in capsys.readouterr().err
