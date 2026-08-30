# ADR-0023: Visualiser reuses Neo4j read credentials; caches payloads for offline use

- **Status:** Accepted
- **Date:** 2026-04-04
- **Sources:** `specs/002-neo4j-schema-ui/research.md`, `plan.md`; `README.md` §Configuration

## Context

`specs/002` forbids adding an authentication layer to the single-user visualiser,
but the schema overview must stay usable during short Neo4j / sample-data outages
(5-minute retry requirement, Constitution IX consistency).

## Decision

- Users supply **read-only Neo4j credentials via `.env`**
  (`FRICTIONLESS_ARCHITECT_NEO4J_*`); no extra auth layer. Empty
  `NEO4J_URI` means "sample data only".
- The visualiser **caches the normalised JSON payload**
  (`.cache/visualiser/schema_payload.json`) and falls back to it when the
  database and sample data are unreachable, showing a non-blocking
  "Sample data unavailable" banner while keeping the schema list visible.
- Cache refreshes are rate-limited (`REFRESH_BACKOFF_SECONDS`, default 300).

## Consequences

- No duplicate identity system; the safest path given the constraint.
- `scripts/neo4j_schema.py` is a separate CLI using unprefixed `NEO4J_*` vars —
  an intentional split from the app's prefixed settings.
