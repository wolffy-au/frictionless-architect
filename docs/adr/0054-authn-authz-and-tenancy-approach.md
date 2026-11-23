# ADR-0054: OIDC token-based authentication, RBAC-via-OPA authorization, workspace-scoped tenancy

- **Status:** Accepted
- **Date:** 2026-11-14
- **Sources:** GH #84 (part of epic GH #83); `ADR-0013` (authn/authz separation);
  `ADR-0019` (OPA/Rego policy engine, Proposed); `ADR-0024` (single-user MVP);
  `NONFUNCTIONALS.md` "Security"; `specs/EPIC-001-governance-platform/spec.md`
  FR-015/FR-016, `data-model.md` "Authentication/Authorization"

<!-- adr-auditor 2026-11-23: the authorization half depends on ADR-0019, still Proposed, with no OPA/Rego in
     this repo (only in the third_party/sample-oscal submodule, see ADR-0052). This record is Accepted
     ahead of its dependency (see Consequences). Also narrows ADR-0024's "RBAC/ABAC deferred, single-user" scope. -->

## Context

`ADR-0013` separated authorization from authentication but deferred the concrete
authn mechanism, authz model, and tenancy boundary to a later decision. Epic #83
needs that decision now: several people must be able to view and edit the same
architecture model concurrently, with different permission levels, and today the
platform has no concept of a user, session, or access boundary at all — anyone
who can reach the visualiser or schema API has full access to every model.

Existing breadcrumbs point in different directions that this ADR must reconcile:
`NONFUNCTIONALS.md` and `specs/001`'s data model mention both "secure tokens" and
ABAC; epic #83's concrete, scoped deliverable is an RBAC roles/permissions
matrix; `ADR-0019` already commits (Proposed) to OPA/Rego as the policy engine.

## Decision

- **Authentication**: standard **OIDC**, provider-agnostic (any OIDC-compliant
  IdP — Keycloak, Azure AD, Okta, etc.) rather than a self-hosted credential
  store. **Token-based**, not session-based: Authorization Code + PKCE for the
  UI, client-credentials for automated agents. FastAPI routes depend on a
  dependency that validates the bearer JWT against the IdP's JWKS and attaches
  verified identity claims to the request — no server-side session state.
- **Authorization**: **RBAC** (viewer / editor / owner / admin, per epic #83's
  scoped "Known task"), expressed as **Rego rules evaluated by OPA** (`ADR-0019`),
  living in the policy component `ADR-0013` already requires to be separate from
  authentication. The policy input is `(user, workspace_id, model_id, action)`.
  Because Rego is attribute-capable, later ABAC-style conditions (time-of-day,
  workspace tier, etc.) are additive rules, not an engine change.
- **Tenancy boundary**: **Workspace**. Every model belongs to exactly one
  Workspace. Role assignments are `(user, workspace)` pairs, not per-model —
  a user's role applies to every model in a workspace they hold it in. Every
  policy check and Neo4j query is scoped by `workspace_id`; a query that omits
  it is a defect.

## Consequences

- Deny-by-default is achievable uniformly: every protected route gets the same
  JWT-validation dependency, and every policy/query call takes the same
  `(user, workspace_id, model_id, action)` shape — satisfying epic #83's
  "Authorization enforcement" and "Tenancy / data isolation" tasks with one
  mechanism each, not bespoke per-endpoint logic.
- No IdP vendor is chosen here; onboarding the business collaboration driving
  epic #83 requires picking or standing up one OIDC provider as a separate,
  deployment-level decision.
- **Model impact** (`architecture/model/`, done in this PR): added
  `fn-authn-oidc` (owned by `sub-portal`, the one mounting surface every
  package's routes already go through) and `fn-authz-policy` (owned by
  `sub-assurance`, which `ADR-0019` already places the OPA wrapper in), linked
  by a `Flow` carrying ADR-0013's "identity attributes supply authorization"
  rule; `store-akg`'s description now records that access to it is scoped by
  workspace (not to be confused with `art-tech-oscal-workspace`, the
  unrelated Trestle round-trip filesystem directory). No new top-level
  Workspace element: at this model's granularity
  (the platform's own architecture, not customer model instances) tenancy is
  a data-shape fact about `store-akg`, not a separate ArchiMate concept — same
  footing as how elements/relationships/views inside a customer model aren't
  individually modelled here either. The Neo4j schema itself (a `workspace_id`
  scoping property on model nodes) is implementation, carried through the
  plan/tasks for #83's sub-issues, not this ADR.
- Per-model sharing with a user outside their workspace (e.g. an external
  collaborator on one model) is out of scope here; if needed later it layers
  on as an explicit override on top of the workspace boundary, not a redesign.
- `ADR-0019` remains Proposed; this ADR depends on it being accepted before
  the RBAC-via-OPA enforcement can ship. If `ADR-0019` is rejected or
  superseded, this ADR's authorization section must be revisited.
- Revisit if: a second IdP integration is needed simultaneously (multi-IdP),
  or per-model ACLs become a hard requirement rather than a future extension.

## Alternatives considered

- **Self-hosted credential store** (passwords/MFA built and held by this
  platform) — rejected: rolling our own identity provider is exactly what a
  bank-compliance platform (APRA CPS 234) should avoid in-house, and
  contradicts `NONFUNCTIONALS.md`'s "industry-standard mechanisms."
- **Server-side sessions** — rejected: adds a session-store dependency the
  platform doesn't otherwise have, and fits a stateless FastAPI API consumed
  by both a UI and automated agents worse than bearer tokens.
- **Pure ABAC from scratch** (no role concept) — rejected: epic #83's scoped,
  concrete deliverable is an RBAC matrix; starting from unconstrained
  attribute rules delays shipping what's actually needed now, when OPA/Rego
  can express RBAC today and grow into ABAC later without a rewrite.
- **Per-model-only tenancy (no Workspace concept)** — rejected: doesn't match
  epic #83's explicit ask for workspace/org scoping, and gives no natural unit
  for org-level policy or role assignment; every grant would be a one-off.
