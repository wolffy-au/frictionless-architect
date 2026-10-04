# Feature Specification: GitHub Roadmap as ArchiMate Implementation & Migration

**Feature Branch**: `feature/gh-95-roadmap-archimate` | **Created**: 2026-10-03 | **Status**: Draft

**Input**: Map GitHub milestones, releases and issues into the architecture model as
Implementation & Migration elements, milestone-first and user-facing, not a dump of every issue.

## Clarifications

### Session 2026-10-04

- Second milestone is titled `multi-user-collaboration` (Plateau `plat-multi-user-collaboration-2`).
- Only closed Work Packages realize a release Deliverable; open ones realize a planned Deliverable. No Work Package realizes a Plateau directly.
- A closed Work Package realizes the first release, among those naming its Plateau, published after it closed; otherwise the planned Deliverable.
- Pre-releases are skipped, like drafts.

## Mapping

| GitHub | Becomes | Relationships |
|---|---|---|
| Milestone | Plateau | Realizes a business function it names (`bfn-*`) |
| Issue with its own milestone, open or closed | Work Package | Realizes one Deliverable (below); aggregates sub-issues; triggers the issues it blocks |
| Published release (not draft or pre-release) | Deliverable | Realizes the Plateau it names |
| Milestone with at least one Work Package | Planned Deliverable | Realizes the milestone's Plateau |
| Issue dependency across milestones | none | One Plateau → Plateau Triggering |

Gaps, the baseline Plateau and Strategy elements stay hand-authored, so the importer
never touches them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the roadmap as Plateaus, Work Packages and Deliverables (P1)

As an architect, I want milestones, milestone-assigned issues and releases in the model,
so the roadmap appears on Implementation & Migration views without hand-editing.

**Independent Test**: Run the import on this repo (2 milestones, 0 releases, 3 issues in the first):
get 2 Plateaus, 1 planned Deliverable (the second milestone has no Work Packages) and 3 Work
Packages, linked as in the table.

1. **Given** an open or closed milestone issue, **When** imported, **Then** it is a Work
   Package with its state recorded, realizing a Deliverable and never a Plateau directly.
2. **Given** an issue with no milestone of its own, **When** imported, **Then** nothing is
   created for it, even if its parent or sub-issues have one.
3. **Given** two releases name one Plateau and an issue closed between them, **When**
   imported, **Then** it realizes the later release only.
4. **Given** an issue closed after the latest release, **When** imported, **Then** it stays
   on the planned Deliverable until a later release is published.

### User Story 2 - See dependencies and hierarchy (P2)

As an architect, I want "blocked by" and parent/child links shown, so the order of work is visible.

**Independent Test**: B blocked by A gives A triggers B; a cross-milestone block gives one
Plateau → Plateau Triggering.

1. **Given** both ends imported, **When** imported, **Then** the link appears; links with an
   unimported end do not.

### User Story 3 - Refresh safely (P1)

As an architect, I want one on-demand run that never half-updates and changes nothing when
GitHub has not, so I can review the output in version control.

**Independent Test**: Run twice with no GitHub change: no diff. Run with GitHub unreachable:
no diff and a clear error.

1. **Given** one issue is closed, **When** re-run, **Then** only that issue's state and
   Deliverable link change.
2. **Given** a check-only run on a stale layer, **When** run, **Then** it reports stale and writes nothing.

### User Story 4 - Coexist with the hand-authored model (P2)

As an architect, I want each element to have one owner, so nothing is duplicated.

**Independent Test**: After first import the first-MVP milestone appears once, and no link
refers to the retired `plat-runtime-mvp`.

1. **Given** the hand-authored `plat-runtime-mvp`, **When** the importer is adopted, **Then** the
   generated Plateau replaces it and its links and view members are retargeted.
2. **Given** an imported Plateau is renamed or deleted on GitHub, **When** the model is built,
   **Then** the build fails naming each dangling hand-authored reference.

### Edge Cases

- Issue reassigned or its milestone removed: its link moves, or its element is removed.
- Reopened issue: state returns, and it moves back to the planned Deliverable if no release covers it.
- Retitled issue or milestone: its id changes, so hand-authored references fail the build until updated.
- Dependency cycles: imported as written.
- Hostile characters in titles or descriptions: escaped; the file still parses.
- A relationship the ArchiMate rules forbid is never emitted.

## Requirements *(mandatory)*

- **FR-001**: Import every milestone as a Plateau, every in-scope issue as a Work Package, and every published release as a Deliverable, per the Mapping table.
- **FR-002**: An issue is in scope only if it carries its own milestone; scope is never inferred from a parent, descendant or label.
- **FR-003**: A Work Package MUST realize exactly one Deliverable and MUST NOT realize a Plateau directly. Open ones realize the planned Deliverable; closed ones realize the first qualifying release (see Clarifications), else the planned one.
- **FR-004**: Never emit a relationship that an existing chain already implies, or one ArchiMate forbids between its end types. The model MUST still validate after the merge.
- **FR-005**: Ids are prefixed by element type, never by source system, and are a pure function of the object's number and title (or tag). Source number and URL are properties.
- **FR-006**: A `bfn-*` or `plat-*` id in a description or release notes is honoured only if it exactly matches an existing element of the right type. All other GitHub text is untrusted and ignored for relationships.
- **FR-007**: Output MUST be deterministic: unchanged GitHub state gives byte-identical files, and a change touches only the affected elements.
- **FR-008**: The imported layer lives apart from the hand-authored model, is merged by the existing build, and is never hand-edited. The importer never creates, changes or deletes a Gap, the baseline Plateau or a Strategy element.
- **FR-009**: Provide an on-demand run and a check-only mode. If complete GitHub data cannot be retrieved (unavailable, unauthenticated, rate-limited, unparseable, or more issues than the cap in `research.md` R8), fail with an actionable message and write nothing.
- **FR-010**: Generated diagrams MUST reflect the roadmap: a view per milestone and the overall Implementation & Migration overview.
- **FR-011**: In the same change, retire `plat-runtime-mvp` and `plat-runtime-target`, replaced by the generated Plateaus; rename the hand-authored runtime Gap for `multi-user-collaboration`; and add a Gap from `plat-baseline` to the first MVP.
- **FR-012**: Record the mapping, id scheme, scope rule and ownership split in an ADR, and update `ARCHITECTURE.md` and the model's documentation in the same change. If that is impossible, open a tracking issue and mark the ADR accepted-but-not-yet-reflected.

## Success Criteria *(mandatory)*

- **SC-001**: Every milestone, published release and milestone issue is represented exactly once, plus one planned Deliverable per milestone with Work Packages, and nothing else.
- **SC-002**: Two consecutive runs with no GitHub change produce zero differences.
- **SC-003**: One GitHub change alters only the elements tied to it.
- **SC-004**: A stakeholder can view a milestone's plan, delivered work and releases as a diagram without hand-editing the layer.
- **SC-005**: When GitHub is unreachable or incomplete, every run fails with a message naming the cause and leaves all files unchanged.
- **SC-006**: After first import the first-MVP milestone appears once and no link refers to the retired plateau.

## Assumptions

- Milestones are deliberate, user-facing increments; which issues are imported is controlled only by which carry a milestone.
- GitHub cannot tell an epic from a task, so every milestone issue is a Work Package.
- Releases are tied to a Plateau only by naming its model id in the notes; GitHub has no release-to-milestone link.
- Gaps relate to Plateaus by Association only, the one relationship ArchiMate permits there.
- Dependencies are GitHub "blocked by" links.
- The model reflects current GitHub state; removed items are removed, not kept as history.
- Uses the existing authenticated `gh` access; no new credential, no schedule.
- The `multi-user-collaboration` milestone exists (GitHub #2) with no issues, so it yields a Plateau and no Work Packages or planned Deliverable yet.
- Performance and scale targets are deferred.
