# Feature Specification: Neo4j Schema Visualiser

**Feature Branch**: `002-neo4j-schema-ui`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Create a UI to visualise the schema of the neo4j data. Reference schema in sample-data/schema and use sample-data/sample-00 to populate with some sample data."

## Clarifications

### Session 2026-04-04

- Q: How should the visualiser behave if the sample dataset is missing or cannot be loaded? → A: Display a warning banner about the missing data while keeping the schema element and relationship lists visible so analysts can still inspect the model.
- Q: What performance and availability targets should the schema visualiser guarantee? → A: Load responses should appear within 2 seconds and the feature should maintain 99.5% availability so analysts can rely on it during work hours without overly strict SLAs.
- Q: What reliability/observability behavior should be enforced when the schema/sample data service fails? → A: Retry the load within 5 minutes, show a non-blocking warning, and keep the read-only schema overview accessible while recovery occurs so analysts can continue referencing definitions. *(Retry made automatic, 2026-10-04 below.)*
- Q: What security posture should the visualiser adopt for access control? → A: Reuse the existing Neo4j read permissions so the visualiser enforces whatever access guardrails already protect the data, avoiding extra auth layers. *(Narrowed to the single service credential, 2026-10-04 below.)*

### Session 2026-10-04

- Q: What is "the schema" behind FR-001/004/005? → A: The `architecture/model/` type system: `pyArchimate.ArchiType` plus the relationship matrix (ADR-0008), extended by the multi-spec types (GH #73). The ArchiMate XSDs only validate sample/exchange XML (ADR-0022).
- Q: Who is the access model for? → A: A single-user local MVP (ADR-0024): one configured Neo4j service credential, no per-user enforcement.
- Q: Is SC-006's retry automatic? → A: Yes. After a failed load a background task retries, at most 5 minutes apart, until it succeeds.
- Q: What happens to the UI requirements? → A: Superseded; the UI is now `schema-visualizer-ui` (#55, ADR-0005/0020). The API contract stays here.

## User Scenarios & Testing *(mandatory)*

Rendering in the scenarios below (highlighting, diagram/table switching) is owned by `schema-visualizer-ui` (#55); this spec's API supplies the data.

### User Story 1 - Schema Exploration (Priority: P1)

A data analyst needs to quickly understand the node, relationship, and view types defined in the Neo4j dataset so they can confidently plan queries and reports that align with the existing model.

**Why this priority**: Without a schema overview it is difficult to validate that new queries or dashboards will stay consistent with the defined architecture, so the analyst cannot start work.

**Independent Test**: Open the schema visualiser, confirm all element and relationship types from the model type system (FR-001) are listed, and match each to at least one entry from `sample-data/sample-00/Test Model Full.xml`.

**Acceptance Scenarios**:

1. **Given** the user opens the schema tab and the sample dataset is loaded, **When** they inspect the element list, **Then** each element type from the schema is shown with one or more sample nodes (e.g., ValueStream VS1, BusinessService Governance Service) drawn from `sample-data/sample-00/Test Model Full.xml`.
2. **Given** the schema contains relationships (Association), **When** the user selects that relationship type, **Then** the visualiser highlights the actual relationships between the sample nodes (e.g., the Association between VS1 and the Governance Service) and shows the source/target identifiers.

---

### User Story 2 - Model Assurance (Priority: P2)

A product owner wants to confirm that every schema directive (element, diagram, relationship) stays interoperable with business documents by seeing how it renders in both diagram and table form.

**Why this priority**: Interoperability across consumer tooling is a Constitution requirement, and having only raw schema files makes it hard to guarantee consistent presentation.

**Independent Test**: Switch between diagram preview and tabular schema summary, verifying that both representations mention the same fields (e.g., element identifier, types, labels) as defined in the schema files.

**Acceptance Scenarios**:

1. **Given** the schema file defines diagrams and views, **When** the owner switches to the diagram preview, **Then** the UI overlays the element positions (x, y, w, h) extracted from the sample view in `sample-data/sample-00/Test Model Full.xml` while showing the same relationships from the schema list.

---

### User Story 3 - Sample Verification (Priority: P3)

A stakeholder reviewing the Neo4j data needs a reproducible way to verify that a schema change still produces the same sample view before it reaches production.

**Why this priority**: Regression prevention is important, but this story can be validated after the core schema awareness flows are in place.

**Independent Test**: Reload the sample dataset, verify that previously noted sample elements (VS1, the Governance Service) and their association render again, and confirm that the schema summary still references the same definition files.

**Acceptance Scenarios**:

1. **Given** the visualiser loads the provided sample data, **When** the reviewer refreshes the sample view, **Then** the overview again presents the same nodes and relationships together with the specification that defines each type.

---

### Edge Cases

- What happens when the schema references a type (e.g., a new ArchiMate element) with no sample nodes in `sample-data/sample-00`?
- How does the visualiser behave if `Test Model Full.xml` defines multiple relationships between the same pair of elements (e.g., duplicate associations) or if nodes share identifiers? Parallel relationships with distinct identifiers are all listed; only a repeated identifier raises a warning.
- What if the validation XSDs are updated to a newer ArchiMate version (e.g., 3.1) but the sample data remains on 3.0-style nodes? *Resolved (ADR-0032)*: the ArchiMate 3.1 exchange-format XSDs keep the `http://www.opengroup.org/xsd/archimate/3.0/` namespace, so 3.0-namespaced sample data remains valid against them. A sample file declaring any other namespace is reported as a warning naming the expected namespace, and `/schema-payload/status` returns `sample_file_status: "invalid"` rather than rendering an empty model.
- What warning should appear if `sample-data/sample-00/Test Model Full.xml` cannot be loaded so analysts understand why sample instances are unavailable without being blocked?

## Requirements *(mandatory)*

All requirements explicitly account for Constitution Principles VII-IX where applicable.

### Functional Requirements

- **FR-001**: System MUST display a concise summary of every node, relationship, and view type in the `architecture/model/` type system (`pyArchimate.ArchiType` and the relationship matrix, ADR-0008; extended by the multi-spec types of GH #73, `ArchiType` alone until then), ensuring the displayed names and identifiers exactly match the definitions (Constitution Principle VII: System Integrity & Accuracy — data accuracy in schema translation).
- **FR-002**: System MUST pair each schema definition with at least one corresponding sample occurrence from `sample-data/sample-00/Test Model Full.xml`, including identifiers, labels, and coordinates, so stakeholders can verify how the schema translates into concrete data (Principle VIII: Durability & Interoperability).
- **FR-003**: Users MUST be able to switch between a diagram-centric overview (respecting the stored x/y/w/h styling) and a tabular schema breakdown that lists element/relationship attributes, ensuring consistent presentation across formats (Principle IX: Cross-Platform Consistency). *Moved to `schema-visualizer-ui` (#55); this spec keeps the payload both views read.*
- **FR-004**: System MUST expose the specification that defines each displayed type (e.g., ArchiMate 3.2) alongside it, so reviewers can trace back definitions (Principle VIII: Durability & Interoperability).
- **FR-005**: System MUST highlight schema coverage gaps by flagging any defined type that lacks a sample entry, providing a clear call-out so data stewards can address missing nodes before further modeling work (Principle VII: System Integrity & Accuracy — verification).
- **FR-006**: System MUST display a non-blocking warning when the sample data file is missing or unreadable, yet keep the schema summary accessible so users can continue investigation without being forced to restore the sample first (Principle IX: Cross-Platform Consistency).
- **FR-007**: System MUST read Neo4j only through its one configured read-only service credential, with no additional authentication layer (single-user local MVP, ADR-0024); per-user permission enforcement is deferred with RBAC/ABAC (Principle V: Security Practices — access control).

### Key Entities *(include if feature involves data)*

- **Model**: Represents the top-level container defined by the ArchiMate schema (identifier, name, namespace) and the entry point for loading sample data (`Test Model Full.xml`).
- **Element Type**: A node type from the model type system (FR-001) (e.g., ValueStream) with identifier, label, and allowable attributes; used to group sample nodes so users can understand each type's meaning.
- **Relationship Type**: Defines allowable connections (e.g., Association) with source/target restrictions from the relationship matrix; the UI should show sample relationships together with that directionality.
- **Diagram / View Node**: The visual specification (x, y, width, height, style) in the ArchiMate exchange format (`archimate3_View.xsd` validates it) that the UI uses to recreate layout previews from the sample file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of data reviewers can identify the schema file backing each displayed node type within 2 minutes of opening the visualiser.
- **SC-002**: 95% of testers can locate a specific sample element (e.g., VS1) and list its relationships after one guided walkthrough, demonstrating schema-to-data traceability.
- **SC-003**: Diagram and table views show the same element/relationship set without discrepancies in at least 99% of refreshes, validating cross-platform consistency.
- **SC-004**: Stakeholder surveys on schema clarity score at least 4 out of 5 for “understandability” once the visualiser is connected to the provided sample dataset.
- **SC-005**: Schema visualisation actions respond within 2 seconds and availability stays at or above 99.5% so analysts can depend on the tool during their work sessions.
- **SC-006**: When data access fails, the visualiser emits a non-blocking warning, keeps read-only schema views accessible from the cache or sample, and a background task retries the load automatically, at most 5 minutes apart, until it succeeds.
- **SC-007**: Every schema visualisation request reaches Neo4j only through the configured read-only service credential (ADR-0024).

## Assumptions

- The Neo4j instance holds the `architecture/model/` model, so its type system (FR-001) is the authoritative source; the XSDs under `sample-data/schema` validate sample/exchange XML only (ADR-0022).
- `sample-data/sample-00/Test Model Full.xml` remains available and representative of the typical dataset, so it can continue to serve as the sample load for demonstrations.
- Future type additions arrive through the type system and include explicit identifiers that the UI can match to Neo4j data.
