# ADR-0030: Vendor OSCAL/FedRAMP content as submodules; consume trestle as a dependency

- **Status:** Accepted
- **Date:** 2026-09-20; revised 2026-09-24
- **Sources:** conversation record (this ADR is not yet back-filled from any narrative doc)

## Context

The architecture model commits to OSCAL-based compliance
(`fn-policy-authoring`, `fn-oscal-conversion`, "Trestle Markdown",
`bo-oscal-*`/`art-oscal-*` DataObjects) with no backing content or tooling —
`ARCHITECTURE.md` lists "which OSCAL tool?" as open, and `ADR-0002` names
"OSCAL tooling" as an anticipated fork category without confirming an
upstream.

`ADR-0029`'s IT4IT pattern (a `third_party/` submodule of ArchiMate-shaped
YAML, merged into the first-party model by `build.py`'s `det_id()` pass)
doesn't transfer: NIST/FedRAMP content is real OSCAL JSON/XML in OSCAL's own
schema, and `compliance-trestle` is a Python library/CLI, not a reference
model — neither is something `build.py` has any business merging.

## Decision

Split the vendoring approach by what each upstream actually is:

- **Vendor as plain `third_party/` git submodules** (no `fork-sync` entry —
  static reference content, not a patched fork):
  - `third_party/oscal` ← `usnistgov/OSCAL` (public domain/CC0) — schemas,
    the ground truth for spec-alignment review (GH #24).
  - `third_party/oscal-content` ← `usnistgov/oscal-content` (public domain)
    — the real NIST SP 800-53 rev5 catalog and LOW/MODERATE/HIGH/PRIVACY
    baseline profiles.
  - `third_party/fedramp-automation` — FedRAMP OSCAL baselines (see
    Implementation note below for the actual upstream).
  - None are consumed by `build.py` — read-only reference content, not
    model data to merge.
- **Consume `compliance-trestle` as an ordinary Poetry dependency**, not a
  submodule. Per `ADR-0002`, `third_party/` is for forks we track and
  potentially patch; we only need trestle's published library/CLI behaviour,
  so it's declared in `pyproject.toml` like any other dependency.
- **Model trestle as `ext-trestle`** in the existing "External systems"
  convention (alongside `ext-llm`/`ext-regsources`), relating into
  `fn-oscal-conversion` via `Serving`/`Realization`, with `desc` noting it's
  a dependency, not vendored source.
- License compatibility: Apache-2.0 (trestle) and public domain/CC0 (the
  three vendored repos) are all compatible with this repo's AGPL-3.0 — no
  copyleft conflict.

This resolves "which OSCAL tool?": consumed as a dependency, not forked; the
NIST/FedRAMP content isn't a "tool" requiring a fork decision at all.

## Consequences

- `sample-data/oscal/` and tests can use the vendored submodules as
  fixtures (tracked as a follow-up, not built here).
- CI must check out submodules (`actions/checkout: submodules: true`) or
  `third_party/*` is silently empty (tracked as GH #21).
- No `build.py` wiring needed for the vendored OSCAL/FedRAMP paths, unlike
  `ADR-0029`'s IT4IT case.
- `compliance-trestle` upgrades follow normal `poetry update`/Dependabot,
  not `fork-sync`.
- Forking/patching trestle later supersedes this decision and needs its own
  ADR.

## Implementation note (2026-09-20): fedramp-automation source swap

`GSA/fedramp-automation` no longer exists (confirmed 404, not a
rename/redirect); FedRAMP content moved to `automate.fedramp.gov`, a docs
site rather than a git source. `third_party/fedramp-automation` is instead
vendored from [`GoComply/fedramp`](https://github.com/GoComply/fedramp), an
active CLI bundling resolved LOW/MODERATE/HIGH baselines at
`bundled/catalogs/` (no PRIVACY baseline; own source is CC0, but it also
vendors Go dependencies under their own non-CC0 licenses). Detail:
`third_party/README.md`.

## Implementation note (2026-09-24): oscal-document-workbench is ported, not vendored

`oscal-compass-lab/compliance-trestle-skills` (Apache-2.0) solves an
adjacent problem (drafting an SSP against an existing catalog) via a Claude
Code plugin, not a library or service. Two of its scripts have directly
reusable *designs* for this feature's different problem (authoring a new
Catalog/Profile from verbatim text): `extract-legacy-doc.sh`'s
document-sectioning/traceability scheme and `validate-oscal-package.sh`'s
validation-report shape. Neither vendoring path above fits agent-only
tooling with no installable interface, so the decision is to **port the
logic as native Python** (`normalizer.py`, `trestle_ops.py`), with
Apache-2.0 §4 attribution headers in the ported modules noting origin and
license. Full detail: `specs/003-oscal-ai-conversion/research.md` R10.

## Alternatives considered

- **Vendor `compliance-trestle` as a submodule** (mirroring IT4IT) —
  rejected: no need to fork/patch its source; `third_party/` overhead
  (pinning, no dependency-resolution) buys nothing over an ordinary
  dependency here.
- **Merge NIST/FedRAMP content into `build.py` like IT4IT** — rejected:
  it's real OSCAL JSON/XML, not ArchiMate model YAML; nothing for
  `det_id()` to merge.
- **Leave OSCAL/trestle prose-only, no real content** — rejected: the model
  has referenced "Trestle Markdown"/"OSCAL Catalogs and Profiles" since
  GH #7 with nothing to check it against; spec-alignment review (GH #24)
  needs real ground truth.
- **Vendor oscal-document-workbench under `third_party/` and shell out to
  its scripts** — rejected: it's a Claude Code plugin, not a versioned
  library/CLI with a stable interface; shelling out adds a subprocess
  dependency and a foreign runtime for logic simple enough to port
  directly.
- **Depend on oscal-document-workbench as an installed package** —
  rejected: it isn't published as one; it exists only as agent-invocable
  skill files.
