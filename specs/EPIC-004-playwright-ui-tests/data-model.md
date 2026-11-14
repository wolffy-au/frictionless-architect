# Data Model: Browser-Level Tests for the HTML UIs

This feature adds test infrastructure and one minimal placeholder page; it introduces no
persisted entity, schema change, or state machine. The only new "shape" is the visualiser's
placeholder page content, described below for completeness since `contracts/` references it.

## Visualiser placeholder page (FR-009)

Not a data entity — a static-shaped HTML response with no request body and no stored state.

| Field | Type | Notes |
|---|---|---|
| title | string | Fixed page title, e.g. "Schema Visualiser" |
| status text | string | Confirms the page rendered (what the `@ui` smoke scenario asserts on) |
| schema summary | string (optional) | Pulled from the existing `/schema-payload` JSON API (sample-data fallback when Neo4j is unavailable) to give the page's "main interaction" (FR-002) something real to exercise, e.g. an element count |

No validation rules, relationships, or lifecycle/state transitions apply — the page is
read-only and stateless. See `contracts/visualiser-placeholder-page.md` for the route
contract.
