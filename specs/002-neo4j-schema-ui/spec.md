# Feature Specification: Neo4j Schema Visualiser

**Feature Branch**: `002-neo4j-schema-ui`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Create a UI to visualise the schema of the neo4j data. Reference schema in sample-data/schema and use sample-data/sample-00 to populate with some sample data."

## Clarifications

### Session 2026-04-04

- Q: How should the visualiser behave if the sample dataset is missing or cannot be loaded? → A: Display a warning banner about the missing data while keeping the schema element and relationship lists visible so analysts can still inspect the model.
- Q: What performance and availability targets should the schema visualiser guarantee? → A: Load responses should appear within 2 seconds and the feature should maintain 99.5% availability so analysts can rely on it during work hours without overly strict SLAs.
- Q: What reliability/observability behavior should be enforced when the schema/sample data service fails? → A: Retry the load within 5 minutes, show a non-blocking warning, and keep the read-only schema overview accessible while recovery occurs so analysts can continue referencing definitions.
- Q: What security posture should the visualiser adopt for access control? → A: Reuse the existing Neo4j read permissions so the visualiser enforces whatever access guardrails already protect the data, avoiding extra auth layers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Schema Exploration (Priority: P1)

A data analyst needs to quickly understand the node, relationship, and view types defined in the Neo4j dataset so they can confidently plan queries and reports that align with the existing model.

**Why this priority**: Without a schema overview it is difficult to validate that new queries or dashboards will stay consistent with the defined architecture, so the analyst cannot start work.

**Independent Test**: Open the schema visualiser, confirm all element and relationship types from `sample-data/schema/archimate3_Model.xsd` are listed, and match each to at least one entry from `sample-data/sample-00/Test Model.xml`.

**Acceptance Scenarios**:

1. **Given** the user opens the schema tab and the sample dataset is loaded, **When** they inspect the element list, **Then** each element type from the schema is shown with one or more sample nodes (e.g., ValueStream VS1, VS2) drawn from `sample-data/sample-00/Test Model.xml`.
2. **Given** the schema contains relationships (Association), **When** the user selects that relationship type, **Then** the visualiser highlights the actual relationships between the sample nodes (e.g., the Association between VS1 and VS2) and shows the source/target identifiers.

---

### User Story 2 - Model Assurance (Priority: P2)

A product owner wants to confirm that every schema directive (element, diagram, relationship) stays interoperable with business documents by seeing how it renders in both diagram and table form.

**Why this priority**: Interoperability across consumer tooling is a Constitution requirement, and having only raw schema files makes it hard to guarantee consistent presentation.

**Independent Test**: Switch between diagram preview and tabular schema summary, verifying that both representations mention the same fields (e.g., element identifier, types, labels) as defined in the schema files.

**Acceptance Scenarios**:

1. **Given** the schema file defines diagrams and views, **When** the owner switches to the diagram preview, **Then** the UI overlays the element positions (x, y, w, h) extracted from the sample view in `sample-data/sample-00/Test Model.xml` while showing the same relationships from the schema list.

---

### User Story 3 - Sample Verification (Priority: P3)

A stakeholder reviewing the Neo4j data needs a reproducible way to verify that a schema change still produces the same sample view before it reaches production.

**Why this priority**: Regression prevention is important, but this story can be validated after the core schema awareness flows are in place.

**Independent Test**: Reload the sample dataset, verify that previously noted sample elements (VS1, VS2) and their association render again, and confirm that the schema summary still references the same definition files.

**Acceptance Scenarios**:

1. **Given** the visualiser loads the provided sample data, **When** the reviewer refreshes the sample view, **Then** the overview again presents the same nodes and relationships together with the source schema filenames (archimate3_Model, archimate3_View).

---

### Edge Cases

- What happens when the schema references a type (e.g., a new ArchiMate element) with no sample nodes in `sample-data/sample-00`?
- How does the visualiser behave if `Test Model.xml` defines multiple relationships between the same pair of elements (e.g., duplicate associations) or if nodes share identifiers?
- What if the schema files are updated to a newer ArchiMate version (e.g., 3.1) but the sample data remains on 3.0-style nodes?
- What warning should appear if `sample-data/sample-00/Test Model.xml` cannot be loaded so analysts understand why sample instances are unavailable without being blocked?

## Requirements *(mandatory)*

All requirements explicitly account for Constitution Principles VII-IX where applicable.

### Functional Requirements

- **FR-001**: System MUST display a concise summary of every node, relationship, and view type declared in the ArchiMate schema files under `sample-data/schema`, ensuring the displayed names and identifiers exactly match the schema definitions (Constitution Principle VII: Financial Data Accuracy / Data Accuracy in schema translation).
- **FR-002**: System MUST pair each schema definition with at least one corresponding sample occurrence from `sample-data/sample-00/Test Model.xml`, including identifiers, labels, and coordinates, so stakeholders can verify how the schema translates into concrete data (Principle IX: Data Longevity & Interoperability).
- **FR-003**: Users MUST be able to switch between a diagram-centric overview (respecting the stored x/y/w/h styling) and a tabular schema breakdown that lists element/relationship attributes, ensuring consistent presentation across formats (Principle IX: Cross-Platform Consistency).
- **FR-004**: System MUST expose the source schema file name (e.g., `archimate3_Model.xsd`, `archimate3_View.xsd`) alongside each displayed type so updates to those files immediately surface in the UI and reviewers can trace back definitions (Principle IX / Interoperability).
- **FR-005**: System MUST highlight schema coverage gaps by flagging any defined type that lacks a sample entry, providing a clear call-out so data stewards can address missing nodes before further modeling work (Principle VII: Data Accuracy and verification).
- **FR-006**: System MUST display a non-blocking warning when the sample data file is missing or unreadable, yet keep the schema summary accessible so users can continue investigation without being forced to restore the sample first (Principle IX: Cross-Platform Consistency).
- **FR-007**: System MUST enforce the Neo4j read permission model for the visualiser so access mirrors the existing data guardrails without introducing an additional authentication layer (Principle VII: Data Accuracy and Access Control).

### Key Entities *(include if feature involves data)*

- **Model**: Represents the top-level container defined by the ArchiMate schema (identifier, name, namespace) and the entry point for loading sample data (`Test Model.xml`).
- **Element Type**: A schema-defined node (e.g., ValueStream) with identifier, label, and allowable attributes; used to group sample nodes so users can understand each type's meaning.
- **Relationship Type**: Defines allowable connections (e.g., Association) with source/target restrictions; the UI should show sample relationships together with schema-defined directionality.
- **Diagram / View Node**: The visual specification from `archimate3_View.xsd` (x, y, width, height, style) that the UI uses to recreate layout previews from the sample file.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of data reviewers can identify the schema file backing each displayed node type within 2 minutes of opening the visualiser.
- **SC-002**: 95% of testers can locate a specific sample element (e.g., VS1) and list its relationships after one guided walkthrough, demonstrating schema-to-data traceability.
- **SC-003**: Diagram and table views show the same element/relationship set without discrepancies in at least 99% of refreshes, validating cross-platform consistency.
- **SC-004**: Stakeholder surveys on schema clarity score at least 4 out of 5 for “understandability” once the visualiser is connected to the provided sample dataset.
- **SC-005**: Schema visualisation actions respond within 2 seconds and availability stays at or above 99.5% so analysts can depend on the tool during their work sessions.
- **SC-006**: When data access fails, the visualiser retries load within 5 minutes, emits a non-blocking warning, and keeps read-only schema views accessible so analysts can continue referencing definitions during recovery.
- **SC-007**: Every schema visualisation request respects Neo4j read permissions so only authorized roles can see the data, matching the existing database access control.

## Assumptions

- The Neo4j instance uses the ArchiMate 3 schema definitions provided under `sample-data/schema`, so the UI can rely on those files as the authoritative source.
- `sample-data/sample-00/Test Model.xml` remains available and representative of the typical dataset, so it can continue to serve as the sample load for demonstrations.
- Future schema updates will continue to follow the XSD structure (elements, relationships, views) and include explicit identifiers that the UI can match to Neo4j data.
