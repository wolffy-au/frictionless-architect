# ADR-0049: ADR attestation is a pluggable, admin-configurable method registry; GPG is the first method

- **Status:** Accepted
- **Date:** 2026-11-09
- **Sources:** `specs/EPIC-001-governance-platform/spec.md` FR-006, "Deferred solution decisions"
  (cryptographic scheme and identity/certificate model for ADR attestation); ADR-0012 (ADR as
  attested FSM); GH #198

## Context

ADR-0012 fixed the ADR entity's state machine and required a verifiable human cryptographic
signature to move an ADR to `Approved` or `Superseded`, but deliberately left the concrete
scheme and identity/certificate model as a deferred solution decision. The MVP is single-user
and locally run (ADR-0024), but the platform's target is a hosted, multi-tenant bank governance
platform where different deployments will have different identity infrastructure already in
place (personal GPG keys, an internal PKI, a keyless OIDC-based scheme, etc.) — fixing one
scheme now would force every future deployment through it or force a breaking change later.

## Decision

Attestation is implemented as a **pluggable "Attestation Method" registry**: the set of
enabled methods is an administrator-configured property of a deployment, never hardcoded to a
single scheme. Each method owns its own identity/certificate binding model and is responsible
for producing a verifiable signature over the ADR's canonical content (Title, Status, Date,
Decision, Consequences) plus resolving that signature to a named, accountable person.

**GPG/OpenPGP detached signatures are the first implemented method.** The identity is the
signer's PGP key fingerprint, resolved against an admin-configured keyring mapping fingerprints
to named people. An ADR transition to `Approved` or `Superseded` (ADR-0012's FSM) requires a
signature from one enabled, configured method that verifies against that method's identity
store; an unverifiable signature or unrecognized key blocks the transition.

## Consequences

- Introduces an attestation-method registry/interface in the eventual
  `architecture-governance` package. The registry's concrete interface shape, config format,
  and how an admin enables/maps identities are implementation detail for that package's
  `plan.md`, not this ADR.
- GPG is the only method required for the single-user local MVP (ADR-0024); one
  fingerprint-to-person mapping is enough to exercise the FSM end to end.
- Additional methods (e.g. Sigstore/cosign keyless signing, X.509 PKI via an internal CA) can
  be added later purely by extending the registry — they do not require revisiting this
  decision.
- The package spec (GH #201) must describe the registry and the GPG method at the what/why
  level; the registry interface itself is plan-level work.

## Alternatives considered

- **Single fixed scheme, no registry** — rejected: different deployments (a bank's internal
  PKI vs. a laptop MVP vs. a GitHub-native org) have different identity infrastructure already
  in place; locking to one scheme now would force a breaking change later.
- **Sigstore/cosign keyless signing as the only method** — rejected as the *sole* method: it
  depends on external Fulcio/Rekor services, which an air-gapped or regulated deployment may
  not be able to reach; viable as one more registry entry, not the first/only one.
- **X.509 PKI via an internal CA as the only method** — rejected as the sole/first method:
  requires provisioning a CA and certificate lifecycle well ahead of the single-user MVP's
  actual need; viable as a later registry entry for deployments that already run one.
