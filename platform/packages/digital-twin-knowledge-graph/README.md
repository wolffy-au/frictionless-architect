# digital-twin-knowledge-graph

Subsystem 3 of the Frictionless Architecture Platform: the knowledge-graph read path
(`if-twin-read-path`, GH #106) over the Neo4j-backed ArchiMate model — plus the ArchiMate
exchange-format parser and idempotent schema/ingestion manager it is built on.

- Modelled as `art-pkg-digital-twin-knowledge-graph` in `architecture/model/`, realised by
  this Artifact; implements half of `sub-twin`'s modelled functions — the intent-plane
  read/ingest path (`if-twin-read-path`). `fn-twin-ingest` (twin-plane ingestion from live
  infrastructure/deployment data) and `fn-ledger-record` (forensic ledger) are out of scope
  for this package — see
  [`specs/001-knowledge-graph-read-path/spec.md`](specs/001-knowledge-graph-read-path/spec.md)
  "Scope boundary".
- A library, not a service: no FastAPI app, router, or CLI entrypoint. Consumed as an
  ordinary Poetry path dependency (ADR-0005) — see
  [`specs/001-knowledge-graph-read-path/contracts/read-path.md`](specs/001-knowledge-graph-read-path/contracts/read-path.md)
  for the public call shape.

## Scope boundary

This package does **not** yet replace flat-`src/`'s `visualizer/api.py` or
`scripts/neo4j_schema.py` — those keep using their own, unchanged copies of the read path,
parser and schema manager. The cutover is deferred to the visualiser API/UI split
(`ARCHITECTURE.md` §8.2, step 7) or a dedicated follow-up; see
[`specs/001-knowledge-graph-read-path/plan.md`](specs/001-knowledge-graph-read-path/plan.md)
Summary.

## Public surface

```python
from digital_twin_knowledge_graph import (
    GraphSettings,
    KnowledgeGraphReadPath,
    ReadPathError,
    SampleParser,
    ParsedSample,
    SchemaManager,
)
```

See [`specs/001-knowledge-graph-read-path/contracts/read-path.md`](specs/001-knowledge-graph-read-path/contracts/read-path.md)
for the full call contract, and
[`specs/001-knowledge-graph-read-path/quickstart.md`](specs/001-knowledge-graph-read-path/quickstart.md)
for runnable validation snippets.
