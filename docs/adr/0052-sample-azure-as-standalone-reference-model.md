# ADR-0052: `sample-azure` is vendored as a standalone reference model, excluded from the vendored-model merge sweep

- **Status:** Proposed
- **Date:** 2026-11-13
- **Sources:** commits `24f75bd` (chore: add third_party/sample-azure as a git submodule), `37dd065`
  (fix(modelling-specification): drop sample-azure from vendored sweep), `b14ec53`/`03c0fbb`
  (chore(third_party): bump sample-azure submodule); ADR-0029 (IT4IT as vendored touchpoint model);
  ADR-0045 (tool/model separation for multi-tenant use)

## Context

`third_party/it4it` is vendored and merged into this repo's own model: `build.py` loads it
alongside the first-party YAML, filtered or whole, into one `det_id()`/`NS` pass (ADR-0029).
This cycle added a second `third_party/` submodule, `sample-azure`
(`frictionless-sample-azure.git`), carrying its own `elements.yaml` for standalone use — per
`37dd065`, this is "a different repo['s] own model" in ADR-0045's multi-tenant sense (a
separate org installing `modelling-specification` and pointing `FRICTIONLESS_MODEL_DIR` at its
own model directory), not reference content meant to merge into this repo's model the way IT4IT
is. The generic `third_party/*/elements.yaml` glob the vendored-sweep used did not distinguish
the two cases, so `sample-azure` was pulled into the root model and its own `diagrams/` wherever
the submodule checkout happened to carry that file locally, until `37dd065` excluded it by name.
This split — one vendored submodule merged in, a second deliberately kept separate — is a real
decision with a plausible alternative (treat every `third_party/*` submodule the same way, per
ADR-0029's general pattern) and currently exists only in commit messages; no ADR or narrative doc
(`ARCHITECTURE.md`, `TECHNICAL.md`) mentions `sample-azure` at all.

## Decision

> DRAFT — confirm: `sample-azure` is vendored as a **standalone demonstration/reference model**
> for the multi-tenant `FRICTIONLESS_MODEL_DIR` use case (ADR-0045), not a touchpoint model to
> merge (unlike IT4IT, ADR-0029). The vendored-model sweep that feeds `build.py` excludes it by
> name rather than by a generic `third_party/*/elements.yaml` glob, so a future third standalone
> reference submodule needs the same explicit exclusion rather than being caught automatically.

## Consequences

> DRAFT — confirm:

- Adding a third `third_party/` submodule requires deciding, and recording, which pattern it
  follows (merged like IT4IT, or standalone like `sample-azure`) rather than assuming the glob
  will do the right thing.
- `sample-azure`'s own commits (modelling the Demo Item business object, Information Structure
  and Technology Usage views, etc.) land via routine submodule bumps and are never expected to
  appear in this repo's own `architecture/model/` build output.
- No narrative doc currently explains why two vendored submodules behave differently; once this
  ADR is Accepted, `ARCHITECTURE.md` §4 ("Forks to vendor") should probably note the distinction
  — tracked as a follow-up, not done by this ADR.
