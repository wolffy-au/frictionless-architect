# Project Principles for Frictionless Architect (X-Accountant)

This document outlines the additional principles guiding the development of the architecture modelling experience, ensuring a consistent vision and high standards for every contribution.

## Constitution Additions

These additions are to be considered in conjunction with the Core Principles found at `.specify/memory/constitution.md`.

### VII. Model Integrity & Accuracy (Foundation of Trustworthy Models)

Architecture models must faithfully reflect the intended reality. Every element, relationship, viewpoint, and derived metric must be consistent, traceable, and free from silent corruption, because stakeholders depend on these diagrams to make strategic decisions.

- **Rules**: Schema definitions, property constraints, and derived metrics must be validated before changes are accepted. Changes that affect relationships or hierarchies must trigger automated consistency checks so invalid configurations cannot propagate. Change logs should capture modeling decisions that impact semantics.
- **Rationale**: Decision-making built on inaccurate architecture maps results in wasted effort and risky deployments. Absolute confidence in each representation is non-negotiable.

### VIII. Model Portability & Continuity (Preserving Architectural Memory)

Architectural knowledge spans releases, teams, and tooling surfaces. Models, exports, and version histories must survive upgrades and play nicely across ecosystem tools so the context behind decisions is never lost.

- **Rules**: Introducing or evolving a model or format must include documented migration paths for existing projects. Import/export routines (ArchiMate exchange, CSV/JSON snapshots, plugin interfaces) must preserve semantics, metadata, and linked artifacts. Platform integrations must include verification steps that guard against semantic drift.
- **Rationale**: Breaking portability or forcing costly migrations chases away architects and severs institutional memory. Model continuity is the backbone of long-lived architecture efforts.

### IX. Cross-Platform Consistency (Universal Accessibility)

The modelling experience must feel stable and reliable across every supported environment (desktop, OS, display configuration). Platform differences should not leak through in behavior, visuals, or data fidelity.

- **Rules**: UI components, rendering paths, and performance expectations must be tested across platforms to ensure consistent results. Platform-specific integrations (file dialogs, clipboard handling, GPU rendering) must degrade gracefully while preserving data integrity.
- **Rationale**: Architects working on different machines or sharing artifacts rely on parity to communicate effectively. Inconsistent behavior creates confusion and undermines collaboration.
