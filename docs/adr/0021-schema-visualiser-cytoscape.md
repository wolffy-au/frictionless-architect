# ADR-0021: Schema visualiser uses cytoscape.js + coordinated HTML tables

- **Status:** Accepted
- **Date:** 2026-04-04
- **Sources:** `specs/002-neo4j-schema-ui/research.md`; `specs/002-neo4j-schema-ui/plan.md`

## Context

The schema visualiser (the one implemented slice) must render ArchiMate
nodes/relationships as a diagram plus coordinated tables, offline-capable, in a
single-user desktop MVP served by one FastAPI process.

## Decision

Render with a bundled **`cytoscape.js`** view plus coordinated HTML tables. The
FastAPI router serves the JS bundle and the JSON payload from the same process.

## Consequences

- Ships as a small, offline-ready static asset with ArchiMate-friendly layouts
  (concentric, breadth-first) and built-in pan/zoom.
- Permissive license, plain JS bundle — keeps the desktop MVP simple.

## Alternatives considered

- **D3.js** — too low-level; would force reinventing layout/pan/zoom.
- **vis.js** — larger bundle, weaker layout control for ArchiMate-style diagrams.
