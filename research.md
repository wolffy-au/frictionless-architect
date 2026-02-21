# Research Tasks

This document outlines the research tasks required to resolve ambiguities and define technical choices for the Frictionless Architecture & Governance Platform.

## Phase 0: Research

### Research 1: Python Environment and Frameworks

* **Task**: Investigate specific Python versions and recommended web frameworks for building a high-performance, secure CLI and service, considering FastAPI. Define version constraints and primary framework.
* **Rationale**: To ensure a robust, maintainable, and performant backend for the governance platform.
* **Alternatives Considered**: Node.js, Go (evaluated against Python's ecosystem and existing requirements).

### Research 2: Semantic System Model Ontology

* **Task**: Determine the most suitable ontology or standard for representing architectural components (microservices, data domains, CBS, regulations) in a Semantic System Model for governance. Evaluate options like UML, ArchiMate, C4 Model, Backstage Software Catalog, or custom definition.
* **Rationale**: To establish a standardized, machine-readable representation of the architecture for effective governance and visualization.
* **Alternatives Considered**: Custom ontology, UML, ArchiMate, C4 Model, IT4IT, TOGAF.
* **Opinion**: We can map these various ontologies to each other and have one archtype relate to a number of different frameworks representing a similar archtype. For example, a UML Component maps to an ArchiMate Application Component, a C4 L3 Component, and an IT4IT Digital Product, all represented by a single node in the graph database.

### Research 3: Critical Business Services (CBS) Definition

* **Task**: Define the essential attributes, lifecycle states, and mapping schema for Critical Business Services (CBS) in the context of APRA CPS 230/234 compliance.
* **Rationale**: To accurately model and map critical business functions to technical components for resilience and regulatory reporting.
* **Alternatives Considered**: Existing industry definitions, simplified internal model.

### Research 4: Regulatory Mapping

* **Task**: Identify and document specific regulatory requirements beyond APRA CPS 230/234 that are relevant to a financial institution's architecture governance platform. Focus on aspects related to data security, resilience, and auditability.
* **Rationale**: To ensure comprehensive compliance coverage beyond the explicitly mentioned regulations.
* **Alternatives Considered**: Focusing only on mentioned regulations (insufficient scope).

### Research 5: Break-Glass Protocol Details

* **Task**: Design the detailed workflow and logging requirements for the "Break-Glass" protocol, including conditions for activation, approval process, expiration handling, and audit trail logging.
* **Rationale**: To formalize an emergency override mechanism that balances operational needs with governance and audit requirements.
* **Alternatives Considered**: No emergency override, manual drift reporting.

### Research 6: PII Anonymization Gateway

* **Task**: Research and select appropriate libraries or techniques for a PII Anonymization Gateway in Python, considering performance, accuracy, and compliance with data privacy regulations.
* **Rationale**: To protect sensitive data during LLM processing while enabling effective analysis.
* **Alternatives Considered**: Tokenization, pseudonymization, data masking.

### Research 7: PostgreSQL Configuration

* **Task**: Determine recommended version and configuration best practices for PostgreSQL when used as a metadata store for an architecture governance platform, considering performance, scalability, and security.
* **Rationale**: To ensure reliable and efficient storage of platform metadata.
* **Alternatives Considered**: Other relational databases (MySQL, SQL Server), NoSQL databases.

### Research 8: Neo4j Knowledge Graph Design

* **Task**: Define the schema and best practices for using Neo4j as a Knowledge Graph for architectural components, regulations, and ADRs. Specify Neo4j version and data modeling approach.
* **Rationale**: To leverage graph capabilities for complex relationship analysis and querying of architectural data.
* **Alternatives Considered**: Relational database for graph data, other graph databases.

### Research 9: ADR Cryptographic Signing

* **Task**: Select the cryptographic signing mechanism for ADRs (e.g., GPG, Ed25519, integration with HSMs) that ensures legal auditability and tamper-proofing.
* **Rationale**: To provide irrefutable proof of human attestation and maintain the integrity of ADRs.
* **Alternatives Considered**: Simple digital signatures, blockchain-based signing.

### Research 10: Regulatory Traceability Matrix Design

* **Task**: Design the data structure and query interface for the Regulatory Traceability Matrix, ensuring efficient natural-language querying and integration with the Semantic System Model.
* **Rationale**: To enable compliance officers to easily query and verify regulatory adherence.
* **Alternatives Considered**: Manual mapping tables, keyword-based search.

### Research 11: API Contract Specifications

* **Task**: Specify the exact versions for OpenAPI (e.g., v3.0.x), JSON Schema, and YAML that will be used for API contracts and data serialization.
* **Rationale**: To ensure consistency and compatibility in API definitions and data exchange.
* **Alternatives Considered**: Older OpenAPI versions, different schema languages.

### Research 12: JWT Authentication Implementation

* **Task**: Define the JWT implementation details for authentication, including signing algorithms (e.g., HS256, RS256), token expiration, and refresh mechanisms.
* **Rationale**: To secure API access and user sessions with a standard, flexible mechanism.
* **Alternatives Considered**: OAuth 2.0, session cookies.

### Research 13: ABAC Policy Framework

* **Task**: Choose an Attribute-Based Access Control (ABAC) policy definition language or framework suitable for defining complex authorization rules based on attributes of users, resources, and actions.
* **Rationale**: To implement fine-grained, flexible, and scalable authorization policies.
* **Alternatives Considered**: Role-Based Access Control (RBAC), policy engines like OPA (Open Policy Agent).

### Research 14: Data Encryption Standards

* **Task**: Specify the encryption standards and algorithms for data at rest (e.g., AES-256) and in transit (e.g., TLS 1.2/1.3).
* **Rationale**: To ensure the confidentiality and integrity of sensitive data throughout its lifecycle.
* **Alternatives Considered**: Different encryption algorithms, older TLS versions.

### Research 15: Threat Modeling and Scanning Tools

* **Task**: Identify suitable tools and establish a frequency for automated scanning of the platform's "As-Built" state for threat modeling (e.g., vulnerability scanners, configuration checkers).
* **Rationale**: To proactively identify and mitigate security vulnerabilities in the deployed infrastructure.
* **Alternatives Considered**: Manual security reviews, ad-hoc scans.

### Research 16: Python Specifics beyond FastAPI

* **Task**: Investigate specific Python versions and recommended web frameworks for building a high-performance, secure CLI and service, considering FastAPI. Define version constraints and primary framework.
* **Rationale**: To ensure a robust, maintainable, and performant backend for the governance platform.
* **Alternatives Considered**: Node.js, Go (evaluated against Python's ecosystem and existing requirements).

### Research 17: Semantic System Model Ontology Standardization

* **Task**: Determine the most suitable ontology or standard for representing architectural components (microservices, data domains, CBS, regulations) in a Semantic System Model for governance. Evaluate options like C4 Model, Backstage Software Catalog, or custom definition.
* **Rationale**: To establish a standardized, machine-readable representation of the architecture for effective governance and visualization.
* **Alternatives Considered**: Custom ontology, ArchiMate, TOGAF.

### Research 18: CBS Definition Schema

* **Task**: Define the essential attributes, lifecycle states, and mapping schema for Critical Business Services (CBS) in the context of APRA CPS 230/234 compliance.
* **Rationale**: To accurately model and map critical business functions to technical components for resilience and regulatory reporting.
* **Alternatives Considered**: Existing industry definitions, simplified internal model.

### Research 19: Additional Regulations

* **Task**: Identify and document specific regulatory requirements beyond APRA CPS 230/234 that are relevant to a financial institution's architecture governance platform. Focus on aspects related to data security, resilience, and auditability.
* **Rationale**: To ensure comprehensive compliance coverage beyond the explicitly mentioned regulations.
* **Alternatives Considered**: Focusing only on mentioned regulations (insufficient scope).

### Research 20: Break-Glass Protocol Details

* **Task**: Design the detailed workflow and logging requirements for the "Break-Glass" protocol, including conditions for activation, approval process, expiration handling, and audit trail logging.
* **Rationale**: To formalize an emergency override mechanism that balances operational needs with governance and audit requirements.
* **Alternatives Considered**: No emergency override, manual drift reporting.

### Research 21: PII Anonymization Gateway Libraries

* **Task**: Research and select appropriate libraries or techniques for a PII Anonymization Gateway in Python, considering performance, accuracy, and compliance with data privacy regulations.
* **Rationale**: To protect sensitive data during LLM processing while enabling effective analysis.
* **Alternatives Considered**: Tokenization, pseudonymization, data masking.

### Research 22: PostgreSQL Best Practices

* **Task**: Determine recommended version and configuration best practices for PostgreSQL when used as a metadata store for an architecture governance platform, considering performance, scalability, and security.
* **Rationale**: To ensure reliable and efficient storage of platform metadata.
* **Alternatives Considered**: Other relational databases (MySQL, SQL Server), NoSQL databases.

### Research 23: Neo4j Knowledge Graph Schema

* **Task**: Define the schema and best practices for using Neo4j as a Knowledge Graph for architectural components, regulations, and ADRs. Specify Neo4j version and data modeling approach.
* **Rationale**: To leverage graph capabilities for complex relationship analysis and querying of architectural data.
* **Alternatives Considered**: Relational database for graph data, other graph databases.

### Research 24: ADR Signing Mechanism

* **Task**: Select the cryptographic signing mechanism for ADRs (e.g., GPG, Ed25519, integration with HSMs) that ensures legal auditability and tamper-proofing.
* **Rationale**: To provide irrefutable proof of human attestation and maintain the integrity of ADRs.
* **Alternatives Considered**: Simple digital signatures, blockchain-based signing.

### Research 25: Regulatory Traceability Matrix Design

* **Task**: Design the data structure and query interface for the Regulatory Traceability Matrix, ensuring efficient natural-language querying and integration with the Semantic System Model.
* **Rationale**: To enable compliance officers to easily query and verify regulatory adherence.
* **Alternatives Considered**: Manual mapping tables, keyword-based search.

### Research 26: API Contract Specifications

* **Task**: Specify the exact versions for OpenAPI (e.g., v3.0.x), JSON Schema, and YAML that will be used for API contracts and data serialization.
* **Rationale**: To ensure consistency and compatibility in API definitions and data exchange.
* **Alternatives Considered**: Older OpenAPI versions, different schema languages.

### Research 27: JWT Authentication Implementation

* **Task**: Define the JWT implementation details for authentication, including signing algorithms (e.g., HS256, RS256), token expiration, and refresh mechanisms.
* **Rationale**: To secure API access and user sessions with a standard, flexible mechanism.
* **Alternatives Considered**: OAuth 2.0, session cookies.

### Research 28: ABAC Policy Framework Selection

* **Task**: Choose an Attribute-Based Access Control (ABAC) policy definition language or framework suitable for defining complex authorization rules based on attributes of users, resources, and actions.
* **Rationale**: To implement fine-grained, flexible, and scalable authorization policies.
* **Alternatives Considered**: Role-Based Access Control (RBAC), policy engines like OPA (Open Policy Agent).

### Research 29: Data Encryption Standards

* **Task**: Specify the encryption standards and algorithms for data at rest (e.g., AES-256) and in transit (e.g., TLS 1.2/1.3).
* **Rationale**: To ensure the confidentiality and integrity of sensitive data throughout its lifecycle.
* **Alternatives Considered**: Different encryption algorithms, older TLS versions.

### Research 30: Threat Modeling & Scanning Tools

* **Task**: Identify suitable tools and establish a frequency for automated scanning of the platform's "As-Built" state for threat modeling (e.g., vulnerability scanners, configuration checkers).
* **Rationale**: To proactively identify and mitigate security vulnerabilities in the deployed infrastructure.
* **Alternatives Considered**: Manual security reviews, ad-hoc scans.
