# Implementation Plan: Neo4j Schema Visualiser

**Branch**: `002-neo4j-schema-ui` | **Date**: 2026-04-04 | **Spec**: `/specs/002-neo4j-schema-ui/spec.md`
**Input**: Feature specification from `/specs/002-neo4j-schema-ui/spec.md`

## Summary
Deliver a single-user Neo4j schema visualiser that pairs every ArchiMate node/relationship/view definition with carefullly curated sample data (`sample-data/sample-00/Test Model Full.xml`), exposes the schema/diagram payload via FastAPI endpoints, powers a cytoscape-powered table/diagram UI, and keeps the schema summary accessible whenever sample data or Neo4j access is unavailable.

## Technical Context

**Language/Version**: Python 3.12 (per `pyproject.toml`).  
**Primary Dependencies**: FastAPI 0.128.x, uvicorn, neo4j 5.x driver, python-dotenv/pydantic for settings and payload validation, httpx/pytest for endpoint tests, ruff/pyright/mypy for linting.  
**Storage**: Neo4j 5 cluster for live schema metadata; canonical ArchiMate schema files under `sample-data/schema` and the enriched `sample-data/sample-00/Test Model Full.xml` drive the payloads. The visualiser caches aggregated JSON payloads in `.cache/visualiser` for offline resilience.  
**Testing**: Async `pytest` suites (`tests/api/…`), expect contract tests for `/schema-payload*` endpoints plus UI smoke tests driving `schema_visualizer.js`.  
**Target Platform**: Single-user desktop MVP that runs via `uvicorn src/frictionless_architect.visualizer:app` (FastAPI) and serves assets to any modern browser on Windows/macOS/Linux.  
**Project Type**: Single Python backend service with embedded UI assets and static payload caches; no separate frontend build chain.  
**Performance Goals**: Fetch/render schema payload <2 seconds, keep schema endpoints available at ≥99.5% uptime, surface `latency_ms` metrics along with warnings when caches or data reloads slow down.  
**Constraints**: Must reuse the existing Neo4j read permissions (no extra auth), keep schemas visible even when `Test Model Full.xml` is missing, and optimize for laptop memory/CPU budgets.  
**Scale/Scope**: One analyst, fixed sample data (~dozens of elements/relations/diagram nodes), no multi-tenant or heavy throughput requirements.

### Research Context
- Visualization choice: cytoscape.js + vanilla JS/HTML tables so the FastAPI router can serve a static bundle that draws diagram/table views from the same JSON payload.  
- Sample parsing: `lxml` + `xmlschema` (or at least `lxml` for now) normalizes `sample-data/schema/*` + `Test Model Full.xml` into JSON that highlights coverage gaps and positions (FR-003).  
- Access model: Reuse Neo4j read credentials, cache aggregated payloads per quickstart, show warning “Sample data unavailable” when reloads fail, and keep schema view accessible per Constitution principles.

## Constitution Check
*GATE: Must pass before Phase 0 research and again after Phase 1 design.*  
1. **Principle VII – System Integrity & Accuracy**: Schema payloads derive directly from ArchiMate definitions + curated sample (`Test Model Full.xml`); every displayed entity tracks its source file & identifiers, and coverage gaps are surfaced via warnings so data accuracy is guaranteed.  
2. **Principle VIII – Durability & Interoperability**: Cached JSON payloads plus documented sample-version lineage let downstream tooling (diagram/table, exports) keep working when Neo4j or sample files change, and the warning banner + retries preserve semantics.  
3. **Principle IX – Cross-Platform Consistency**: The same payload drives both cytoscape diagrams and schema tables on any desktop browser, with a consistent warning banner/refresh UX when data becomes stale or missing.

## Project Structure

### Documentation (this feature)
```text
specs/002-neo4j-schema-ui/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```
### Source Code (repository root)
```text
src/frictionless_architect/
├── config.py
├── schema/             # existing Neo4j ingestion
└── visualizer/          # new FastAPI router + static assets + helpers
sample-data/
├── schema/              # ArchiMate XSD files
└── sample-00/           # Test Model.xml and richer Test Model Full.xml
tests/
└── api/                 # new endpoint coverage
```  
**Structure Decision**: Keep the single Python project layout and add `visualizer` plus the enriched sample data so the feature stays colocated with the Neo4j helpers.

## Complexity Tracking
No constitution violations detected; table omitted.
