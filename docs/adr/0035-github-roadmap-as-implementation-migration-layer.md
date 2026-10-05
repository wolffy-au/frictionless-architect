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
  elements. Gaps come from the speckit scan below; the baseline Plateau, Strategy elements
  and the Triggering between Plateaus that orders them stay hand-authored.
- **Failure:** any incomplete or failed read (including more than 1000 issues) exits
  non-zero and writes nothing; `--check` reports drift without writing.
- **Cut-over:** `plat-runtime-mvp` and `plat-runtime-target` are retired in favour of the
  generated Plateaus; `gap-runtime-hosted` becomes
  `gap-policy-to-oscal-mvp-to-multi-user-collaboration`, and
  `gap-neo4j-schema-ui` carries the ADR-0024 solo-use narrative.

### Strategy and Implementation & Migration elements, by source

The table above covers what the importer emits. Every other type in the two layers, with
the ArchiMate 3.2 meaning that decides its source:

| ArchiMate type | Source | Why |
|---|---|---|
| Plateau | GitHub milestone (`plat-<slug>-<n>`) | A named state; generated (baseline is hand-authored) |
| Work Package | GitHub issue (`wp-<slug>-gh-<n>`) | A bounded unit of work; generated |
| Deliverable | GitHub release (`del-release-<tag-slug>`) | A defined result of work; generated |
| Gap | Speckit spec plus a mapping file | What is missing between Plateaus, not how it is built |
| Implementation Event | Not used currently | A go-live, cut-over or freeze date |
| Capability | Hand-authored | An architectural judgement |
| Course of Action | Hand-authored | An architectural judgement: a plan configuring capabilities and resources to reach a goal |
| Resource | Hand-authored | An asset owned or controlled by a person or organisation |
| Value Stream | Hand-authored | An architectural judgement |

Gap convention: a Gap is a feature, aligned with the speckit features under `specs/NNN-…`
(including those under `platform/packages/*/specs/`). Several Gaps may lie between the same
two Plateaus, one per feature. Each is Associated with its two Plateaus and with the Work
Packages and Deliverable that deliver it (Association is the only relationship ArchiMate
allows from a Gap).

- **Source:** a scan of the specs supplies the id (`gap-<spec-slug>`), the title (H1) and the
  status. The specs do not name their Plateaus, so a hand-authored mapping file lists, per
  spec directory, the "from" and "to" Plateau ids and any Work Packages or Deliverable to
  Associate. A spec with no entry yields no Gap.
- **Output:** a layer of its own, separate from `gh-roadmap/`, merged by `build.py` the same
  way. The GitHub importer still never creates Gaps.
- **Validation:** a mapping entry that names an unknown Plateau, Work Package or Deliverable
  fails the scan and writes nothing.

Course of Action is hand-authored. GitHub cannot tell an epic from a task, and an epic is
only a larger unit of work, not a plan, so epics stay Work Packages (a parent issue
Aggregates its children).

## Alternatives considered

- **Hand-maintain the layer:** drifts again; rejected.
- **GitHub Projects as the source:** needs extra scopes and a second model of the roadmap.
- **Link Work Packages straight to Plateaus:** loses which release delivered the work and
  duplicates what the Deliverable chain already implies.

## Consequences

- The model changes whenever the roadmap does and must be re-imported on demand; there is
  no scheduled run.
- A milestone rename changes its Plateau id (the id is a function of title and number).
