# ADR-0038: Section-B roles are canonical; other role lists specialise them

- **Status:** Accepted
- **Date:** 2026-10-18
- **Sources:** GH #69; GH #45; `specs/EPIC-001-governance-platform/spec.md`; `architecture/model/elements.yaml` (`role-*`)

## Context

Three role lists disagreed: spec 001 named a single undifferentiated "Architect" persona
alongside Developer, Compliance Officer and System Administrator/Platform Engineer;
`architecture/model/` section B already modelled six `BusinessRole`s (Enterprise Architect,
Solution Architect, Security Architect/Threat Modeller, Developer, Compliance Officer/Auditor,
Platform Operations); and GH #45's role-journey list (Policy conversion admin, Policy author,
Patterns admin, Security assessor, Pattern contributor, Implementation contributor, Solution
architect) only shared "Solution architect" with the model. Journey APIs are designed one per
role, and access control derives from them (FR-016), so one canonical role set is needed
before that work can proceed. The maintainer decided on 2026-09-26 that the section-B roles
are canonical (Principle X: decisions belong in `architecture/model/`).

## Decision

The six `BusinessRole`s already in `architecture/model/elements.yaml` section B are the
platform's canonical roles. GH #45's role-journey entries are modelled as `Specialization`s
of them, not as a parallel role set:

| GH #45 entry | Specialises | Basis |
|---|---|---|
| Policy conversion admin | Compliance Officer / Auditor (`role-compliance`) | assigned to `bfn-policy-conversion` |
| Policy author | Compliance Officer / Auditor | *Policy & Standards Authoring* is part of that function |
| Patterns admin | Enterprise Architect (`role-ea`) | assigned to `bfn-pattern-blueprint-traceability`; curates patterns per `sub-library` Serving edge |
| Security assessor | Security Architect / Threat Modeller (`role-sec`) | name match; runs threat models in `sub-library` |
| Pattern contributor | Solution Architect (`role-sa`) | contributes candidate patterns for the Solution Architect to curate, distinct from the Enterprise Architect's admin function |
| Implementation contributor | Developer (`role-dev`) | name match; consumes generated specifications |
| Solution architect | *is* Solution Architect (`role-sa`) | the same role, no new element |

Spec 001's single "Architect" persona is split: the primary-users line names all three
architect roles (Enterprise, Solution, Security), while the ADR-review/attestation/drift-
conflict journeys that already existed in that spec's text (FR-006, the P1 journeys, the edge
cases) name Enterprise Architect specifically, since that is the only one of the three whose
function (`bfn-architecture-strategy`, `bfn-drift-management` "approves architectural drift")
matches what those journeys describe.

## Consequences

- `architecture/model/elements.yaml` gains six new `BusinessRole`s (`role-policy-conversion-admin`,
  `role-policy-author`, `role-patterns-admin`, `role-security-assessor`,
  `role-pattern-contributor`, `role-implementation-contributor`), each with exactly one
  `Specialization` edge to its section-B role in `relationships.yaml`.
- Future journey-API and access-control work derives its role set from `architecture/model/`
  section B, not from spec 001 or GH #45 directly.
- Modelling the role journeys themselves (re-cutting the `bfn-*` functions) is out of scope
  here and tracked as epic item 0 of GH #68.
- If GH #45 gains a role with no clear section-B parent, that is a new decision and reopens
  this ADR rather than being added silently.

## Alternatives considered

- **Keep three separate role lists, reconciled only in code** — rejected: FR-016 needs one
  canonical set before journey APIs and access control can be derived from it; reconciling in
  code every time would re-litigate the same mapping ad hoc.
- **Promote GH #45's finer-grained roles to canonical, retire the section-B six** — rejected:
  the section-B roles already carry `Assignment`s to business functions and `Serving` edges to
  subsystems throughout the model; replacing them would be a much larger, unrelated change for
  no stated benefit over specialising them.
