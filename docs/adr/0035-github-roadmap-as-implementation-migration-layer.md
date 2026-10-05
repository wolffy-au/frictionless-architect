# ADR-0035: GitHub roadmap as the Implementation & Migration layer

- **Status:** Accepted
- **Date:** 2026-10-05
- **Sources:** GH #95; `specs/003-gh-roadmap-archimate/` (spec, data-model, research);
  [ADR-0029](0029-it4it-as-vendored-touchpoint-model.md) (layer merge through `det_id`/`NS`);
  [ADR-0018](0018-postgres-plus-neo4j-data-layer.md) and [ADR-0024](0024-single-user-local-mvp.md)
  (the runtime Plateaus this replaces); ArchiMate 3.2 §3.5 (derivation)

## Context

The Implementation & Migration layer was hand-authored, so it drifted from the roadmap
kept in GitHub milestones, issues and releases. The roadmap needed one source of truth
with the model following it, without hand-editing the generated layer.

## Decision

`architecture/model/import_gh_roadmap.py` reads GitHub through the `gh` CLI and writes
`architecture/model/gh-roadmap/{elements,relationships,views}.yaml`. `build.py` merges that
directory as a model layer (`MODEL_LAYERS`) through the same `det_id`/`NS` pass as vendored
models. The files are committed, deterministic and never hand-edited.

| GitHub | ArchiMate | Id |
|---|---|---|
| Milestone | Plateau | `plat-<slug>-<n>` |
| Issue with its own milestone | Work Package | `wp-<slug>-gh-<n>` |
| Published release (not draft or pre-release) | Deliverable | `del-release-<tag-slug>` |
| Milestone with Work Packages | Unreleased Deliverable | `del-<slug>-<n>-unreleased` |

- **Scope:** an issue is in scope only if it carries its own milestone; scope is never
  inferred from a parent, child or label.
- **Realization:** a Work Package realizes exactly one Deliverable, never a Plateau. A
  closed one realizes the first release published after `closedAt`, else the unreleased one.
- **Dependencies:** `blockedBy` becomes Triggering between Work Packages, lifted to a
  de-duplicated Plateau Triggering across milestones; a parent and child both in scope
  are joined by Aggregation. Links to unimported issues are dropped.
- **Derivation:** a link already implied by two shorter importer-emitted links is not
  emitted (ArchiMate 3.2 §3.5 subset), so `check_derived.py` stays clean.
- **Untrusted text:** only an exact `plat-*` or `bfn-*` id match in a description or
  release body creates a link; everything else from GitHub is ignored.
- **Ownership:** the importer never creates Gaps, the baseline Plateau or Strategy
  elements. Those, and the Triggering between Plateaus that orders them, stay
  hand-authored.
- **Failure:** any incomplete or failed read (including more than 1000 issues) exits
  non-zero and writes nothing; `--check` reports drift without writing.
- **Cut-over:** `plat-runtime-mvp` and `plat-runtime-target` are retired in favour of the
  generated Plateaus; `gap-runtime-hosted` becomes
  `gap-policy-to-oscal-mvp-to-multi-user-collaboration`, and
  `gap-baseline-to-policy-to-oscal-mvp` carries the ADR-0024 solo-use narrative.

## Alternatives considered

- **Hand-maintain the layer:** drifts again; rejected.
- **GitHub Projects as the source:** needs extra scopes and a second model of the roadmap.
- **Link Work Packages straight to Plateaus:** loses which release delivered the work and
  duplicates what the Deliverable chain already implies.

## Consequences

- The model changes whenever the roadmap does and must be re-imported on demand; there is
  no scheduled run.
- A milestone rename changes its Plateau id (the id is a function of title and number).
