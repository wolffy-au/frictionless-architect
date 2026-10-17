# API tests

In-process tests for the schema visualiser's FastAPI app
(`frictionless_architect.app:app`). They use `httpx.AsyncClient` with `ASGITransport`,
so no server needs to run and Neo4j is never contacted
(`FRICTIONLESS_ARCHITECT_NEO4J_URI` is forced to empty).

Specs: [`specs/002-neo4j-schema-ui/spec.md`](../../specs/002-neo4j-schema-ui/spec.md),
[`contracts/api.md`](../../specs/002-neo4j-schema-ui/contracts/api.md) and
[`quickstart.md`](../../specs/002-neo4j-schema-ui/quickstart.md).

## Run

```bash
poetry run pytest tests/api
poetry run pytest tests/api -k status                  # a subset
poetry run pytest tests/api/test_schema_status.py::test_schema_status_reports_metadata
```

## Test modules

| Module | Covers |
|---|---|
| `test_schema_payload.py` | `GET /schema-payload`: content, missing-sample warning, XSD violations as warnings, the 2-second build target |
| `test_schema_status.py` | `GET /schema-payload/status`, `POST /schema-payload/refresh` (`202`, `409`, `429` + `Retry-After`) and the automatic retry (SC-006) |
| `test_schema_view_consistency.py` | The first view's nodes and connections reference elements and relationships in the payload, and every node has bounds |
| `test_app_lifespan.py` | Shutdown cancels a pending retry and closes the Neo4j loader |

## Fixtures (`conftest.py`)

Each fixture yields an `httpx.AsyncClient` bound to the app, with a per-test
`FRICTIONLESS_ARCHITECT_CACHE_DIR` under `tmp_path` and cleared settings/service caches.

| Fixture | Scenario |
|---|---|
| `schema_client` | The real sample model in `sample-data/` |
| `schema_client_without_sample` | `SampleParser.parse` raises `FileNotFoundError` |
| `schema_client_with_slow_refresh` | `_build_payload` sleeps 0.1 s so overlapping refreshes can be provoked |
| `schema_client_with_xsd_violation` | A copy of the sample with one element the XSD rejects |
| `schema_client_recovering_sample` | The first load fails, later loads succeed; retry interval `0` |

Helper: `_build_client(monkeypatch, tmp_path, patch_sample_parse=None, patch_service_class=None,
sample_data=REPO_SAMPLE_DATA)` builds the client; new fixtures should go through it.

## Typical pattern

```python
@pytest.mark.asyncio
async def test_status_reports_metadata(schema_client):
    await schema_client.get("/schema-payload")
    status = (await schema_client.get("/schema-payload/status")).json()
    assert status["neo4j_status"] == "disabled"
```
