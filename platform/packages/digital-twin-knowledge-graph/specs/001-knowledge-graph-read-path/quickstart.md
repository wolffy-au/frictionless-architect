# Quickstart: Digital Twin Knowledge Graph — Read Path

## Prerequisites

- From `platform/`: `poetry install` (adds `neo4j`, `defusedxml`, `pydantic-settings` once
  declared in `packages/digital-twin-knowledge-graph/pyproject.toml`; one shared lock,
  ADR-0002).
- A reachable Neo4j 5 instance for the integration test and any manual read-path check
  (`FRICTIONLESS_ARCHITECT_NEO4J_URI` / `_NEO4J_USER` / `_NEO4J_PASSWORD` — same env vars
  flat-`src/`'s visualiser already uses, research.md R6).

## Validate User Story 1 (read path)

```python
from digital_twin_knowledge_graph import GraphSettings, KnowledgeGraphReadPath

settings = GraphSettings()  # reads FRICTIONLESS_ARCHITECT_NEO4J_* from the environment
read_path = KnowledgeGraphReadPath(settings)
payload = read_path.collect()
assert set(payload) == {"elements", "relationships", "views"}
read_path.close()
```

Expect elements/relationships/views lists populated from whatever is already in the graph
(seeded by User Story 3 below, or by the existing flat-`src/` tooling). With no
`neo4j_uri` configured, expect all three lists empty, not an error (FR-003).

## Validate User Story 2 (parser)

```python
from pathlib import Path
from digital_twin_knowledge_graph import SampleParser

result = SampleParser(Path("sample-data/sample-00/Test Model Full.xml")).parse()
assert result.elements and result.relationships
```

Feed a file with a duplicate element identifier and confirm `result.warnings` names it
(FR-005), rather than raising. Feed a non-ArchiMate-namespace XML file and confirm it raises
`ArchimateNamespaceError`.

## Validate User Story 3 (idempotent ingestion)

```python
from digital_twin_knowledge_graph import SchemaManager

manager = SchemaManager(uri, user, password)
manager.apply_constraints()
manager.ingest({"elements": [...], "relationships": [...]})
counts_after_first = read_path.collect()

manager.ingest({"elements": [...], "relationships": [...]})  # same payload again
counts_after_second = read_path.collect()
assert counts_after_first == counts_after_second  # SC-004
manager.close()
```

Ingest a relationship whose `source` doesn't exist and confirm it raises `ValueError` naming
the missing endpoint, with no dangling edge created (FR-007).

## Run the fast suite

```bash
cd platform
poetry run pytest packages/digital-twin-knowledge-graph/tests/unit -v
bash scripts/platform_checks.sh     # from the repo root: pyright, mypy, pytest at 90% coverage
```

## Run the integration test (needs a real Neo4j instance)

```bash
cd platform
poetry run pytest packages/digital-twin-knowledge-graph/tests/integration -v
```

## Failure modes to check

- No `neo4j_uri` configured → `collect()` returns empty lists, not an error.
- Neo4j unreachable → `collect()` raises `ReadPathError`, never a raw `neo4j` exception type
  (confirm with `pytest.raises(ReadPathError)`, not a `neo4j.exceptions` type).
- A view/diagram references a relationship identifier with no matching edge →
  `run_audit_checks()` reports it; parsing/ingestion itself does not raise.
- Re-running `apply_constraints()` against an already-provisioned graph is a no-op.

## Out of scope for this quickstart

Cutting `visualizer/api.py` or `scripts/neo4j_schema.py` over to this package is deferred
(plan.md Summary) — there is no flat-`src/` command to run against the new package yet.
