"""Steps for the schema visualiser API, driving the real in-process FastAPI app."""

# pyright: reportCallIssue=false
# mypy: disable-error-code="untyped-decorator,no-any-return"
from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path
from typing import Any

import httpx
from behave import given, then, when  # type: ignore[import-untyped]
from httpx import ASGITransport
from pydantic import ValidationError

from frictionless_architect import app as app_mod
from frictionless_architect.visualizer import api as api_mod
from frictionless_architect.visualizer import config as config_mod
from frictionless_architect.visualizer.data_loader import DataLoader, DataLoaderError

REPO_SAMPLE_DATA = Path(__file__).resolve().parents[3] / "sample-data"
SAMPLE_REL = Path("sample-00") / "Test Model Full.xml"
NEW_TYPE = {"identifier": "id-new-type", "type": "Grouping", "name": "Brand New Type"}


def _copy_sample_data(context: Any) -> Path:
    """Copy sample-data into the scenario's tmp dir so the XML can be altered."""
    target = context.tmp_dir / "sample-data"
    if not target.exists():
        shutil.copytree(REPO_SAMPLE_DATA, target)
    context.options["sample_data"] = target
    return target


def _edit_sample(context: Any, old: str, new: str) -> None:
    sample = _copy_sample_data(context) / SAMPLE_REL
    text = sample.read_text(encoding="utf-8")
    assert old in text, f"sample no longer contains {old!r}"
    sample.write_text(text.replace(old, new, 1), encoding="utf-8")


def _stub_neo4j(context: Any, fail_first: bool = False) -> None:
    """Replace the Neo4j read with a stub supplying one extra schema element."""
    calls = {"n": 0}

    def collect(_: DataLoader) -> dict[str, list[dict[str, Any]]]:
        calls["n"] += 1
        if fail_first and calls["n"] == 1:
            raise DataLoaderError("Neo4j query failed: stubbed outage")
        return {"elements": [dict(NEW_TYPE)], "relationships": [], "views": []}

    context.monkeypatch.setattr(DataLoader, "collect", collect)
    context.options["neo4j_uri"] = "bolt://stub:7687"


def _ensure_client(context: Any) -> httpx.AsyncClient:
    if context.client is not None:
        return context.client
    options = context.options
    sample_data = options.get("sample_data", REPO_SAMPLE_DATA)
    env = {
        "FRICTIONLESS_ARCHITECT_NEO4J_URI": options.get("neo4j_uri", ""),
        "FRICTIONLESS_ARCHITECT_CACHE_DIR": str(context.tmp_dir / "cache"),
        "FRICTIONLESS_ARCHITECT_SAMPLE_DATA_DIR": str(sample_data),
        "FRICTIONLESS_ARCHITECT_REFRESH_BACKOFF_SECONDS": "0",
        "FRICTIONLESS_ARCHITECT_RETRY_INTERVAL_SECONDS": str(options.get("retry_interval", 300)),
    }
    for key, value in env.items():
        context.monkeypatch.setenv(key, value)
    config_mod.get_visualizer_settings.cache_clear()
    api_mod.get_schema_service.cache_clear()
    context.client = httpx.AsyncClient(transport=ASGITransport(app=app_mod.app), base_url="http://testserver")
    return context.client


def _call(context: Any, method: str, url: str, **kwargs: Any) -> httpx.Response:
    client = _ensure_client(context)
    return context.loop.run_until_complete(client.request(method, url, **kwargs))


def _payload(context: Any) -> dict[str, Any]:
    response = _call(context, "GET", "/schema-payload")
    assert response.status_code == 200, response.text
    context.response = response
    return response.json()


def _wait_until(context: Any, predicate: Any, attempts: int = 100) -> dict[str, Any]:
    status: dict[str, Any] = {}
    for _ in range(attempts):
        status = _call(context, "GET", "/schema-payload/status").json()
        if predicate(status):
            return status
        context.loop.run_until_complete(asyncio.sleep(0.05))
    raise AssertionError(f"condition not reached; last status {status}")


@given("the visualiser API is running against the sample data")
def step_running(context: Any) -> None:
    context.options["sample_data"] = REPO_SAMPLE_DATA


@given("the sample dataset is loaded")
@given("the visualiser loads the provided sample data")
@given("the schema contains relationships (Association)")
def step_sample_loaded(context: Any) -> None:
    assert _call(context, "GET", "/schema-payload").status_code == 200
    status = _call(context, "GET", "/schema-payload/status").json()
    assert status["sample_file_status"] == "loaded", status
    context.before = _call(context, "GET", "/schema-payload").json()


@when("they inspect the element list")
def step_inspect_elements(context: Any) -> None:
    context.payload = _payload(context)


@then(
    "each element type from the schema is shown with one or more sample nodes (e.g., ValueStream VS1, VS2) "
    'drawn from "sample-data/sample-00/Test Model Full.xml"'
)
def step_elements_with_samples(context: Any) -> None:
    elements = context.payload["elements"]
    assert elements
    for element in elements:
        assert element["sample_instances"], f"{element['type']} has no sample node"
    value_streams = [e for e in elements if e["type"] == "ValueStream"]
    assert any(e["name"] == "Value Stream VS1" for e in value_streams)


@when("the user selects that relationship type")
def step_select_relationship(context: Any) -> None:
    context.payload = _payload(context)


@then(
    "the visualiser highlights the actual relationships between the sample nodes "
    "(e.g., the Association between VS1 and VS2) and shows the source/target identifiers"
)
def step_association(context: Any) -> None:
    associations = [r for r in context.payload["relationships"] if r["type"] == "Association"]
    assert associations
    assert any(r["source"] == "id-vs1" and r["target"] and r["sample_instances"] for r in associations)


@when("the reviewer refreshes the sample view")
def step_refresh(context: Any) -> None:
    assert _call(context, "POST", "/schema-payload/refresh", json={"source": "manual"}).status_code == 202
    _wait_until(context, lambda s: not s["refresh_in_progress"] and "last_refresh_completed" in s)
    context.after = _payload(context)


@then(
    "the overview again presents the same nodes and relationships together with the specification that defines each type"
)
def step_same_overview(context: Any) -> None:
    before, after = context.before, context.after

    def shape(p: dict[str, Any]) -> tuple[Any, Any]:
        return (
            [(e["identifier"], e["type"], e["source_file"]) for e in p["elements"]],
            [(r["identifier"], r["type"], r["source"], r["target"], r["source_file"]) for r in p["relationships"]],
        )

    assert shape(before) == shape(after)
    assert all(e["source_file"] for e in after["elements"])
    assert all(r["source_file"] for r in after["relationships"])


@given('the schema references a type (e.g., a new ArchiMate element) with no sample nodes in "sample-data/sample-00"')
def step_type_without_sample(context: Any) -> None:
    _stub_neo4j(context)


@when("the schema payload is requested")
def step_request_payload(context: Any) -> None:
    context.response = _call(context, "GET", "/schema-payload")
    context.payload = context.response.json() if context.response.status_code == 200 else {}


@then("that type is flagged as lacking a sample entry and the rest of the schema is still returned")
def step_flagged(context: Any) -> None:
    assert context.response.status_code == 200
    payload = context.payload
    entry = next(e for e in payload["elements"] if e["identifier"] == NEW_TYPE["identifier"])
    assert entry["coverage"] is False and entry["sample_instances"] == []
    assert f"Missing sample entry for {NEW_TYPE['type']} {NEW_TYPE['name']}" in payload["warnings"]
    assert any(e["coverage"] for e in payload["elements"])


@given('"Test Model Full.xml" has nodes that share identifiers')
def step_shared_ids(context: Any) -> None:
    _edit_sample(
        context,
        '<element identifier="id-busactor"',
        '<element identifier="id-vs1" xsi:type="ValueStream"><name xml:lang="en">Again</name></element>\n'
        '    <element identifier="id-busactor"',
    )


@then("the payload warns about the duplicate identifier and is still returned")
def step_duplicate_warning(context: Any) -> None:
    assert context.response.status_code == 200
    assert any("Duplicate element identifier id-vs1" in w for w in context.payload["warnings"])


@given("the sample data declares a namespace other than the ArchiMate 3.0 one")
def step_other_namespace(context: Any) -> None:
    _edit_sample(
        context,
        'xmlns="http://www.opengroup.org/xsd/archimate/3.0/"',
        'xmlns="http://www.opengroup.org/xsd/archimate/9.9/"',
    )
    _stub_neo4j(context)


@when("the schema payload status is requested")
def step_request_status(context: Any) -> None:
    context.payload = _payload(context)
    context.status = _call(context, "GET", "/schema-payload/status").json()


@then('sample_file_status is "invalid" and a warning names the expected namespace')
def step_invalid_status(context: Any) -> None:
    assert context.status["sample_file_status"] == "invalid", context.status
    expected = "http://www.opengroup.org/xsd/archimate/3.0/"
    assert any(expected in w for w in context.payload["warnings"]), context.payload["warnings"]


@given('"sample-data/sample-00/Test Model Full.xml" cannot be loaded and Neo4j supplies the schema')
def step_sample_unloadable(context: Any) -> None:
    (_copy_sample_data(context) / SAMPLE_REL).unlink()
    _stub_neo4j(context)


@then('the warning "Sample data unavailable" appears and the schema element list stays accessible')
def step_warning_and_list(context: Any) -> None:
    assert context.response.status_code == 200
    assert "Sample data unavailable" in context.payload["warnings"]
    assert context.payload["elements"]
    status = _call(context, "GET", "/schema-payload/status").json()
    assert status["sample_file_status"] == "missing"


@when("the schema payload is requested with the cache bypassed")
def step_request_cold(context: Any) -> None:
    started = time.perf_counter()
    context.response = _call(context, "GET", "/schema-payload", params={"force_reload": "true"})
    context.elapsed = time.perf_counter() - started


@then("the response arrives within 2 seconds")
def step_within_two_seconds(context: Any) -> None:
    assert context.response.status_code == 200
    assert context.elapsed < 2.0
    assert 0 <= context.response.json()["latency_ms"] < 2000


@given("Neo4j fails on the first load and then recovers")
def step_flaky_neo4j(context: Any) -> None:
    context.options["retry_interval"] = 0
    _stub_neo4j(context, fail_first=True)


@then("the payload is returned with a non-blocking warning")
def step_nonblocking_warning(context: Any) -> None:
    assert context.response.status_code == 200
    assert any("Neo4j query failed" in w for w in context.payload["warnings"])
    assert context.payload["elements"]


@then("a background retry is pending")
def step_retry_pending(context: Any) -> None:
    status = _call(context, "GET", "/schema-payload/status").json()
    assert status["retry_pending"] is True, status


@then("the retry loads the schema without a manual refresh")
def step_retry_loads(context: Any) -> None:
    status = _wait_until(context, lambda s: not s["retry_pending"])
    assert status["neo4j_status"] == "available", status
    assert "last_refresh_completed" in status


@then("the default retry interval is 300 seconds")
def step_default_interval(context: Any) -> None:
    context.monkeypatch.delenv("FRICTIONLESS_ARCHITECT_RETRY_INTERVAL_SECONDS", raising=False)
    config_mod.get_visualizer_settings.cache_clear()
    assert config_mod.VisualizerSettings().retry_interval_seconds == 300


@then("a RETRY_INTERVAL_SECONDS above 300 is rejected")
def step_interval_cap(context: Any) -> None:
    context.monkeypatch.setenv("FRICTIONLESS_ARCHITECT_RETRY_INTERVAL_SECONDS", "301")
    try:
        config_mod.VisualizerSettings()
    except ValidationError:
        return
    raise AssertionError("an interval above 5 minutes was accepted")
