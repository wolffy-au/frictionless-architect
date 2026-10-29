# ADR-0039: Conversational solution modelling — scope, subsystem split, and relation to ADR-0037

- **Status:** Proposed
- **Date:** 2026-10-24
- **Sources:** GH #68 (epic, decision 8); GH #138; `architecture/model/elements.yaml`
  (`fn-solution-modelling`, `process-conversational-solution-modelling`)

<!-- adr-auditor 2026-10-29: evidence supports Accepted: fn-solution-modelling,
     process-conversational-solution-modelling and their edges are in architecture/model/, and the
     EPIC-003/002 spec cites this as decided placement. Held at Proposed until a human attests it
     (ADR-0012). The do-convention-rules question stays open (see Consequences). -->

## Context

GH #68's epic adds a conversational interface for the Solution Architect to refine a Solution
Design directly, with live re-rendered ArchiMate views. This risks being read as the same
feature GH #108/ADR-0037 already shipped — conversational authoring is also natural-language,
metamodel-validated, and live-rendered — but it is not: ADR-0037's `fn-conversational-authoring`
edits Candidate Architecture Options (`do-candidate-arch`) in the enterprise knowledge graph
(`store-akg`) for the Enterprise Architect role. GH #138 (epic item 0)
needs the new, distinct function recorded before it could be misread as redundant with
ADR-0037, and needs the subsystem split from #68's decision 8 recorded as load-bearing
(Principle X) before `/speckit-specify` (GH #139) builds on it.

Separately, GH #69's follow-on already gave `role-sec` and `role-dev` a minimal
business-layer presence (`bfn-security-assurance`, `bfn-implementation`) by wrapping each
role's one already-modelled touchpoint, rather than renaming any `bfn-*` id. That closed the
"re-cut `bfn-*`" half of #138's scope without this ADR; the conversational-modelling function
and the business-layer wiring it needs are what remain, and are what this ADR covers.

## Decision

1. **Distinct from ADR-0037.** `fn-solution-modelling` (new) edits `do-solution-design` in
   `store-patterns`; `fn-conversational-authoring` (ADR-0037) edits `do-candidate-arch` in
   `store-akg`. Neither function is merged or superseded, but giving `role-sa` its own,
   correctly-scoped equivalent exposed a correction to ADR-0037/spec 004's framing: that spec
   described `bfn-conversational-authoring`/`process-conversational-authoring`/
   `fn-conversational-authoring` as a "shared standing process" jointly Assigned from
   `role-ea` and `role-sa`, but nothing ever wired `role-sa` to anything beyond that one
   Assignment edge, and `role-sa`'s canonical journey (composing Solution Designs) never
   touches `do-candidate-arch`. All three elements are renamed "Conversational Candidate
   Architecture Authoring" (ids unchanged) and the `role-sa` Assignment is dropped; `role-sa`
   now reaches the shared `if-modelling-authoring-ui` through `fn-solution-modelling` instead
   (new `Serving fn-solution-modelling -> if-modelling-authoring-ui` edge, mirroring
   `fn-conversational-authoring`'s existing one).
2. **Subsystem placement (per #68 decision 8).** `fn-solution-modelling` is Assigned to
   `sub-library` (subsystem 2, `reusable-architecture-library`) — the same home as
   `fn-solution-compose`, the structured composition function it sits alongside. It Serves
   `fn-notation-engine` in `sub-modelling` (subsystem 6, `modelling-specification`) for
   rendering, mirroring `fn-conversational-authoring`'s existing edge, rather than a package
   dependency between the two subsystems.
3. **The agent edits a Solution Design, never `architecture/model/`.** Scope is bounded to one
   `do-solution-design` at a time; no promotion between enterprise and domain models (that is
   milestone D, GH #149).
4. **Business-layer placement.** The new process, `process-conversational-solution-modelling`,
   Composes into the *existing* `bfn-solution-design` alongside `process-solution-design`
   (structured, pattern-composed authoring) — same business capability, two authoring modes.
   No new `BusinessFunction` is added, matching the reasoning already recorded in
   `views.yaml`'s GH #108 commentary against folding shared/role-specific conversational work
   into a single function it doesn't belong to.

## Consequences

- A reviewer or future agent can tell the two conversational features apart by target artefact
  and store, not just by name — GH #139's spec can cite both without conflating them.
- Follow-up: GH #140 (chat/live-view UI shell) adds the `if-*` interface and its Serving edge;
  this ADR deliberately leaves that out rather than guess at #140's design.
- Open, not resolved here: whether `fn-solution-modelling` reads `do-convention-rules` the way
  `fn-conversational-authoring` does (ADR-0037 decision 3). Revisit when #140 or #142 (agent
  service) needs an answer — a Solution Design is bounded, not enterprise-wide, so the same
  conventions may not apply unmodified.
- Revisit if GH #151 (D4, many architects on shared models) changes the bounded-Solution-Design
  assumption in decision 3.

## Alternatives considered

- **Reuse/extend `fn-conversational-authoring` to also cover Solution Designs** — rejected:
  conflates two different target artefacts and stores under one function, and `views.yaml`
  already records a prior decision against collapsing shared/role-specific authoring into one
  function for exactly this reason.
- **A new `BusinessFunction` instead of a second process under `bfn-solution-design`** —
  rejected: the business capability ("produce a Solution Design") doesn't change, only the
  authoring mode does; a second function would duplicate the capability, not model a new one.
