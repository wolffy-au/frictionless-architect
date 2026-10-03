# Feature Specification: GitHub Roadmap as ArchiMate Implementation & Migration

**Feature Branch**: `feature/gh-roadmap-archimate`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Map GitHub issues and milestones into the canonical ArchiMate model under architecture/model/, representing them as Implementation & Migration layer elements — but milestone-first and user-facing, not a raw dump of every GitHub issue."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See milestones and releases as Plateaus (Priority: P1)

As a platform architect, I want every GitHub milestone and every published
release in this repository represented as a Plateau in the architecture
model, so that the project's deliberately-scoped past, current, and planned
states appear on the model's Implementation & Migration views alongside the
rest of the architecture.

**Why this priority**: Plateaus are the backbone the rest of this mapping
hangs off (Gaps and Work Packages are both defined relative to a milestone's
Plateau). Without this, nothing else in the mapping has anywhere to attach.

**Independent Test**: Run the import against this repository (which has one
milestone, `policy-to-oscal-mvp`, and zero releases) and confirm the
milestone appears as exactly one Plateau element, with no manual YAML
editing required.

**Acceptance Scenarios**:

1. **Given** a repository with an open milestone, **When** the import runs,
   **Then** the milestone appears as a Plateau element with a human-readable
   name and, where set, a due date.
2. **Given** a repository with a published release, **When** the import
   runs, **Then** the release appears as its own Plateau element, whether or
   not it is associated with a milestone.
3. **Given** the import has already run once, **When** it is run again with
   no new GitHub activity, **Then** the set of Plateau elements and their
   ids are unchanged.

---

### User Story 2 - See outstanding milestone work as Gaps (Priority: P1)

As a platform architect, I want every open GitHub issue that is assigned to
a milestone represented as a Gap against that milestone's Plateau, so that
outstanding work toward a deliberately-scoped, user-facing increment is
visible on architecture diagrams as the difference between the current and
target state.

**Why this priority**: Gaps are the other half of what makes this mapping
valuable — "what's left to reach this milestone" is the main thing a roadmap
view exists to answer, and it's equally foundational to Story 1.

**Independent Test**: Run the import and confirm every currently-open issue
that carries a milestone assignment appears as a Gap element related to that
milestone's Plateau, and that an issue with no milestone does not appear in
the imported layer at all.

**Acceptance Scenarios**:

1. **Given** an open issue assigned to a milestone, **When** the import
   runs, **Then** a Gap element appears, related to that milestone's
   Plateau.
2. **Given** an open issue with no milestone assignment, **When** the import
   runs, **Then** no element is created for that issue.
3. **Given** a milestone-assigned open issue that is later closed, **When**
   the import is re-run, **Then** the Gap element is replaced by the
   corresponding closed representation (see Story 3) and no stale Gap
   remains.
4. **Given** a milestone-assigned issue that later has its milestone removed
   (unassigned), **When** the import is re-run, **Then** the element for
   that issue is removed from the imported layer, since it is no longer
   scoped to any Plateau.

---

### User Story 3 - See completed milestone work as Work Packages / Deliverables (Priority: P2)

As a platform architect, I want every closed, milestone-assigned GitHub
issue represented as a Work Package or Deliverable realizing that
milestone's Plateau, so that the historical record of what shipped toward a
given increment — not just what's outstanding — is visible in the model.

**Why this priority**: This completes the picture Stories 1 and 2 establish
for a milestone, but closed/historical issues are read far less often than
open ones.

**Independent Test**: Run the import against a repository with a closed,
milestone-assigned issue and confirm it appears as a Work Package or
Deliverable element, related to (realizing) that milestone's Plateau.

**Acceptance Scenarios**:

1. **Given** a closed issue assigned to a milestone, **When** the import
   runs, **Then** a Work Package/Deliverable element appears, realizing that
   milestone's Plateau.
2. **Given** a closed issue with no milestone assignment, **When** the
   import runs, **Then** no element is created for that issue.

---

### User Story 4 - See roadmap-level groupings as Courses of Action (Priority: P3)

As a platform architect, I want epic-level/roadmap groupings of
milestone-scoped issues represented as Courses of Action, so that the model
shows the strategic threads that Gaps and Work Packages/Deliverables belong
to, not just a flat per-milestone list.

**Why this priority**: Valuable context once the underlying milestone-scoped
issues are already represented (Stories 1-3), but the model is useful
without it, and this repository does not yet use any epic-grouping
convention.

**Independent Test**: Run the import against a repository that has
epic-level groupings of milestone-scoped issues and confirm each grouping
appears as a Course of Action element, related to the issues it groups.

**Acceptance Scenarios**:

1. **Given** an epic-level grouping with linked, milestone-scoped issues,
   **When** the import runs, **Then** a Course of Action element appears,
   related to each linked issue's Gap or Work Package/Deliverable element.
2. **Given** a repository with no epic-grouping convention in use (the
   current state of this repository), **When** the import runs, **Then** no
   Course of Action elements are created, and every other story's import
   behavior is unaffected.

---

### User Story 5 - Refresh the roadmap on demand (Priority: P2)

As a platform architect, I want to re-run the import at any time and have
the model reflect the repository's current milestone/issue/release state,
so the roadmap view never goes stale and I never have to hand-edit the
imported elements.

**Why this priority**: Without this, the mapping is just a one-time
snapshot — the whole point of this feature over a one-off export is that it
stays current.

**Independent Test**: Run the import twice in a row with no intervening
GitHub activity and confirm the second run produces no differences in the
generated model; then make a change on GitHub (close a milestone-scoped
issue, assign a previously-unscoped issue to a milestone) and confirm a
third run reflects exactly that change and nothing else.

**Acceptance Scenarios**:

1. **Given** no change in GitHub state since the last import, **When** the
   import is re-run, **Then** the regenerated model is byte-for-byte
   unchanged.
2. **Given** one milestone-scoped issue closed and one previously-unscoped
   issue newly assigned to a milestone since the last import, **When** the
   import is re-run, **Then** only those two elements change in the
   regenerated model — every other element and its id is untouched.
3. **Given** the imported elements and the hand-authored architecture model,
   **When** the model is rebuilt, **Then** the build succeeds and passes the
   model's existing validation.

---

### Edge Cases

- An issue is reassigned from one milestone to another between import runs:
  the next import must move its relationship to the new milestone's
  Plateau, not leave a relationship to the old one.
- An issue loses its milestone assignment entirely between import runs: the
  next import must remove that issue's element (see Story 2, Scenario 4) —
  it falls out of scope rather than lingering unassociated.
- A milestone or a milestone-scoped issue is deleted on GitHub after a prior
  import: the next import reflects current GitHub state (the element is
  removed), rather than the model retaining it indefinitely as a historical
  ledger.
- A closed, milestone-scoped issue is later reopened: the next import must
  move it back from a Work Package/Deliverable to a Gap.
- An issue belongs to more than one epic-level grouping, or none: both cases
  must be representable without error.
- A release exists with no associated milestone: it is still imported as its
  own Plateau.
- A milestone's title or description happens to name a BusinessFunction
  already in the hand-authored model: the import may (best-effort) relate
  the resulting Plateau to that BusinessFunction, but a milestone that names
  none must import cleanly without that relationship — this is never a hard
  requirement.
- The GitHub API/CLI is unavailable or rate-limited when the import is run:
  the import must fail clearly rather than silently producing an empty or
  partial model layer.
- A milestone or issue title contains characters that could be
  mis-interpreted by the model's YAML authoring format: the import must
  escape/handle these safely rather than producing an unparsable file.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The import MUST represent every milestone and every published
  release in the repository — open and closed/historical alike — as a
  Plateau element.
- **FR-002**: The import MUST represent every currently-open,
  milestone-assigned issue as a Gap element, related to its milestone's
  Plateau.
- **FR-003**: The import MUST represent every currently-closed,
  milestone-assigned issue as a Work Package or Deliverable element,
  realizing its milestone's Plateau.
- **FR-004**: An issue with no milestone assignment MUST NOT be imported as
  any element — it is out of scope, not an unassociated Gap/WorkPackage.
- **FR-005**: The import MUST represent every epic-level/roadmap grouping of
  milestone-scoped issues as a Course of Action element, related to the
  issues it groups. When this repository has no such grouping convention in
  use, zero Course of Action elements is correct behavior.
- **FR-006**: Re-running the import against unchanged GitHub state MUST
  produce an identical set of element and relationship identifiers —
  running it twice in a row must not change anything.
- **FR-007**: Re-running the import after a change on GitHub MUST update
  only the elements/relationships affected by that change, leaving every
  other previously-imported element's identifier stable.
- **FR-008**: Re-running the import MUST reflect an issue's current
  open/closed state, moving it between the Gap representation and the Work
  Package/Deliverable representation as that state changes (including
  issues that are reopened after being closed).
- **FR-009**: Re-running the import MUST reflect an issue's current
  milestone assignment, moving its relationship to a new milestone's
  Plateau on reassignment, and removing the issue's element entirely if its
  milestone assignment is removed (per FR-004).
- **FR-010**: The imported elements and relationships MUST live in a layer
  that is separate from the hand-authored canonical model content, merged
  into the final architecture model by the existing build process rather
  than requiring hand-editing.
- **FR-011**: The architecture model MUST continue to pass its existing
  structural/consistency validation after the imported layer is merged in.
- **FR-012**: Architecture diagrams generated from the model MUST be able to
  reflect the imported roadmap elements once the model is regenerated.
- **FR-013**: The import MUST be runnable on demand, without requiring any
  change to the hand-authored architecture model files.
- **FR-014**: The import MUST fail clearly (rather than producing an empty
  or partially-written result) when it cannot retrieve current GitHub data.
- **FR-015**: When a milestone's title or description identifies an existing
  BusinessFunction in the hand-authored model, the import MAY relate the
  resulting Plateau to that BusinessFunction; a milestone that identifies
  none MUST still import successfully without that relationship.

### Key Entities

- **Plateau**: A milestone or release at a specific point in time — the
  model's representation of a deliberately-scoped, user-facing past,
  current, or future state of the project's delivery. Carries the
  milestone/release's name and date(s), and may (best-effort) realize a
  BusinessFunction it was named after.
- **Gap**: A currently-open issue assigned to a milestone, representing
  outstanding work relative to that milestone's Plateau. Carries the
  issue's number, title, and labels. An issue with no milestone is not a Gap
  — it has no model representation.
- **Work Package / Deliverable**: A currently-closed issue assigned to a
  milestone, representing work completed toward that milestone's Plateau.
  Carries the issue's number, title, and closure state.
- **Course of Action**: An epic-level or roadmap grouping of
  milestone-scoped issues, representing a strategic thread that spans
  multiple Gaps and/or Work Packages/Deliverables.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After an import run, every milestone, release, and
  milestone-assigned issue in the repository is represented by exactly one
  corresponding model element — none missing, none duplicated — and no
  milestone-less issue is represented by any element.
- **SC-002**: Running the import twice in a row with no intervening GitHub
  activity produces zero differences in the regenerated architecture model.
- **SC-003**: Running the import after a single GitHub change (e.g. one
  milestone-scoped issue closed) changes only the elements/relationships
  tied to that one change in the regenerated model.
- **SC-004**: A stakeholder can view the roadmap for a deliberately-scoped
  increment — its milestone, its outstanding work, and its completed work —
  as architecture diagrams, without anyone having hand-edited the underlying
  model files.
- **SC-005**: An architect can bring the roadmap view up to date with
  current GitHub activity by running one on-demand process, with no manual
  YAML editing step in between.

## Assumptions

- Milestones are authored on GitHub as deliberately-scoped, user-facing
  increments (e.g. named after a BusinessFunction MVP, as
  `policy-to-oscal-mvp` already is in this repository) — the import reflects
  whatever milestones exist and does not validate or enforce that framing
  itself; keeping milestones meaningful is an authoring discipline outside
  this feature's scope.
- "Epic-level/roadmap grouping" (User Story 4 / FR-005) is realized through
  whatever mechanism this repository already uses to group issues above the
  individual-issue level (e.g. a label, a tracking issue, or GitHub's native
  issue-grouping feature) — the exact mechanism is a planning-time decision,
  not a scope decision; this repository currently has no such grouping
  convention in use, so Story 4 covers zero elements until one exists, and
  the rest of the feature is unaffected.
- Relating a Plateau to the BusinessFunction its milestone targets (FR-015)
  is best-effort only; most milestones are not expected to carry an
  unambiguous BusinessFunction reference at this stage.
- The import runs with the same GitHub access already available in this
  environment (`gh` CLI, authenticated) — no new credential or access
  request is in scope.
- The model reflects current GitHub state as of the last import run; a
  milestone, release, or milestone-scoped issue deleted (or unassigned from
  its milestone) on GitHub is removed on the next import rather than being
  kept forever as a historical record independent of GitHub.
- No automated schedule is required to keep the model current — the import
  is triggered on demand by a person or a follow-up task, not by a
  background job, unless a future feature asks for one.
- Releases without an associated milestone are still imported as their own
  Plateau, not skipped or merged into another element.
