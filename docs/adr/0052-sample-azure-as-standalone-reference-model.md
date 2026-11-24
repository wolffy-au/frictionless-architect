# ADR-0052: `sample-azure` / `sample-gcp` are standalone reference models, excluded from the merge sweep

- **Status:** Accepted
- **Date:** 2026-11-13; extended 2026-11-23 to `sample-gcp` and `sample-oscal`
- **Sources:** commits `24f75bd` (chore: add third_party/sample-azure as a git submodule), `37dd065`
  (fix(modelling-specification): drop sample-azure from vendored sweep), `b14ec53`/`03c0fbb`
  (chore(third_party): bump sample-azure submodule); `c6243bd` (chore: add third_party/sample-gcp and
  sample-oscal as git submodules), `b7fea26` (fix(modelling-specification): exclude sample-gcp from
  vendored sweep); `model_io.py` `_STANDALONE_THIRD_PARTY_MODELS`; ADR-0029 (IT4IT as vendored
  touchpoint model); ADR-0045 (tool/model separation for multi-tenant use)

<!-- adr-auditor 2026-11-23: extended at the human's request after the audit found sample-gcp and
     sample-oscal had been added (v0.12.0..HEAD) without this record covering them. The original
     sample-azure text below is unchanged; the sample-gcp / sample-oscal paragraph is new. -->

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

`sample-azure` is vendored as a **standalone demonstration/reference model**
for the multi-tenant `FRICTIONLESS_MODEL_DIR` use case (ADR-0045), not a touchpoint model to
merge (unlike IT4IT, ADR-0029). The vendored-model sweep that feeds `build.py` excludes it by
name rather than by a generic `third_party/*/elements.yaml` glob, so a future third standalone
reference submodule needs the same explicit exclusion rather than being caught automatically.
Confirmed as the intended permanent pattern; ADR-0029's merge-in behaviour is not generalized to
every `third_party/*` submodule.

**Extension (2026-11-23).** `sample-gcp` follows the same pattern as `sample-azure`: it carries its own
`elements.yaml` for standalone demo infrastructure, and `b7fea26` added it to
`_STANDALONE_THIRD_PARTY_MODELS` in `model_io.py`, so it is excluded from the sweep by name. `sample-oscal`
was added in the same change as `c6243bd`, described as the "steel thread" that ties the Azure and GCP
samples together via OPA checks. Checked against the checked-out submodules (2026-11-23): it has **no**
`elements.yaml`, so the sweep's `third_party/*/elements.yaml` glob never matches it and it needs no entry in
the exclusion set. It is not an ArchiMate model at all but an OSCAL content repo with its own Trestle
workspace (`.trestle/`, catalogs, profiles, component definitions, assessment plans/results, SSPs, POA&Ms),
Rego policies under `policies/datastores/` with their tests, and recorded OPA results under `evidence/`. It
is therefore a third kind of vendored content, neither merged (IT4IT, ADR-0029) nor a standalone model
(`sample-azure`, `sample-gcp`). Because it carries working Rego, it is the only OPA/Rego in the platform's
orbit today and is relevant to ADR-0019, still Proposed. A future `elements.yaml` added to it would be merged
silently by the glob, so that case needs an explicit decision then.

## Consequences

- Adding a third `third_party/` submodule requires deciding, and recording, which pattern it
  follows (merged like IT4IT, or standalone like `sample-azure`) rather than assuming the glob
  will do the right thing.
- `sample-azure`'s own commits (modelling the Demo Item business object, Information Structure
  and Technology Usage views, etc.) land via routine submodule bumps and are never expected to
  appear in this repo's own `architecture/model/` build output.
- No narrative doc currently explains why two vendored submodules behave differently —
  `ARCHITECTURE.md` §4 ("Forks to vendor") noting the distinction is tracked as a follow-up,
  not done by this ADR.
