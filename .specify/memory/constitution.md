<!--
  Sync Impact Report:
  - Version change: v1.0.0 → v1.0.1
  - List of modified principles:
    - II. Testing Standards (Refined wording)
    - III. User Experience Consistency (Refined wording)
  - Added sections: None
  - Removed sections: None
  - Templates requiring updates:
    - .specify/templates/plan-template.md (✅ aligned)
    - .specify/templates/spec-template.md (✅ aligned)
    - .specify/templates/tasks-template.md (✅ aligned)
  - Follow-up TODOs: None
-->

# SpecKit Constitution

## Core Principles

### I. Code Quality (Excellence through Clarity)
Logic must be self-documenting, modular, and adhere to SOLID principles. We prioritize readability over cleverness. Every function must have a clear purpose and minimal side effects.
- **Rules**: No "magic numbers," use descriptive naming, keep functions under 30 lines where possible.
- **Rationale**: Maintainability is the primary constraint for long-term project health.

### II. Testing Standards (Verified Correctness)
Automated tests are non-negotiable. Every feature must include unit and integration tests. Test coverage MUST prioritize critical paths and edge cases. We follow the Red-Green-Refactor cycle.
- **Rules**: 100% coverage on core business logic; tests must be isolated and reproducible.
- **Rationale**: Tests provide the confidence to refactor and ensure regressions are caught early.

### III. User Experience Consistency (Unified Interface)
Interfaces MUST follow established patterns to ensure predictability. Whether CLI or GUI, the user's mental model MUST be respected. Error messages must be actionable and clear.
- **Rules**: Use consistent command structures for CLI; provide helpful error messages with resolution steps.
- **Rationale**: Consistency reduces cognitive load and improves user trust and efficiency.

### IV. Performance Requirements (Efficiency by Design)
System responsiveness is a first-class citizen. Code must be optimized for resource efficiency. Any operation exceeding 200ms must be asynchronous or justified.
- **Rules**: Profile critical paths; avoid premature optimization but maintain O(n) awareness.
- **Rationale**: Performance is a feature; a slow system is a broken system for the user.

## Development Workflow

Our workflow is designed to ensure that every change is intentional and verified.
1. **Specify**: Define requirements and user stories in a feature spec.
2. **Plan**: Research technical approaches and map out tasks.
3. **Implement**: Execute tasks following the Red-Green-Refactor cycle.
4. **Verify**: Pass all quality gates before merging.

## Quality Gates

Before any feature is considered "Done," it must pass these gates:
- **Linting & Formatting**: Must pass all project-standard style checks.
- **Test Suite**: All new and existing tests must pass.
- **Documentation**: READMEs, specs, and inline comments must be updated.
- **Constitution Check**: Implementation must be reviewed against these core principles.

## Governance

This constitution is the supreme guide for SpecKit development.
- **Amendments**: Proposed via PR; requires explanation of why the change improves project governance.
- **Versioning**: Follows semantic versioning.
- **Compliance**: All contributors must adhere to these principles; deviations must be justified in the `plan.md` complexity tracking section.

**Version**: 1.0.1 | **Ratified**: 2026-02-18 | **Last Amended**: 2026-02-20
