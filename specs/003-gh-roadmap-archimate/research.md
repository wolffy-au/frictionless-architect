# Research: GitHub Roadmap as ArchiMate Implementation & Migration

All Technical Context unknowns are resolved below. Facts about this repository were
checked on 2026-10-03/04. Superseded designs (Gap-by-hierarchy, `gh-*` ids, milestone
inheritance, Work Package → Plateau) are in git history at `f593ea8` and earlier.

## R1. Element mapping: Plateau, Deliverable, Work Package only

- **Decision**: Milestone → `Plateau`; published release → `Deliverable`; milestone with
  at least one Work Package → one planned `Deliverable`; issue with its own milestone →
  `WorkPackage` (open or closed as a `gh-state` prop). Gaps, `plat-baseline` and Strategy
  elements stay hand-authored. (Maintainer direction, 2026-10-04.)
- **Rationale**: A Gap is a difference between two Plateaus, an architectural judgement
  that GitHub cannot express. Work Packages and Deliverables are what GitHub actually
  records. Every issue is a Work Package because GitHub cannot tell an epic from a task.
- **Alternatives**: Gap-by-issue-hierarchy (the earlier design) mislabelled GitHub objects
  and made the importer own architectural judgements.

## R2. Relationship types (probed against `validate.py`)

| From → To | Legal types | Chosen |
|---|---|---|
| WorkPackage → Deliverable | Realization, Association, … | **Realization** |
| Deliverable → Plateau | Realization, Association | **Realization** |
| WorkPackage → Plateau | Realization, Association, Triggering | **never emitted** (FR-003) |
| WorkPackage → WorkPackage | Association, Aggregation, Composition, Triggering, Flow, Specialization | **Aggregation** (parent → child), **Triggering** (blocker → blocked) |
| Plateau → Plateau | Association, Aggregation, Composition, Triggering, Flow, Specialization | **Triggering** (derived) |
| Plateau → BusinessFunction | Realization, Association, Aggregation | **Realization** |
| Gap → Plateau | Association only | hand-authored, not emitted |

Realization WP → Plateau is legal, but it is dropped by design: a Work Package reaches its
Plateau through a Deliverable, so no direct edge would be redundant under the derivation rule
and would hide which release delivered the work.

## R3. How the layer is merged by `build.py`

- **Decision**: Replace the single-purpose `VENDORED_MODELS` list with a general
  `MODEL_LAYERS = [*VENDORED_MODELS, HERE / "gh-roadmap"]` that `load_vendored`
  iterates. It already skips a missing dir silently, so a checkout that has never
  run the importer still builds.
- **Rationale**: Same `det_id()`/`NS` pass, so no reconciliation step (ADR-0029).
- **Id collisions**: Ids are type-prefixed, so they share a namespace with hand-authored
  `plat-*`, `del-*` and `wp-*`. Generated ids are distinguishable by shape
  (`plat-…-<n>`, `del-release-…`, `del-…-planned`, `wp-…-gh-<n>`) and none matches today's
  hand-authored ids. `add_elements` already errors on a duplicate, which is the backstop.

## R4. Stable ids

- **Decision**: `plat-<title-slug>-<n>`, `del-release-<tag-slug>`,
  `del-<title-slug>-<n>-planned`, `wp-<title-slug>-gh-<n>`. Slugs are lower-case,
  hyphenated, cut at a word boundary to at most 40 characters. `gh-*` is only a prop key.
- **Rationale**: Type prefixes make ids self-describing and keep the source system out of
  the model. The number guarantees uniqueness so truncation never collides. Retitling
  changes the id by design, so hand-authored references fail loudly instead of silently
  pointing at the wrong thing.

## R5. Scope

- **Decision**: An issue is in scope only if it carries its own milestone; no inheritance
  from a parent or descendant. Drafts and pre-releases are skipped.
- **Rationale**: The author controls granularity by choosing which issues get a milestone,
  and scope becomes a field test rather than a graph walk. #47–#49 and #76 are under #44
  but carry no milestone, so they stay out.

## R6. Which Deliverable a Work Package realizes

- **Decision**: Open → the planned Deliverable. Closed → the first release, among those
  naming its Plateau (exact `plat-*` token), with `published_at` after the issue's
  `closedAt` (ties by `tag_name`); none → the planned Deliverable.
- **Rationale**: GitHub has no issue-to-release link, so close time against publish time
  is the only available signal. It answers "which work packages were part of a release"
  without a new convention. Reopening naturally moves a Work Package back.
- **Alternatives**: Last release before closure (rejected: it attributes work to a release
  that was already published); a manual label (rejected: extra convention to maintain).

## R7. Dependencies

- **Decision**: Read GitHub's native `blockedBy`. For in-scope Work Packages A (blocker)
  and B: `Triggering A → B`. When A and B belong to different milestones N and M: one
  `Triggering N → M`, de-duplicated, never self-loops. Parent/child, both imported:
  `Aggregation` parent → child.
- **Rationale**: Dependencies on out-of-scope issues are dropped. Cycles are emitted as
  written; the importer does not judge them.
- **Real data**: #44 and #7 have blockers without a milestone, so no Triggering appears
  today.

## R8. Fetching GitHub state

- **Decision**: `gh api --paginate` REST for milestones (`state=all`) and releases;
  **one** paginated `gh api graphql` query for issues (`number, title, state, closedAt,
  url, milestone{number}, parent{number}, blockedBy{nodes{number}}`). Drafts and
  pre-releases are filtered after the fetch. Results are used only after every call
  succeeds; any non-zero exit aborts the run.
- **Rationale**: One GraphQL query avoids N+1 calls. `gh` supplies auth, so no new
  credential is in scope. Connections are capped per page (`first: 100`); the importer
  fails if `hasNextPage` is true rather than silently truncating (FR-009).
- **Alternatives**: `gh issue list --json` (no `parent` or dependency data).

## R9. Determinism and atomic output (FR-007, FR-009)

- **Decision**: Sort every list by `(kind, number)` (releases by `published_at`, tag);
  `yaml.safe_dump(..., sort_keys=False, width=<fixed>, allow_unicode=True)`; no timestamps;
  fixed header comment. Write `*.tmp` and `os.replace` after all three files render. A
  failed fetch leaves the committed layer untouched.

## R10. Untrusted text (FR-006)

- **Decision**: Titles and descriptions enter the file only as Python strings through
  `safe_dump`. A `bfn-*` token in a milestone description or `plat-*` token in release
  notes is honoured only on exact match to an existing element of the right type;
  otherwise ignored. A test round-trips titles with a colon-space, `#`, quotes, leading
  `-`/`*` and newlines. `build.py`'s `_check_null_keys` stays as a backstop.

## R11. BusinessFunction link

- **Decision**: Opt-in and deterministic, via the `bfn-*` token (R10). No fuzzy matching:
  it could invent a wrong relationship (Principle VII). No milestone carries the token
  yet, so no link appears until one is authored.

## R12. Views and diagrams (FR-010)

- **Decision**: The generated `gh-roadmap/views.yaml` holds one view per milestone
  (`implementation_migration` viewpoint) listing its Plateau, Deliverables and Work
  Packages. `view-implementation-migration-overview` uses `include_types` and picks the
  imported elements up. Diagrams are regenerated with `render_diagrams.py`.
- **Check in tasks**: `add_views` errors on a missing member id; members come from the
  same element set. Confirm the viewpoint admits Realization WP → Deliverable and
  Deliverable → Plateau.

## R13. Replacing hand-authored elements (FR-011)

- **Decision**: In the same change as the first import, delete `plat-runtime-mvp` and
  retarget its 8 relationship lines and 3 view members to `plat-policy-to-oscal-mvp-1`;
  rename `plat-runtime-target` and `gap-runtime-hosted` for `multi-user-collaboration`
  (`plat-multi-user-collaboration-2`). The milestone does not yet exist on GitHub;
  creating it needs maintainer approval, so the rename waits on it.

## R14. Test strategy

- Inject a `run_gh(args) -> str` callable so unit tests feed recorded JSON and never touch
  the network.
- Cases: the mapping; scope (own milestone only); Deliverable attachment (open, closed
  before/between/after releases, two releases, reopen, tie on `published_at`); drafts and
  pre-releases skipped; planned Deliverable only with ≥1 Work Package; reassign, unassign,
  deleted milestone; dependencies (in-scope, out-of-scope, cross-milestone, cycle); untrusted
  tokens; hostile titles; `gh` failure → exit 2 and no files written; double run
  byte-identical.
- Integration: build a fixture layer through `build.py` and assert `validate.py` exits 0.
