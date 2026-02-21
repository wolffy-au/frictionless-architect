<!--
  Sync Impact Report:
  - Version change: v1.0.1 -> v1.0.2
  - List of modified principles:
    - I. Code Quality (Added DRY)
    - II. Testing Standards (Added TDD and cross-ref)
    - V. Security Practices (New section)
  - Added sections: V. Security Practices
  - Removed sections: None
  - Templates requiring updates:
    - .specify/templates/plan-template.md (pending)
    - .specify/templates/spec-template.md (pending)
    - .specify/templates/tasks-template.md (pending)
  - Follow-up TODOs: None
-->

# SpecKit Constitution

## Core Principles

### I. Code Quality (Excellence through Clarity)

Logic must be self-documenting, modular, and adhere to SOLID principles. We prioritize readability over cleverness. Every function must have a clear purpose and minimal side effects.

- **Rules**: No "magic numbers," use descriptive naming, keep functions under 30 lines where possible. For detailed guidance on code structure and naming, refer to `TECHNICAL.md`'s "Code Style" and "File Structure" sections.
- **Rationale**: Maintainability is the primary constraint for long-term project health. We adhere to the **DRY (Don't Repeat Yourself)** principle to minimize redundancy and improve consistency.

### II. Testing Standards (Verified Correctness)

Automated tests are non-negotiable. Every feature must include unit and integration tests. Test coverage MUST prioritize critical paths and edge cases. We follow the Red-Green-Refactor cycle, embracing **Test-Driven Development (TDD)** principles.

- **Rules**: 100% coverage on core business logic; tests must be isolated and reproducible. For detailed testing practices and framework choices, see `TECHNICAL.md`'s "Patterns and Practices > Testing" section.
- **Rationale**: Tests provide the confidence to refactor and ensure regressions are caught early.

### III. User Experience Consistency (Unified Interface)

Interfaces MUST follow established patterns to ensure predictability. Whether CLI or GUI, the user's mental model MUST be respected. Error messages must be actionable and clear.

- **Rules**: Use consistent command structures for CLI; provide helpful error messages with resolution steps. For comprehensive guidance on API design principles that ensure consistency, refer to `TECHNICAL.md`.
- **Rationale**: Consistency reduces cognitive load and improves user trust and efficiency.

### IV. Performance Requirements (Efficiency by Design)

System responsiveness is a first-class citizen. Code must be optimized for resource efficiency. Any operation exceeding 200ms must be asynchronous or justified.

- **Rules**: Profile critical paths; avoid premature optimization but maintain O(n) awareness. Performance considerations are further detailed in `TECHNICAL.md`'s "Performance" section.
- **Rationale**: Performance is a feature; a slow system is a broken system for the user.

### V. Security Practices (Proactive Defense)

Security is paramount throughout the development lifecycle. We adhere to secure coding practices, referencing established guidelines such as **OWASP**, **CWE**, **CERT Secure Coding Standards**, etc.

- **Rules**: Never commit sensitive information; validate all user inputs; use environment variables for configuration. Detailed security guidelines are available in `TECHNICAL.md`'s "Security" section.
- **Rationale**: Protecting data and systems from threats is a fundamental responsibility.

### VI. State Management and Workflow Integrity (Predictable Evolution)

Logic must define clear lifecycles and state transitions for key entities to ensure predictable evolution and auditable workflows. Data integrity must be maintained through controlled state changes, preventing invalid transitions.

- **Rules**: Document entity lifecycles and state transition rules. Implement these rules rigorously. Refer to `TECHNICAL.md` for detailed patterns on implementing state management and workflow control.
- **Rationale**: Robust state management and enforced workflows enhance system predictability, reliability, audibility, and maintainability, crucial for governance and complex processes.

## Development Workflow

Our workflow is designed to ensure that every change is intentional and verified. It follows a sequence of:

1. **Specify**: Define requirements and user stories in a feature spec.
2. **Plan**: Research technical approaches, map out tasks, and generate design artifacts.
3. **Implement**: Execute tasks following the Red-Green-Refactor cycle.
4. **Verify**: Pass all quality gates before merging.
    For more on our patterns and practices, see `TECHNICAL.md`.

## Quality Gates

Before any feature is considered "Done," it must pass these gates:

- **Linting & Formatting**: Must pass all project-standard style checks, as detailed in `TECHNICAL.md`.
- **Test Suite**: All new and existing tests must pass, adhering to the standards in `TECHNICAL.md`.
- **Documentation**: READMEs, specs, and inline comments must be updated.
- **Constitution Check**: Implementation must be reviewed against these core principles.

## Governance

This constitution is the supreme guide for SpecKit development.

- **Amendments**: Proposed via PR; requires explanation of why the change improves project governance.
- **Versioning**: Follows semantic versioning.
- **Compliance**: All contributors must adhere to these principles; deviations must be justified in the `plan.md` complexity tracking section.

**Version**: 1.0.2 | **Ratified**: 2026-02-18 | **Last Amended**: 2026-02-21
