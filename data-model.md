# Data Model

## Entities

### Architecture Artifacts

* **Description**: Executable or structured data (JSON/Markdown) representing architectural information.
* **Attributes**: Content (text/binary), Format (JSON, Markdown, etc.), Version.

### Architecture Decision Record (ADR)

* **Description**: Captures technical decisions, trade-offs, and their rationale. Requires human attestation.
* **Attributes**:
  * Title (string)
  * Status (enum: Draft, Under Review, Approved, Superseded)
  * Date (datetime)
  * Rationale (text)
  * Decision (text)
  * Consequences (text)
  * Human Attestation (string/signature - e.g., cryptographic signature)
* **State Transitions**: Draft -> Under Review -> Approved -> Superseded.
* **Validation Rules**: Requires human cryptographic sign-off for Approved/Superseded status.

### Semantic System Model

* **Description**: A graph-based model mapping microservices, data domains, Critical Business Services (CBS), and regulations.
* **Attributes**:
  * Nodes: Microservices, Data Domains, CBS, Regulations.
  * Edges: Represent relationships (e.g., 'uses', 'supports', 'governed by').
* **Relationships**: Links microservices to CBS and regulations; CBS to data domains.

### Critical Business Service (CBS)

* **Description**: Defined services critical to business operations, with mapped technical components and associated impact tolerances.
* **Attributes**:
  * Name (string)
  * Description (text)
  * Impact Tolerances (e.g., RTO, RPO)
  * Mapped Technical Components (list of references)
  * Associated Regulations (list of references)
* **Validation Rules**: Must align with APRA CPS 230/234 requirements.

### Policy

* **Description**: Governing rules for compliance and security.
* **Attributes**:
  * Name (string)
  * Type (e.g., CPS 230, CPS 234, OPA Rego)
  * Content/Rules (text/code)
  * Scope (e.g., applies to CBS, microservices)
* **Validation Rules**: Must be machine-readable and enforceable.

## Relationships

* **ADR** `governs` **Architecture Artifacts** (or components/decisions within them).
* **ADR** `is_attested_by` **Human Architect**.
* **CBS** `is_supported_by` **Microservices**.
* **CBS** `is_governed_by` **Regulations** and **Policies**.
* **Semantic System Model** `represents` **Microservices**, **Data Domains**, **CBS**, **Regulations**.
* **Policy** `enforces_rules_on` **CBS**, **Microservices**, **Data Domains**.

## Validation Rules Summary

* **ADR Sign-off**: Mandatory human cryptographic signature for approved ADRs.
* **Code Quality**: Adherence to DRY, SOLID principles; readability.
* **Testing**: TDD, automated tests, 100% core logic coverage.
* **Performance**: Operations < 200ms where justified.
* **Security**: Data encryption (rest/transit), input validation.
* **Authentication/Authorization**: JWTs, ABAC.
* **Query Performance**: Regulatory Traceability Matrix queries < 1 minute.

## State Transitions

* **ADR**: Draft -> Under Review -> Approved -> Superseded.
