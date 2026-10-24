# Feature Specification: Conversational Solution Design Modelling

**Feature Branch**: `feature/gh-139-conversational-modelling-spec`

**Created**: 2026-10-24

**Status**: Draft

**Input**: User description: "Add a conversational interface for the Solution Architect role to refine a Solution Design (do-solution-design/art-solution-design in store-patterns) in natural language, with live re-rendered ArchiMate views, distinct from and never touching the enterprise knowledge graph (do-candidate-arch/store-akg) that GH #108/ADR-0037's fn-conversational-authoring already edits. The new function is fn-solution-modelling, Assigned to sub-library (subsystem 2, reusable-architecture-library), Serving fn-notation-engine in sub-modelling (subsystem 6) for rendering. Business-layer process-conversational-solution-modelling Composes into the existing bfn-solution-design alongside the structured, pattern-composed process-solution-design -- same business capability, two authoring modes. Per GH #68's resolved open question, the MVP is free-form modelling (the architect describes changes directly), not composing from a pattern/blueprint library -- pattern composition and OSCAL System Security Plan emission (fn-solution-compose) are deferred to a later milestone. Scope is bounded to one Solution Design at a time; no promotion between enterprise and domain models (that's milestone D, GH #149). Per GH #68 decisions: one journey API per role (Solution Architect, plus a read-only Compliance Officer/Auditor role per decision 5), with a stubbed policy check on every call; the API contract streams from day one (SSE or websocket) with a stub simulating LLM latency; the agent acts under the architect's own identity and can never exceed that architect's journey permissions. Needs behave acceptance scenarios (GH #139's explicit requirement)." (GH #139, epic GH #68)

## Clarifications

### Session 2026-10-24

- Q: Free-form modelling vs. composing from a pattern/blueprint library for the MVP? → A: Free-form (GH #68's resolved open question) — the architect describes changes directly; `fn-solution-compose`'s pattern/blueprint composition and OSCAL System Security Plan emission are deferred to a later milestone. This feature covers only the conversational path (`fn-solution-modelling`).
- Q: Does this feature's agent ever write to `architecture/model/` or promote changes between enterprise and domain models? → A: No. Scope is bounded to one Solution Design (`do-solution-design`/`art-solution-design` in `store-patterns`) at a time. Promotion between enterprise and domain models is milestone D (GH #149), out of scope here.
- Q: Does this feature reuse GH #108/ADR-0037's `fn-conversational-authoring`? → A: No — distinct function (`fn-solution-modelling`), distinct target artefact and store (ADR-0039). The two are never merged or superseded; a reviewer tells them apart by target artefact and store, not by name alone.

## User Scenarios & Testing *(mandatory)*

### Overall flow

One conversational solution-modelling session, scoped to a single Solution Design. The Solution Architect's request goes through the journey API; a stubbed policy check runs on every call; nothing is written to the Solution Design until the architect accepts a proposed change.

### User Story 1 - Describe a Solution Design change and see it validated and rendered (Priority: P1)

A Solution Architect describes a change to their Solution Design in plain language (e.g. "add a new SolutionComponent for the payment gateway, served by the API component"). The agent proposes a candidate delta to that Solution Design, validates it against the ArchiMate metamodel, and — once accepted — renders the affected part of the Solution Design as a live ArchiMate view next to the conversation, without the architect hand-editing the design or running a manual render step.

**Why this priority**: This is the feature's core loop; without it there is no conversational Solution Design authoring capability at all.

**Independent Test**: Describe a single well-formed change to a Solution Design in conversation and confirm a diagram reflecting it appears, and that no other Solution Design or the enterprise knowledge graph is touched.

**Acceptance Scenarios**:

1. **Given** a Solution Architect has an open Solution Design and describes a valid, unambiguous change, **When** the agent proposes the delta, **Then** it validates cleanly against the ArchiMate metamodel and, once the architect accepts it, is applied to that Solution Design only.
2. **Given** a change has just been applied, **When** the architect asks to see the affected SolutionComponent or a described view of the Solution Design, **Then** the corresponding diagram renders immediately, reflecting the Solution Design's current state.
3. **Given** a proposed change would alter the enterprise knowledge graph or any Solution Design other than the one open in the session, **When** the agent evaluates the request, **Then** it refuses the request and explains that this session is scoped to a single Solution Design.

---

### User Story 2 - Only the Solution Architect's own journey permissions apply (Priority: P1)

The agent acts under the requesting architect's own identity and journey, and can never exceed what that architect's role is permitted to do. A Compliance Officer / Auditor can open the same journey API in a read-only capacity to review a Solution Design and its conversation history, but cannot propose or apply changes.

**Why this priority**: Without a role-scoped journey API and a policy check on every call, this feature cannot sit safely under GH #68's planned RBAC layer (milestone D) without rework, and a conversational surface that could write outside its caller's permissions is a governance risk the rest of the epic depends on avoiding.

**Independent Test**: Call the journey API as a Solution Architect and confirm changes can be proposed and applied; call it as a Compliance Officer / Auditor against the same Solution Design and confirm every read succeeds but every write (propose, accept, apply) is refused.

**Acceptance Scenarios**:

1. **Given** a request arrives from a Solution Architect's own identity, **When** the journey API receives it, **Then** the stubbed policy check authorizes the operations that role's journey permits (propose, accept, apply, render, query) and no others.
2. **Given** a request arrives from a Compliance Officer / Auditor's identity, **When** the journey API receives it, **Then** read/query/render operations succeed and any attempt to propose, accept, or apply a change is refused with an explanation of why.
3. **Given** any request, **When** the policy check for that role and operation fails, **Then** the agent never performs the operation on the Solution Design, regardless of how the request was phrased.

---

### User Story 3 - The conversation streams, including simulated latency (Priority: P2)

The journey API streams its response from the first token, including while a stub simulates realistic LLM latency, so the architect sees progressive feedback rather than a blocking wait.

**Why this priority**: Valuable for a responsive conversational experience and required by GH #68's decision 6 (Principle IV: operations over 200ms must be asynchronous or justified), but the propose/validate/render loop (P1) already delivers the feature's core value without streaming wired end to end.

**Independent Test**: Issue a request against the stubbed agent service and confirm the response arrives as a stream of incremental events (not one blocking reply), with the stub's simulated latency visible as a delay before the first event rather than before the whole response.

**Acceptance Scenarios**:

1. **Given** a Solution Architect submits a request, **When** the stubbed agent service processes it, **Then** the journey API delivers the response as a stream of events (e.g. server-sent events or a websocket), starting before the full reply is ready.
2. **Given** the stub simulates LLM latency, **When** a request is submitted, **Then** the delay is visible before streaming starts, not as a single pause before a non-streamed reply.

---

### Edge Cases

- A request that would promote a change from a Solution Design into the enterprise or domain model, or that otherwise implies writing to `architecture/model/`, is refused: that promotion path is out of this feature's scope (GH #149).
- A request to compose the Solution Design from a pattern or blueprint (rather than describing the change directly) is met with an explanation that pattern/blueprint composition is a separate, structured authoring mode (`fn-solution-compose`, `process-solution-design`) not covered by this conversational feature, and the architect is not silently redirected or auto-converted into that mode.
- A Compliance Officer / Auditor's read-only session against a Solution Design with no accepted changes yet still succeeds — an empty Solution Design is a valid thing to query, not an error.
- A request from an identity that maps to neither the Solution Architect nor the Compliance Officer / Auditor journey is refused outright, with no partial read or write performed.
- A policy-check failure produces the same visible outcome (refusal with an explanation) regardless of whether the underlying cause is a genuinely disallowed operation or a stub returning a negative decision — the architect is never shown an internal error for a permissions refusal.
- If the agent's underlying LLM call fails or times out mid-stream, the architect sees a clear failure in the stream rather than a silently truncated response, and no partial, unvalidated delta is applied to the Solution Design.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The journey API MUST accept a natural-language description of an intended change to a specific, already-open Solution Design and propose a candidate delta scoped to that Solution Design only.
- **FR-002**: The agent MUST validate every candidate delta against the ArchiMate metamodel before it is applied to the Solution Design.
- **FR-003**: The agent MUST NOT write to `architecture/model/`, the enterprise knowledge graph (`do-candidate-arch`/`store-akg`), or any Solution Design other than the one open in the current session, under any request.
- **FR-004**: The journey API MUST perform a policy check, scoped to the calling identity's role, before performing any operation (propose, accept, apply, render, query) on a Solution Design.
- **FR-005**: The Solution Architect role's journey MUST be permitted to propose, accept, apply, render, and query changes to a Solution Design it has access to.
- **FR-006**: The Compliance Officer / Auditor role's journey MUST be permitted to render and query a Solution Design and its conversation history, and MUST be refused when it attempts to propose, accept, or apply a change.
- **FR-007**: When a policy check refuses an operation, the agent MUST explain the refusal to the caller and MUST NOT perform any part of the refused operation.
- **FR-008**: The journey API MUST stream its response to a request as a sequence of incremental events rather than a single blocking reply.
- **FR-009**: The stubbed agent service MUST simulate realistic LLM latency before streaming begins, consistent with GH #68 decision 6.
- **FR-010**: The agent MUST render the Solution Design view under discussion live via the platform's existing rendering function (`fn-notation-engine`), without a manual render step, when the architect requests a view or an explicit object.
- **FR-011**: A request to compose a Solution Design from an existing pattern or blueprint MUST be explained as out of this feature's scope (the structured composition mode, `fn-solution-compose`) rather than silently attempted or auto-converted.
- **FR-012**: The agent MUST act under the requesting architect's own identity for every operation; no operation is ever performed under a different identity than the one that made the request.

### Key Entities *(include if feature involves data)*

- **Solution Design**: The bounded artefact this feature's agent edits (`do-solution-design`/`art-solution-design` in `store-patterns`). One session is scoped to exactly one Solution Design; this feature never promotes a change out of it into the enterprise or domain model.
- **Candidate Delta**: A proposed, not-yet-applied change to the open Solution Design, derived from the architect's natural-language request; discarded if not accepted.
- **Journey API call**: One role-scoped, policy-checked, streamed request/response exchange between a caller (Solution Architect or Compliance Officer / Auditor) and the agent service, operating on a single Solution Design.
- **Policy Decision**: The stubbed authorization outcome (allow/refuse) for a given identity, role, and operation, evaluated on every journey API call before the operation proceeds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Solution Architect can go from describing an intent to seeing a validated, rendered change to their Solution Design without hand-editing the design or running a manual render command.
- **SC-002**: 100% of requests that would write outside the open Solution Design (to `architecture/model/`, the enterprise knowledge graph, or another Solution Design) are refused, with none silently redirected or partially applied.
- **SC-003**: 100% of write operations (propose, accept, apply) attempted by a Compliance Officer / Auditor identity are refused; 100% of read operations (render, query) by that identity succeed.
- **SC-004**: 100% of journey API responses begin streaming before the full reply is ready, including when the stub is simulating latency.

## Assumptions

- The Solution Architect and Compliance Officer / Auditor roles, and the journey-API-per-role pattern, follow GH #68's decisions 3, 5, and 7; the policy check itself remains a stub in this feature (the real policy engine, ADR-0019/OPA, lands in milestone D, GH #148).
- `fn-solution-modelling` (Assigned to `sub-library`, subsystem 2 `reusable-architecture-library`) and the business-layer `process-conversational-solution-modelling` (Composing into the existing `bfn-solution-design`) are already recorded in `architecture/model/` per GH #138 and ADR-0039; this feature does not re-decide that placement.
- Whether `fn-solution-modelling` validates against `do-convention-rules` (the enterprise/domain convention rules `fn-conversational-authoring` already uses) is left open by ADR-0039 and is not decided by this spec; it is revisited when GH #140 (UI shell) or GH #142 (agent service) needs an answer, since a Solution Design is bounded rather than enterprise-wide and the same conventions may not apply unmodified.
- The journey API, UI, and agent for this feature are placed in `platform/packages/reusable-architecture-library/{ui,api}` per GH #68 decision 8; rendering, validation, and view checks are served by `fn-notation-engine`, already implemented in the existing `platform/packages/modelling-specification` package (GH #108/ADR-0037). `reusable-architecture-library` itself does not exist yet as an extracted package — the monorepo pattern it would follow is already proven by `modelling-specification`, `controls-compliance-catalog`, `digital-twin-knowledge-graph`, and `schema-visualizer-api`, so GH #68's "blocked on the monorepo pattern being proven" note is stale. This feature's specification does not depend on the extraction having happened, only its eventual implementation does.
- Duplicate-detection, pattern-suggestion, and override-decision mechanics analogous to GH #108/ADR-0037's `fn-conversational-authoring` are not assumed to carry over to this feature by default; if the Solution Design authoring loop needs equivalent safeguards, that is a decision for `/speckit-plan`, not assumed here.
- Multi-architect concurrent editing of the same Solution Design, and locking/merging semantics, are out of scope (GH #151, milestone D).
- Behave acceptance scenarios for this feature's user stories are deferred to its own implementation phase, package-scoped under `platform/packages/reusable-architecture-library/tests/features/` once that package exists, rather than written now at specify time — matching GH #108/ADR-0037's own precedent (its behave scenarios were written during implementation against the real running app, not during `/speckit-specify`, see `specs/EPIC-003-conversational-model-authoring/tasks.md`). This spec's Acceptance Scenarios above are the basis those future scenarios will be written from.
