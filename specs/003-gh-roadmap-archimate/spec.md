# Feature Specification: GitHub Roadmap as ArchiMate Implementation & Migration

**Feature Branch**: `feature/gh-95-roadmap-archimate`

**Created**: 2026-10-03

**Status**: Draft

**Input**: User description: "Map GitHub issues and milestones into the canonical ArchiMate model under architecture/model/, representing them as Implementation & Migration layer elements — but milestone-first and user-facing, not a raw dump of every GitHub issue."

## Clarifications

### Session 2026-10-04

- Q: What should the second GitHub milestone (multi-user collaboration) be titled? → A: `multi-user-collaboration`, giving the Plateau id `plat-multi-user-collaboration-2`.
- Q: Should every Work Package of a milestone realize the release's Deliverable, or only closed ones? → A: Only closed ones, and no Work Package realizes a Plateau directly. Open Work Packages realize a per-milestone planned Deliverable, which realizes the Plateau.
- Q: If several releases name the same milestone's Plateau, which release Deliverable does a closed Work Package realize? → A: The first of those releases published after the issue was closed. If there is none yet, the planned Deliverable.
- Q: Should a GitHub pre-release count as a published release? → A: No. Pre-releases are skipped, as drafts are; only full published releases become Deliverables.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See milestones as Plateaus (Priority: P1)

As a platform architect, I want every GitHub milestone in this repository
represented as a Plateau in the architecture model, so that the project's
deliberately-scoped past, current, and planned states appear on the model's
Implementation & Migration views alongside the rest of the architecture.

**Why this priority**: Plateaus are the backbone the rest of this mapping hangs
off: Deliverables realize a Plateau, and Work Packages realize Deliverables. Without
them nothing else has anywhere to attach.

**Independent Test**: Run the import against this repository (which has one
milestone, `policy-to-oscal-mvp`, and zero releases) and confirm the milestone
appears as exactly one Plateau element, with no manual YAML editing.

**Acceptance Scenarios**:

1. **Given** a repository with an open milestone, **When** the import runs,
   **Then** the milestone appears as a Plateau with its title as the name, its
   description, and, where set, its due date.
2. **Given** a milestone description that names an existing business function
   (an identifier beginning `bfn-`), **When** the import runs, **Then** the
   Plateau realizes that business function.
3. **Given** a milestone description that names no business function, or names
   an identifier that does not match an existing one, **When** the import runs,
   **Then** the Plateau is imported without that relationship.
4. **Given** the import has already run once, **When** it is run again with no
   new GitHub activity, **Then** the Plateaus and their identifiers are
   unchanged.

---

### User Story 2 - See milestone-assigned issues as Work Packages (Priority: P1)

As a platform architect, I want every issue that is itself assigned to a
milestone represented as a Work Package that contributes to that milestone's
Plateau through a Deliverable, whether it is still planned (open) or already
done (closed), so that both the plan and the historical record toward a given
increment are visible in the model.

**Why this priority**: Work Packages are the leaves of the roadmap; without them
Plateaus are empty headings.

**Independent Test**: Run the import against a repository with open and closed
milestone-assigned issues and confirm each appears as a Work Package realizing
a Deliverable of that milestone's Plateau, with its open/closed state
recorded, that none realizes the Plateau directly, and that an issue without a
milestone of its own does not appear.

**Acceptance Scenarios**:

1. **Given** an open issue assigned to a milestone, **When** the import runs,
   **Then** a Work Package appears, realizing that milestone's planned
   Deliverable, with its state recorded.
2. **Given** a closed issue assigned to a milestone whose Plateau is named by a
   release published after the issue was closed, **When** the import runs,
   **Then** its Work Package realizes the first such release's Deliverable. If
   no such release exists, it realizes the planned Deliverable instead.
3. **Given** an issue with no milestone of its own, **When** the import runs,
   **Then** no element is created for it, even if its parent or its
   sub-issues have a milestone.
4. **Given** an issue's milestone is later changed, **When** the import is
   re-run, **Then** its realization moves to a Deliverable of the new
   milestone's Plateau.
5. **Given** an issue is closed or reopened, **When** the import is re-run,
   **Then** its recorded state changes and, where a qualifying release exists,
   so does the Deliverable it realizes; its identifier is unchanged.
6. **Given** a parent issue and one of its sub-issues are both imported,
   **When** the import runs, **Then** the parent aggregates the sub-issue.

---

### User Story 3 - See releases as Deliverables (Priority: P2)

As a platform architect, I want every published release represented as a
Deliverable that the closed Work Packages of its milestone produce and that
realizes the milestone's Plateau, so that what actually shipped, and in which
release, is distinct from what is still planned.

**Why this priority**: Releases add the "what shipped" view, but the roadmap is
useful without them (this repository has none yet), so they follow Stories 1
and 2.

**Independent Test**: Import a repository with a published release whose notes
name a milestone's Plateau, and confirm the Deliverable realizes that Plateau.

**Acceptance Scenarios**:

1. **Given** a published release, **When** the import runs, **Then** a
   Deliverable appears with the release name and tag recorded.
2. **Given** release notes that name an imported Plateau, **When** the import
   runs, **Then** the Deliverable realizes that Plateau, and the Work Packages
   of that milestone closed before the release was published (and not already
   in an earlier release) realize it, while its open Work Packages keep
   realizing the planned Deliverable.
3. **Given** release notes that name no Plateau, or name an identifier that does
   not match an imported Plateau, **When** the import runs, **Then** the
   Deliverable is still imported, standing alone.
4. **Given** any imported Work Package, **When** the import runs, **Then** it
   has no direct realization of a Plateau; it reaches the Plateau only through
   a Deliverable.
5. **Given** a draft or pre-release, **When** the import runs, **Then** it is
   not imported, and no Work Package is attached to it.
6. **Given** two releases both name the same Plateau, and a Work Package was
   closed between them, **When** the import runs, **Then** it realizes the later
   release only; Work Packages closed before the earlier release realize the
   earlier one.

---

### User Story 4 - See issue dependencies as Triggering (Priority: P2)

As a platform architect, I want GitHub's native "blocked by" dependencies
between imported issues shown as Triggering relationships, so that the order in
which work must happen is visible on the roadmap, including which milestones
depend on which.

**Why this priority**: Order is the second thing a roadmap answers, but it needs
Stories 1 and 2 first.

**Independent Test**: Import a repository where one imported Work Package is
blocked by another and confirm a Triggering relationship runs from the blocker
to the blocked item.

**Acceptance Scenarios**:

1. **Given** Work Package B is blocked by Work Package A and both are imported,
   **When** the import runs, **Then** A triggers B.
2. **Given** blocked-by links where either end is not imported, **When** the
   import runs, **Then** those links are not imported.
3. **Given** a Work Package in milestone N blocks one in milestone M (N ≠ M),
   **When** the import runs, **Then** Plateau N triggers Plateau M, once,
   however many such dependencies exist.

---

### User Story 5 - Refresh safely and repeatably (Priority: P1)

As an architect, I want to bring the roadmap up to date with one on-demand
process that never leaves the model half-updated and that changes nothing when
GitHub has not changed, so that I can run it freely and review its output in
version control.

**Why this priority**: A roadmap layer that churns or half-writes cannot be
trusted or reviewed; this governs every other story.

**Independent Test**: Run the import twice with no GitHub activity in between
and confirm no file changes; run it with GitHub unreachable and confirm no file
changes and a clear error.

**Acceptance Scenarios**:

1. **Given** the import has run, **When** it is run again with no GitHub
   activity, **Then** nothing in the generated layer changes.
2. **Given** one imported issue is closed on GitHub, **When** the import is
   re-run, **Then** only that issue's recorded state changes.
3. **Given** GitHub cannot be reached, is rate-limited, or returns incomplete
   data, **When** the import runs, **Then** it stops with a message naming what
   failed and how to fix it, and no file is changed.
4. **Given** a check-only run, **When** the generated layer is out of date,
   **Then** the process reports it as stale without writing anything.

---

### User Story 6 - Roadmap and hand-authored model work together (Priority: P2)

As an architect, I want the imported Plateaus and Work Packages to sit alongside
the hand-authored parts of the model that only a person can judge (the
baseline state, the Gaps between states, and Strategy), so that each element
has exactly one owner and nothing is duplicated.

**Why this priority**: Without a clear ownership split the same milestone would
appear twice, once hand-authored and once imported.

**Independent Test**: After the first import, confirm the milestone appears
once, as the imported Plateau, and that the hand-authored links that used to
point at the old runtime plateau now resolve to it.

**Acceptance Scenarios**:

1. **Given** the hand-authored runtime plateau for the first MVP, **When** the
   import is first adopted, **Then** it is replaced by the imported Plateau for
   that milestone, and its hand-authored links and view memberships point at the
   imported Plateau.
2. **Given** the hand-authored plateau and gap for team collaboration, **When**
   the `multi-user-collaboration` milestone exists, **Then** they are renamed for
   that milestone (the plateau becomes `plat-multi-user-collaboration-2`) and keep
   their descriptions and links.
3. **Given** an imported Plateau is renamed or deleted on GitHub, **When** the
   model is built, **Then** the build fails naming any hand-authored reference
   that no longer resolves.
4. **Given** the model's Gaps, baseline state and Strategy elements, **When**
   the import runs, **Then** it neither creates, changes nor deletes any of
   them.

---

### Edge Cases

- An issue is reassigned from one milestone to another between import runs: the
  next import moves its relationship to the new milestone's Plateau, leaving
  none to the old one.
- An issue loses its milestone between import runs: its element and
  relationships are removed on the next import.
- A milestone or an imported issue is deleted on GitHub after a prior import:
  the next import reflects current GitHub state and removes it, rather than
  keeping it as a historical ledger.
- A closed issue is later reopened: its recorded state changes and, where a
  release Deliverable exists, it moves back to realizing the planned
  Deliverable.
- A milestone has no Work Packages: no planned Deliverable is created for it.
- A Work Package is closed after the latest release: it stays with the planned
  Deliverable until a later release is published, then moves to that release.
- Dependencies that form a cycle: imported as written; the importer does not
  reject or resolve them.
- A release's notes name a Plateau that was not imported: the Deliverable is
  imported without that relationship.
- An issue or milestone is retitled: its identifier changes with its title, so
  hand-authored references to it fail the build until updated.
- Two issues have the same title: their identifiers still differ, because each
  carries its issue number.
- A very long title: the readable part of the identifier is shortened at a word
  boundary, and the number keeps it unique.
- The GitHub API or CLI is unavailable or rate-limited: the import fails
  clearly rather than producing an empty or partial layer.
- GitHub returns more items than one page can hold: the import fails rather than
  importing a partial set.
- A title or description contains characters that could be misread by the
  model's YAML authoring format: the import escapes them safely and still
  produces a parseable file.
- A relationship that the model's rules would not permit is never emitted; the
  model must still validate after the layer is merged.
- Release notes or a milestone description name an identifier that is
  malformed, unknown, or belongs to an element of the wrong type: it is ignored,
  the element is still imported, and no relationship is created from it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The import MUST represent every milestone, open and
  closed/historical alike, as a Plateau element, carrying its title,
  description and, where set, due date.
- **FR-002**: The import MUST represent every issue that is itself assigned to a
  milestone as a Work Package element, whether the issue is open or closed. Its
  open/closed state is recorded as a property, not as a different element
  type. A Work Package MUST NOT realize a Plateau directly; it reaches the
  Plateau only through a Deliverable (FR-004).
- **FR-003**: An issue is in scope only when it carries a milestone itself. The
  import MUST NOT infer scope from a parent, a descendant or a label, and any
  other issue MUST NOT be imported as any element.
- **FR-004**: The import MUST represent every published, non-pre-release release
  (drafts and pre-releases are skipped) as a Deliverable
  element that realizes the Plateau named in the release notes, when the notes
  name an imported Plateau. It MUST also create, for each milestone that has at
  least one Work Package, one planned Deliverable that realizes that milestone's
  Plateau. Every closed Work Package MUST realize the first release Deliverable, among
  those realizing its milestone's Plateau, that was published after the issue
  was closed, and otherwise the planned Deliverable. Every open Work Package
  MUST realize the planned Deliverable. A Work Package realizes exactly one
  Deliverable.
- **FR-005**: The import MUST NOT emit a relationship that an existing chain of
  relationships already implies.
- **FR-006**: GitHub's native "blocked by" dependency between two imported Work
  Packages MUST be imported as a Triggering relationship from the blocker to the
  blocked item. A dependency between Work Packages in different milestones MUST
  also be imported as a single Triggering relationship from the blocker's
  Plateau to the blocked item's Plateau. A dependency with an unimported end is
  not imported.
- **FR-007**: When two imported issues are in a parent and child relationship,
  the import MUST relate parent to child by aggregation.
- **FR-008**: When a milestone's description names an existing business function
  by its model identifier, the import MUST relate the resulting Plateau to it by
  realization. A milestone that names none MUST still import successfully.
- **FR-009**: Every element identifier MUST begin with a prefix for the type of
  object it represents (Plateau, Deliverable, Work Package) and MUST NOT begin
  with a prefix naming the source system. The source's number and URL are
  recorded as properties.
- **FR-010**: A Plateau identifier MUST combine a readable form of the
  milestone title with the milestone number. A Work Package identifier MUST
  combine a readable form of the issue title, cut at a word boundary to a
  bounded length, with the issue number. A release Deliverable identifier MUST
  combine the release tag, and a planned Deliverable identifier MUST combine its
  milestone's title and number and mark it as planned. Identifiers MUST be unique and MUST be a pure function of the
  GitHub object's current number and title (or tag).
- **FR-011**: Re-running the import against unchanged GitHub state MUST produce
  byte-identical output; running it twice in a row must change nothing.
- **FR-012**: Re-running the import after a change on GitHub MUST update only
  the elements and relationships affected by that change.
- **FR-013**: Re-running the import MUST reflect an issue's current state and
  milestone: closing or reopening changes its recorded state (and, where a qualifying
  release exists, which Deliverable it realizes); reassigning moves its
  realization to the new milestone; removing its milestone removes its element.
- **FR-014**: The imported elements and relationships MUST live in a layer that
  is separate from the hand-authored model, merged into the final architecture
  model by the existing build process, and MUST NOT be hand-edited.
- **FR-015**: The import MUST NOT create, change or delete any Gap, the baseline
  Plateau, or any Strategy element (Capability or Course of Action). Those
  remain hand-authored.
- **FR-016**: The architecture model MUST continue to pass its existing
  structural and consistency validation after the layer is merged, and every
  emitted relationship MUST be one the ArchiMate rules permit between its two
  element types.
- **FR-017**: Architecture diagrams generated from the model MUST be able to
  reflect the imported roadmap, including a view per milestone and the overall
  Implementation & Migration overview.
- **FR-018**: The import MUST be runnable on demand without changing any
  hand-authored model file, and MUST offer a check-only mode that reports
  whether the layer is current without writing.
- **FR-019**: The import MUST fail clearly, writing nothing, when it cannot
  retrieve complete current GitHub data (unavailable, unauthenticated,
  rate-limited, unparseable, or more items than one page holds).
- **FR-020**: The hand-authored runtime plateau for the first MVP MUST be
  replaced by the imported Plateau for that milestone, with its relationships
  and view memberships retargeted in the same change. The hand-authored
  collaboration plateau and gap MUST be renamed for the
  `multi-user-collaboration` milestone, the plateau taking the identifier
  `plat-multi-user-collaboration-2`.
- **FR-021**: The mapping decision (what each GitHub object becomes, the
  identifier scheme, the scope rule and the ownership split) MUST be recorded as
  an architecture decision record in the same change. The architecture narrative
  and the model's own documentation MUST be updated to agree with it in that
  same change; where that is not possible, a tracking issue MUST be opened and
  the decision marked accepted-but-not-yet-reflected in the decision log's
  index until it is.
- **FR-022**: Text read from GitHub (milestone descriptions, release notes,
  titles) is untrusted. A model identifier named in a milestone description or
  release notes MUST be honoured only when it exactly matches an existing
  element of the permitted type (a business function for a Plateau, an imported
  Plateau for a Deliverable). Any other text MUST be ignored for the purpose of
  relationships, and no GitHub text MAY change which elements or relationships
  are emitted beyond what this specification defines.

### Key Entities

- **Plateau**: A milestone at a specific point in time: the model's
  representation of a deliberately-scoped, user-facing past, current or future
  state of delivery. Carries the milestone's title, description, state and due
  date, and may realize a business function it names.
- **Work Package**: An issue that carries its own milestone, representing a unit
  of planned (open) or completed (closed) work toward a Plateau. Carries the
  issue's number, URL and state.
- **Deliverable**: Either a published release (what shipped), produced by the
  Work Packages closed before it was published and not in an earlier release, or
  the per-milestone planned Deliverable (what is still to ship), produced by the
  open ones and by closed ones no release yet covers. Each realizes its
  milestone's Plateau; a release names that Plateau in its notes.
- **Dependency**: A GitHub "blocked by" link, imported as Triggering between Work
  Packages and, derived from those, between Plateaus.
- **Gap, baseline Plateau, Strategy elements**: Hand-authored, not imported. A
  Gap is the difference between two Plateaus; the baseline Plateau is the start
  state before any milestone.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After an import run, every milestone, published release and
  milestone-assigned issue in the repository is represented by exactly one
  model element (plus one planned Deliverable per milestone that has Work
  Packages), none missing, none duplicated, and no other issue is
  represented by any element.
- **SC-002**: Running the import twice in a row with no intervening GitHub
  activity produces zero differences in the regenerated layer and architecture
  model.
- **SC-003**: Running the import after a single GitHub change (for example one
  imported issue closed) changes only the elements and relationships tied to that
  one change.
- **SC-004**: A stakeholder can view the roadmap for a deliberately-scoped
  increment (its milestone, its planned work and its completed work) as an
  architecture diagram, without anyone having hand-edited the generated layer.
- **SC-005**: An architect can bring the roadmap view up to date by running one
  on-demand process, with no manual YAML editing in between.
- **SC-006**: When GitHub is unreachable or incomplete, the process fails with a
  message naming the cause in 100% of runs and leaves every file unchanged.
- **SC-007**: After the first import, the first-MVP milestone appears exactly
  once in the model and no hand-authored link refers to the retired runtime
  plateau.

## Assumptions

- Milestones are authored on GitHub as deliberately-scoped, user-facing
  increments (named after a business function MVP, as `policy-to-oscal-mvp`
  already is in this repository). Keeping them meaningful is an authoring
  discipline outside this feature's scope. Which issues are imported, and at
  what granularity, is controlled entirely by which issues carry a milestone.
- GitHub's structure does not say whether an issue is an epic, feature, story or
  task, so this feature does not try to tell them apart: every milestone-assigned
  issue is a Work Package.
- Gaps, the baseline Plateau and Strategy elements stay hand-authored, because
  they are architectural judgements that GitHub data cannot establish. A Gap is
  related to its two Plateaus by association only, which is the only
  relationship the ArchiMate rules permit there.
- Dependencies come from GitHub's native "blocked by" links, which this
  repository already uses.
- GitHub has no link between a release and a milestone, so a release is tied to a
  Plateau only through the Plateau's model identifier named in its notes; a
  release that names none stands alone.
- The identifiers contain readable text taken from titles, so retitling a
  milestone or issue changes its identifier. Hand-authored references then fail
  the build with an unknown-identifier error and are updated in the same change.
  This is accepted in exchange for readable identifiers.
- A second milestone, titled `multi-user-collaboration`, does not yet exist on
  GitHub. Its title is settled; creating it is an outward-facing action that
  still needs the maintainer's approval. Until it exists, the hand-authored
  collaboration plateau and gap keep their current names.
- The import runs with the GitHub access already available in this environment
  (`gh` CLI, authenticated); no new credential is in scope.
- The model reflects current GitHub state as of the last import run; a milestone,
  release or issue deleted or leaving scope on GitHub is removed on the next
  import, not kept as a historical record.
- No automated schedule is required; the import is triggered on demand by a
  person or a follow-up task.
- The architecture decision record for the mapping takes the next free number
  in the decision log at the time it is filed.
