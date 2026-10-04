# Research: GitHub Roadmap as ArchiMate Implementation & Migration

All Technical Context unknowns are resolved below. Facts about this repository were
checked on 2026-10-03.

## R1. Gap vs WorkPackage: by issue hierarchy, not state

- **Decision**: An in-scope issue **with sub-issues** is a `Gap` (feature or
  epic); an in-scope issue **without** is a `WorkPackage` (story or task). Open
  or closed is a `gh-state` prop on both. (Maintainer direction, 2026-10-03.)
- **Rationale**: A Gap is the difference between two states and a Work Package is
  a bounded unit of planned or done work, so the hierarchy maps better than
  open/closed. State never changes an element's type or relationships, so closing
  an issue changes one prop and nothing else (FR-007/008). An issue changes kind
  only when it gains its first or loses its last sub-issue.
- **Alternatives**: Open → Gap / closed → WorkPackage (the original spec). An
  open story is planned work, not a state difference, so it mislabelled planned
  work.

## R2. Relationship types (probed against `validate.py`, 2026-10-03)

| From → To | Legal types | Chosen |
|---|---|---|
| WorkPackage → Plateau | Realization, Association, Triggering | **Realization** |
| Gap → Plateau | Association only | **Association** |
| Gap → Gap (child feature) | Association, Aggregation, Composition, Specialization | **Aggregation** parent → child |
| Gap ↔ WorkPackage | Association only | **Association** parent → child |
| WorkPackage → WorkPackage | Association, Aggregation, Composition, Triggering, Flow, Specialization | **Triggering** (blocker → blocked) |
| Plateau → Plateau | Association, Aggregation, Composition, Triggering, Flow, Specialization | **Triggering** (derived) |
| Plateau → BusinessFunction | Realization, Association, Aggregation | **Realization** (FR-015) |
| Gap → Gap, Gap ↔ WorkPackage | Triggering is **not** legal | not emitted |

The Gap → Plateau choice follows the existing `gap-runtime-hosted`, which uses
`Association` to its Plateaus.

## R3. How the layer is merged by `build.py`

- **Decision**: Replace the single-purpose `VENDORED_MODELS` list with a general
  `MODEL_LAYERS = [*VENDORED_MODELS, HERE / "gh-roadmap"]` that `load_vendored`
  iterates. It already skips a missing dir silently, so a checkout that has never
  run the importer still builds.
- **Rationale**: Same `det_id()`/`NS` pass, so no reconciliation step (ADR-0029).
  The only change is one list and its name. The layer is first-party generated
  content, not a vendored submodule.
- **Id collisions**: Every imported id carries the `gh-` prefix. Existing
  first-party ids use `plat-`, `gap-`, `wp-` and `deliv-`, and none starts `gh-`.
  `add_elements` already errors on duplicates.

## R4. Stable ids

- **Decision**: `gh-milestone-<number>`, `gh-release-<tag-slug>`,
  `gh-issue-<number>`.
- **Rationale**: Issue and milestone numbers are GitHub's own, and the id carries
  no state or kind. `gh-issue-44` stays the same id if it later becomes a Work
  Package. Releases have no per-repo number that survives delete-and-recreate, so
  the tag is the stable key (slugged to kebab).

## R5. Scope and milestone inheritance

- **Decision**: An issue is in scope when it, an ancestor or a descendant has a
  milestone. Its own milestone wins over an inherited one. A Gap is also
  `Association`-linked to the Plateau of each descendant's milestone (US2 S4).
- **Rationale**: This repo already needs it. #44 is in milestone 1 and has four
  sub-issues (#47, #48, #49, #76) with no milestone of their own. Under "own
  milestone only" the stories under a roadmap feature would vanish and the
  hierarchy would be lost. The spec's FR-004 was reworded to match.
- **Cost**: Scope is a graph walk, not a field test; it is covered by unit tests.

## R6. Dependencies (FR-005)

- **Decision**: Read GitHub's native `blockedBy`. For in-scope Work Packages A
  (blocker) and B: `Triggering A → B`. When A and B realize different Plateaus
  N and M: one `Triggering N → M`, de-duplicated, never self-loops.
- **Rationale**: `Triggering` is only legal between WorkPackages and between
  Plateaus (R2), so Gap-level and mixed dependencies are dropped; the
  parent/child `Association` already ties a Gap to its stories. Dependencies on
  out-of-scope issues are dropped. Cycles are emitted as written; the importer
  does not judge them.
- **Real data**: #44 is blocked by its own children and by #43/#45. The children
  links drop (Gap involved) as do #43/#45 (out of scope). #48 blocks #47 and #49,
  and both are in scope, so two Triggering edges appear.

## R7. Courses of Action dropped

- **Decision**: No `CourseOfAction` elements. Epics are Gaps (R1).
- **Rationale**: Maintainer direction. Keeping both would model the same GitHub
  object twice. The spec's original Story 4 / FR-005 were replaced by the
  dependency story.

## R8. Fetching GitHub state

- **Decision**: `gh api --paginate` REST for milestones (`state=all`) and releases
  (non-draft only); **one** paginated `gh api graphql` query for issues (`number,
  title, state, url, labels, milestone{number}, parent{number},
  subIssues{nodes{number}}, blockedBy{nodes{number}}`). Results are used only after
  every call succeeds; any non-zero exit aborts the run. All the fields were
  confirmed to exist on this repo.
- **Rationale**: One GraphQL query avoids N+1 calls. `gh` supplies auth, so no new
  credential is in scope. Nested connections are capped per page (`first: 100`); the
  importer fails if `hasNextPage` is true on one rather than silently truncating.
- **Alternatives**: `gh issue list --json` (no hierarchy or dependency data).

## R9. Determinism and atomic output (FR-006, FR-014)

- **Decision**: Sort every list by `(kind, number)`; `yaml.safe_dump(...,
  sort_keys=False, width=<fixed>, allow_unicode=True)`; no timestamps or run
  metadata in the output; fixed header comment; props only from GitHub data
  (`gh-number`, `gh-url`, `gh-state`, `gh-labels` sorted, `gh-due`). Write to
  `*.tmp` and `os.replace` into place **after** all three files render. A failed
  fetch leaves the committed layer untouched.
- **Rationale**: Gives byte-identical re-runs, and a delete is a removal because
  the layer is regenerated whole each run.

## R10. Hostile text (edge case)

- **Decision**: Titles and descriptions only enter the file as Python strings
  through `safe_dump`, which quotes them correctly. A test round-trips titles with
  a colon-space, `#`, quotes, leading `-`/`*`, and newlines. `build.py`'s
  `_check_null_keys` stays as a backstop.

## R11. BusinessFunction link (FR-015)

- **Decision**: Opt-in and deterministic. A milestone whose description contains a
  token matching an existing `bfn-*` element id gets `Realization` from its Plateau
  to that BusinessFunction (the spec says the Plateau realizes it). Anything else
  gets no link and still imports.
- **Rationale**: Fuzzy-matching `policy-to-oscal-mvp` against "Policy-to-OSCAL
  Conversion" is brittle and could invent a wrong relationship (Principle VII). The
  importer reads the first-party `elements.yaml` for the id set. No milestone
  carries the token yet, so no link appears until one is authored.

## R12. Views and diagrams (FR-012)

- **Decision**: The generated `gh-roadmap/views.yaml` holds one view per milestone
  (`implementation_migration` viewpoint) listing that milestone's Plateau, Gaps and
  WorkPackages. `view-implementation-migration-overview` already uses
  `include_types` and picks the imported elements up automatically. Diagrams are
  regenerated with `render_diagrams.py` after a build.
- **Check in tasks**: `add_views` errors on a missing member id; the importer builds
  members from the same element set, so they stay in step. Confirm the viewpoint
  admits Triggering between Work Packages and Plateaus.

## R13. Test strategy

- Inject a `run_gh(args) -> str` callable so unit tests feed recorded JSON and
  never touch the network.
- Cases: the mapping, scope and milestone inheritance, kind change on sub-issue
  add/remove, close/reopen as a prop-only diff, reassign, unassign, deleted
  milestone, release with no milestone, dependencies (in-scope, out-of-scope,
  Gap-involved, cross-milestone, cycle), hostile titles, `gh` failure → non-zero
  exit and no files written, double run byte-identical.
- Integration: build a fixture layer through `build.py` and assert `validate.py`
  exits 0.
