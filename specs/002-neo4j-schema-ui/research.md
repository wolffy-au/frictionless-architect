# Research Tasks

## Visualization library for the schema explorer
**Decision:** Surface nodes/relationships with a bundled `cytoscape.js` view plus coordinated HTML tables, where the FastAPI router serves the JS bundle and JSON payload from the same single-user process.  
**Rationale:** Cytoscape provides ready-made ArchiMate-friendly layouts (concentric, breadth-first) and built-in panning/zooming, which lets us ship a small, offline-ready asset that still highlights node/edge metadata and can be referenced from sample data coverage warning overlays. Its permissive license and plain JS bundle keep the desktop MVP simple.  
**Alternatives considered:** D3.js (too low-level and would force us to reinvent layout/pan/zoom) and vis.js (similar feature set but larger bundle and weaker layout controls for ArchiMate-style diagrams).  

## Parsing ArchiMate schema + sample XML data
**Decision:** Use `lxml` plus `xmlschema` to load `sample-data/schema/*.xsd` and `sample-data/sample-00/Test Model Full.xml`, extract element/relationship/view definitions, and normalize them into JSON payloads that both Neo4j ingestion and the visualiser share.  
**Rationale:** `xmlschema` understands XSD-defined structures so we can validate the schema files, while `lxml` keeps parsing fast for the small sample data. Normalizing into JSON simplifies the front-end contract and lets us detect coverage gaps (schema entry without matching sample element) while still providing the layout bounds FR-003 needs.  
**Alternatives considered:** Custom regex/XML parsing (fragile) or relying solely on Neo4j (reduces the ability to show sample coverage before the database is populated).  

## Reusing Neo4j read permissions + offline resilience
**Decision:** Keep the existing Neo4j read permission model by requiring users to supply read-only credentials (via `.env`), and fall back to cached JSON payloads when the database/sample data cannot be reached; the UI surfaces the non-blocking warning "Sample data unavailable" and keeps the schema list visible through cached data.  
**Rationale:** The spec forbids extra auth layers, so leveraging Neo4j credentials is the safest path. Caching the normalized schema/sample payloads lets analysts keep working during short outages, meets the 5-minute retry requirement, and keeps the schema overview accessible for Principle IX consistency.  
**Alternatives considered:** Duplicate authentication layers (adds complexity and violates constraints) or offline snapshots outside Neo4j (loses the single source of truth and the ability to highlight coverage gaps reliably).  
