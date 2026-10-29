# ADR-0042: Maintenance subagents and a generated wiki as repo-governance tooling

- **Status:** Proposed
- **Date:** 2026-10-29
- **Sources:** `.claude/agents/README.md`; `wiki/sources.yaml`; `AGENTS.md` §Skills & Workflows;
  `RELEASE.md`; commits `f1b77a3`, `db57174` (transitive dependency floor pins)

## Context

Repo upkeep is delegated to a catalog of subagents under `.claude/agents/` (quality, coverage,
acceptance, docs, vulnerability, refactor, spec-alignment, ADR audit, release, commit audit, wiki
maintenance), several of them run on weekly schedules. A project wiki under `wiki/` is generated from
the sources declared in `wiki/sources.yaml` by the `wiki-librarian` skill, and is not edited by hand.
None of this is recorded as a decision, although `AGENTS.md` and `RELEASE.md` depend on it.

Dependabot scores each package's `pyproject.toml` independently of the shared `platform/poetry.lock`,
so transitive dependencies already resolved to fixed versions kept raising alerts (`f1b77a3`,
`db57174`).

## Decision

> DRAFT — confirm: Upkeep is done by tracked, single-purpose subagents. Read-only ones report; write-capable
> ones push a branch and open a PR. They never merge, and `adr-auditor` leaves its PR as a draft.
>
> DRAFT — confirm: The wiki is derived output. `wiki/sources.yaml` is the only hand-edited input; everything
> else under `wiki/` is regenerated.
>
> DRAFT — confirm: Each platform package manifest pins explicit lower bounds for transitive dependencies that
> have security advisories, so the manifest agrees with the lock.

## Consequences

> DRAFT — confirm:

- Agent instructions become load-bearing governance files; changes to them are decisions to be recorded.
- Wiki content can go stale silently; the weekly wiki-maintenance audit is the control.
- Floor pins add manifest noise and must be refreshed when advisories change.
- Revisit if the agent catalog grows enough to need its own governance, or if Dependabot starts honouring
  the shared lock.

## Alternatives considered

None found in the sources. A human should add any that were weighed (for example hand-written docs instead
of a generated wiki, or dismissing the transitive Dependabot alerts instead of pinning).
