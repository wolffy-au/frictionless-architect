# Implementation Plan: GitHub Roadmap as ArchiMate Implementation & Migration

**Branch**: `feature/gh-95-roadmap-archimate` (issue #95) | **Date**: 2026-10-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-gh-roadmap-archimate/spec.md`

## Summary

A live-refreshable importer, `architecture/model/import_gh_roadmap.py`, pulls
milestones, releases and issues (with their parent and blocked-by links) through the
`gh` CLI and writes a first-party YAML layer under `architecture/model/gh-roadmap/`
(`elements.yaml`, `relationships.yaml`, `views.yaml`). `build.py` merges that layer
through the same `det_id()`/`NS` pass it already uses for `third_party/it4it`
(ADR-0029), so no second build step or id-reconciliation exists. The importer emits only
Implementation & Migration elements: milestone → `Plateau` (`plat-<title-slug>-<n>`),
published non-draft non-pre-release release → `Deliverable` (`del-release-<tag-slug>`,
realizing the Plateau named by an exact `plat-*` token in its notes), a milestone with at
least one Work Package → one planned `Deliverable` (`del-<title-slug>-<n>-planned`), and
every issue carrying its own milestone → `WorkPackage` (`wp-<title-slug>-gh-<n>`, open or
closed as a prop). A Work Package realizes exactly one Deliverable and never a Plateau
directly: open → planned; closed → the first release published after its `closedAt`, else
planned. `blockedBy` becomes `Triggering` between Work Packages and, derived, between
Plateaus; parent/child becomes `Aggregation`. Gaps, the baseline Plateau and Strategy
elements stay hand-authored. Element ids are type-prefixed, never `gh-*`. The hand-authored
`plat-runtime-mvp` is replaced by the generated `plat-policy-to-oscal-mvp-1`, and
`plat-runtime-target`/`gap-runtime-hosted` are renamed for the `multi-user-collaboration`
milestone. Output is deterministic and written atomically only after every fetch succeeded.
The mapping is filed as ADR-0035 (Principle X).

## Technical Context

**Language/Version**: Python 3.12 (floor `>=3.11,<3.14`), same as `build.py`

**Primary Dependencies**: stdlib (`subprocess`, `json`, `pathlib`, `argparse`) + `pyyaml` (already imported by `build.py`); `gh` CLI (authenticated) as the only GitHub client — no new dependency

**Storage**: Files — generated YAML in `architecture/model/gh-roadmap/`, committed like `frictionless-architect.xml`

**Testing**: `pytest` — unit tests with a stubbed `gh` runner (recorded JSON fixtures); one integration test that runs `build.py` over a fixture layer and asserts the validator passes; behave scenario for the idempotency and single-change stories (SC-002/003)

**Target Platform**: Developer machine / devcontainer (Linux, WSL2), on demand

**Project Type**: Single script + generated data layer inside the architecture-model toolchain (not an application package)

**Performance Goals**: One import under ~30 s for this repo (≈50 issues); not on any hot path (Principle IV N/A)

**Constraints**: Idempotent byte-identical output (FR-007); fail clearly and write nothing on any `gh` failure (FR-009); every emitted relationship legal in the ArchiMate 3.2 matrix (FR-004); YAML built by `yaml.safe_dump`, never string-templated (FR-006, hostile titles)

**Scale/Scope**: 1 milestone, 0 releases, 3 in-scope issues today (#44, #61, #7); a second milestone, `multi-user-collaboration`, is not yet created; hundreds supported; design holds to hundreds of issues

## Constitution Check

*GATE: passed before Phase 0; re-checked after Phase 1 — still passes.*

| Principle | Assessment |
|---|---|
| I. Code Quality | Small pure functions (fetch → map → render → write); mapping is a pure function over plain dicts, trivially testable. Pass. |
| II. Testing | TDD order in tasks: stub-`gh` unit tests first, then idempotency/single-change tests, then `build.py` integration. 90% gate applies to the new module if `architecture/model/` is in coverage scope — tasks must confirm and, if excluded, still test it. Pass. |
| III. UX Consistency | CLI mirrors `build.py` (`poetry run python architecture/model/import_gh_roadmap.py`); errors name the failing `gh` call and the fix (`gh auth login`). Pass. |
| IV. Performance | Off hot path; no 200 ms obligation. Pass. |
| V. Security | Uses the operator's existing `gh` auth; no tokens read, stored or logged; issue/milestone text is untrusted input and is only ever passed through `safe_dump`. `gh` invoked with an argv list, never `shell=True`. Pass. |
| VI. State Mgmt | Issue lifecycle (open ⇄ closed, release published after close, milestone moved/removed) is a documented state table in `data-model.md`. Pass. |
| VII. Integrity | Whole model re-validated by `validate.py` after merge; importer output is a pure function of GitHub state. Pass. |
| VIII. Durability | Output schema is the existing YAML schema (ADR-0007/0008); stable ids never renumbered. Pass. |
| IX. Cross-Platform | Pure Python + `gh`; no OS-specific paths. Pass. |
| X. Decision Traceability | ADR-0035 (mapping + milestone-assigned scope + type-prefixed id scheme + importer/hand-authored ownership split + layer merge) filed in the same PR; `architecture/model/README.md` and `ARCHITECTURE.md` §8 updated to match. Pass (tracked in tasks). |

No violations; Complexity Tracking is empty.

### Model impact

- Adds the generated layer `architecture/model/gh-roadmap/` (`plat-*`, `del-*`, `wp-*`, their relationships and one view per milestone).
- Retires `plat-runtime-mvp` (8 relationship lines, 3 view members retargeted to `plat-policy-to-oscal-mvp-1`).
- Renames `plat-runtime-target` and `gap-runtime-hosted` for `multi-user-collaboration`, once that milestone exists.
- Changes `build.py` (`MODEL_LAYERS`) and `architecture/model/README.md`; regenerate diagrams after `validate.py`.

## Project Structure

### Documentation (this feature)

```text
specs/003-gh-roadmap-archimate/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── importer-cli.md      # command, exit codes, failure behaviour
│   └── gh-roadmap-layer.md  # shape of the generated YAML layer
├── checklists/requirements.md
└── tasks.md             # Phase 2 — /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
architecture/model/
├── import_gh_roadmap.py      # NEW: gh → mapping → YAML layer
├── build.py                  # CHANGED: load gh-roadmap/ as a merged layer (see research R3)
├── gh-roadmap/               # NEW, generated + committed, never hand-edited
│   ├── elements.yaml
│   ├── relationships.yaml
│   └── views.yaml
└── README.md                 # CHANGED: document the layer + importer

docs/adr/0035-github-roadmap-as-implementation-migration-layer.md   # NEW
docs/adr/README.md                                                  # CHANGED: index row

tests/unit/architecture/test_import_gh_roadmap.py     # NEW
tests/unit/architecture/test_build_layers.py          # NEW
tests/unit/architecture/fixtures/gh_*.json            # NEW: recorded gh payloads
tests/features/gh_roadmap_import.feature (+ steps)    # NEW: SC-002/SC-003
```

**Structure Decision**: Single script beside `build.py`, as the issue and ADR-0007
direct; it is model tooling, not an extracted platform package, so `platform/` is
not used. Tests mirror the existing `tests/unit/<area>/` layout.

## Design views

Where the importer runs:

```plantuml
@startuml
title Where the importer runs
node "Developer machine / devcontainer" {
  component "gh CLI\n(operator's own auth)" as gh
  component "import_gh_roadmap.py" as imp
  component "build.py + validate.py" as build
  folder "architecture/model/" {
    file "elements.yaml\nrelationships.yaml\nviews.yaml\n(hand-authored)" as hand
    folder "gh-roadmap/" {
      file "elements.yaml\nrelationships.yaml\nviews.yaml\n(generated, committed)" as gen
    }
    file "frictionless-architect.xml" as xml
  }
}
cloud "GitHub" as github

imp --> gh : argv list, no shell
gh --> github : HTTPS
imp --> gen : atomic write
build --> hand : read
build --> gen : read
build --> xml : write
@enduml
```

What one run does, and when it writes nothing:

```plantuml
@startuml
title One importer run
start
:Parse options (--repo, --check);
:Fetch milestones, releases and issues\nthrough gh (paginated GraphQL);
if (gh failed, unauthenticated,\nrate-limited or output unparseable?) then (yes)
  :Print failing call and fix to stderr;
  stop
endif
if (a page reports hasNextPage\nbeyond the cap?) then (yes)
  :Fail rather than import a partial set;
  stop
endif
:Keep only issues with their own milestone;
:Drop draft and pre-release releases;
:Map milestones to Plateaus, releases to Deliverables,\nissues to Work Packages;
:Attach each Work Package to one Deliverable\n(planned, or first release after closedAt);
:Derive links: Realization, Aggregation, Triggering,\nPlateau to business function;
:Drop links implied by a chain (derivation rule);
:Sort by (kind, number) and render YAML\nwith yaml.safe_dump, in memory;
if (--check?) then (yes)
  if (rendered bytes equal files on disk?) then (yes)
    :Exit 0, layer is current;
  else (no)
    :Exit 1, layer is stale;
  endif
  stop
endif
if (rendered bytes equal files on disk?) then (yes)
  :Print "unchanged";
else (no)
  :Write temp files beside the layer;
  :Replace atomically (os.replace);
  :Print summary line;
endif
stop
@enduml
```

## Complexity Tracking

No constitution violations to justify.
