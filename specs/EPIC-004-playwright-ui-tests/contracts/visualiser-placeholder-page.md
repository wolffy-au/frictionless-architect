# Contract: Visualiser placeholder page

## `GET /` (visualiser app)

New minimal HTML route satisfying FR-009, giving FR-001/FR-002 a real page to smoke-test.

**Request**: No parameters, no body.

**Response**: `200 OK`, `Content-Type: text/html`.

- Renders without a JavaScript console error (FR-001).
- Includes a visible element reflecting a value derived from the existing
  `/schema-payload` JSON endpoint (sample-data fallback when Neo4j is unavailable, per
  `VisualizerSettings.neo4j_uri` default) — this is the page's "main interaction" that
  FR-002's browser-level test asserts against.
- Superseded once GH #74's UI composition/build tooling ships a real subsystem UI; this
  route is not meant to accrete features in the meantime (ADR-0053).

**Out of scope**: Authentication, styling beyond what's needed for the smoke assertion, and
any interaction beyond rendering the schema-derived value.
