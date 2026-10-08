# ADR-0036: Element id prefixes name the element's own ArchiMate type

- **Status:** Accepted
- **Date:** 2026-10-08
- **Sources:** GH #109; `architecture/model/elements.yaml`; ADR-0007 (id hashing)

## Context

`architecture/model/elements.yaml` ids are short, kebab-case, human-readable
(ADR-0007), and each carries an informal prefix — but the prefix scheme grew
organically, one prefix per contributor's judgement call, with no document
defining what a prefix is allowed to mean. That let `art-` end up meaning two
different things: the genuine ArchiMate `Artifact` type (Technology layer,
code packages) and, separately, 35 `DataObject`-typed elements prefixed
`art-` for "artefact" (the business term for the things flowing through the
compliance pipeline). The collision was not just cosmetic — GH #108's planning
work mistyped a new `DataObject` as `Artifact` in a draft because the `art-`
prefix implied the wrong metamodel type, and the error was caught only by a
manual check against existing ids, not by any gate.

## Decision

An element id prefix names the element's own ArchiMate type — never a loose
English synonym, business term, or role name that could be mistaken for a
different type. Where a prefix already denotes a type unambiguously, it stays
as hand-assigned text (not a generated code); this ADR records the convention
and the live legend, it does not change `build.py`'s hashing.

The 35 `DataObject` elements previously prefixed `art-*` (the artefact
input/output pipeline: policy documents, OSCAL catalogs/profiles, baselines,
blueprints, the ADR/roadmap/gate-decision chain, etc.) are renamed to `do-*`
(`do-policy-doc`, `do-oscal-catalog`, …). `art-*` now exclusively denotes
genuine ArchiMate `Artifact`-typed elements (code packages, deployment
artefacts): `art-flat-src`, `art-pkg-*`, `art-tech-oscal-workspace`,
`art-tech-ledger-file`.

Current prefix legend (derived from `elements.yaml`, authoritative at time of
writing — this table is illustrative, not re-synced on every model change):

| Prefix | ArchiMate type |
|---|---|
| `art-` | Artifact |
| `assess-` | Assessment |
| `bc-` | BusinessCollaboration |
| `bfn-` | BusinessFunction |
| `bi-` | BusinessInteraction |
| `bo-` | BusinessObject |
| `cap-` | Capability |
| `coa-` | CourseOfAction |
| `const-` | Constraint |
| `do-` | DataObject |
| `driver-` | Driver |
| `ext-` | ApplicationComponent (external system) |
| `fn-` | ApplicationFunction |
| `gap-` | Gap |
| `goal-` | Goal |
| `if-` | ApplicationInterface |
| `node-` | Node |
| `outcome-` | Outcome |
| `plat-` | Plateau |
| `principle-` | Principle |
| `process-` | BusinessProcess |
| `req-` | Requirement |
| `res-` | Resource |
| `role-` | BusinessRole |
| `stk-` | Stakeholder |
| `sw-` | SystemSoftware |
| `techfn-` | TechnologyFunction |
| `techproc-` | TechnologyProcess |
| `vs-` / `vss-` | ValueStream / ValueStreamStage |
| `wp-` | WorkPackage |

`store-`, `sub-` and `sys-` are grouping-role prefixes, not type codes (a
`DataObject` aggregation store, an `ApplicationComponent` subsystem, and a
`Grouping` respectively) — acceptable because they name a structural role the
model gives that element, not a different ArchiMate type.

## Consequences

- No prefix contradicts the ArchiMate type of the element it names; a reviewer
  can infer an id's type from its prefix alone, closing the class of error
  GH #108 hit.
- Adding a new element type requires picking a prefix that isn't already
  claimed by a different type; check this table (or re-derive it from
  `elements.yaml`) before inventing one.
- Any future id collision of this kind is a defect against this ADR, not a
  judgement call to make again from scratch.

## Alternatives considered

- **Redefine `art-` to mean "artefact" (the business term) and move the
  genuine `Artifact`-typed elements off it** — rejected: `Artifact` is the
  rarer group (11 ids) and the name every ArchiMate-literate reader expects
  `art-` to mean; moving it would trade one confusion for another.
- **Leave the scheme undocumented and just rename the colliding ids** —
  rejected: without a recorded rule, the same collision class can recur the
  next time a new element type needs a prefix.
