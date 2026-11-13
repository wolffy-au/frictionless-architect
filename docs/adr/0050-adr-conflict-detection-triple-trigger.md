# ADR-0050: ADR-conflict detection runs on submission, on demand, and on a weekly audit sweep

- **Status:** Accepted
- **Date:** 2026-11-09
- **Sources:** `specs/EPIC-001-governance-platform/spec.md` FR-014, Edge Cases ("Two ADRs
  conflict: the system flags the contradiction and requires a human Enterprise Architect to
  resolve it before either is Approved"); GH #199

## Context

FR-014 requires the platform to detect when a new decision contradicts an existing ADR, but
left open when that check runs. A single trigger does not cover every case: checking only at
submission misses contradictions that surface later, when an ADR accepted against the
model-at-the-time turns out to conflict with another ADR accepted afterwards; checking only on
demand does not guarantee every ADR is ever checked at all.

## Decision

Conflict detection runs on **three triggers**:

1. **Automatic, on submission** — every new ADR is checked against the existing accepted ADR
   set before it can leave `Draft`. This is the primary compliance gate: an unresolved conflict
   blocks `Approved`/`Superseded` per the spec's Edge Cases.
2. **On demand** — an architect can explicitly re-run the check against a draft at any point
   while iterating, without needing a full submission cycle.
3. **Weekly scheduled audit sweep** — a recurring job re-checks the full accepted ADR log for
   contradictions introduced after the fact (e.g. two ADRs each consistent with the model at
   their own acceptance time, now found to conflict). Findings are surfaced to a human reviewer
   for resolution (a new ADR or an amendment); the sweep never auto-reverts an already-`Accepted`
   ADR.

## Consequences

- The submission-time check is the one FR-014 literally requires ("MUST detect when a new
  decision contradicts an existing ADR") and is the only one that blocks a transition.
- The on-demand check supports iterative drafting with immediate feedback.
- The weekly sweep is advisory/reporting only; it needs a scheduling mechanism, left to the
  package's `plan.md`.
- The package spec (GH #201) describes all three triggers at the what/why level; scheduling
  implementation, API shape, and the sweep's report format are plan-level work.

## Alternatives considered

- **Automatic-only** — rejected: misses conflicts introduced by later ADRs against
  already-`Accepted` ones, since nothing re-checks the log after acceptance.
- **On-demand-only** — rejected: does not guarantee every ADR is ever checked, a weaker
  compliance guarantee for an audit-focused platform.
- **Automatic + on-demand, no sweep** — rejected: same gap as automatic-only for
  post-acceptance contradictions; the sweep is the only trigger that catches those.
