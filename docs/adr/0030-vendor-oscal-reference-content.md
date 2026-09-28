# ADR-0030: Vendor OSCAL/FedRAMP content as submodules; consume trestle as a dependency

- **Status:** Accepted
- **Date:** 2026-09-20; revised 2026-09-24, 2026-09-28
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

- Tests use vendored, provenance-tracked fixtures under
  `tests/fixtures/golden-oscal/` rather than reading `third_party/*`
  submodules directly — see the 2026-09-28 implementation note below.
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
license. Full detail: `platform/packages/controls-compliance-catalog/specs/001-oscal-ai-conversion/research.md` R10.

## Implementation note (2026-09-28): golden-test fixtures vendored independently of the submodules

The 2026-09-20 note above already shows the risk this decision was meant to
manage isn't hypothetical: `GSA/fedramp-automation` disappeared outright and
had to be re-sourced from `GoComply/fedramp`. That same failure mode — a
pinned submodule commit becomes unfetchable if the upstream repo is taken
down, rewritten, or rate-limits/blocks CI — applies equally to the
`sample-data/oscal/` fixtures follow-up this ADR's Consequences section
flagged and deferred. Relying on `third_party/*` submodules being *fetchable
at test time* (not just pinned) would make the test suite hostage to the same
availability risk this ADR already had to work around once.

Decision: golden-dataset test fixtures are vendored as plain committed files
under `tests/fixtures/golden-oscal/`, not read from `third_party/` at test
time. `third_party/*` submodules remain the reference/exploration copies
(spec-alignment review, ad hoc lookups) but carry no test dependency.

- Structure is tiered and grows deliberately: `slice-1-minimal/` (a small,
  cross-cutting control set — AC-2 plus its AC-2.1/AC-2.11 enhancements,
  AU-2, and IA-3 — chosen because it shows both enhancement-set growth
  (AC-2) and presence/absence (IA-3) across the NIST 800-53 rev5
  LOW/MODERATE/HIGH baselines; no FedRAMP excerpt at this tier, dropped for
  simplicity), `slice-2-medium/` (full AC/AU control families, catalog,
  baseline profiles, FedRAMP excerpts, Trestle Markdown), and `slice-3-full/`
  (complete catalog, all four baseline profiles including PRIVACY, all three
  FedRAMP resolved catalogs, the full CSF v2.0 catalog).
- `slice-1-minimal/` is further split into `1a-conversion/` (standard →
  Trestle Markdown, User Stories 1→2 territory) and `1b-resolution/`
  (catalog + profile → resolved catalog, User Story 3 territory), sharing a
  top-level `catalog/` between them — see slice-1's own README.
- Every vendored artifact (or coherent group of them) carries a sidecar
  `<name>.provenance.yaml`: source repo/commit SHA or source URL, license,
  capture date, extraction method, and a sha256 checksum — so staleness or
  tampering is checkable without re-fetching upstream.
- `tests/fixtures/golden-oscal/standards/` additionally vendors the
  standalone verbatim NIST/FIPS publication PDFs (SP 800-53 rev5, CSF 2.0,
  FIPS 199, FIPS 200) fetched directly from `nvlpubs.nist.gov` — these have
  no OSCAL form in any submodule at all, and exist here so control prose in
  the OSCAL catalog can be manually traced back to its source document when
  QA'ing the agentic prose→OSCAL conversion pipeline.
- FedRAMP's resolved-profile-as-catalog files (the only form vendored in
  `third_party/fedramp-automation`) are self-contained — no baseline
  `import` chain to resolve — so `slice-2-medium/`'s FedRAMP excerpts could
  drop the `<back-matter>` sections and keep just the relevant controls'
  subtree (`slice-1-minimal/` carries no FedRAMP excerpt at all; see the
  2026-09-28 "Known issue" note below on the FedRAMP content's own rev4/rev5
  mismatch).

This resolves the Consequences-section follow-up: `sample-data/oscal/` was
not used (fixtures belong under `tests/fixtures/` per this repo's testing
layout convention), but the underlying need — real OSCAL ground truth
available to tests — is now met, without adding a live-submodule dependency
to do it.

## Known issue (2026-09-28): vendored FedRAMP baselines are rev4, not rev5

`third_party/fedramp-automation` (vendored from `GoComply/fedramp`, commit
`22fdd080273f5ec98c1c9c07f677659046af63f5` — see the 2026-09-20 note above for
why this fork was used instead of `GSA/fedramp-automation`) ships SP 800-53
**Revision 4** content, not Revision 5: its resolved-profile-as-catalog XML
declares `oscal-version` `1.0.0-milestone3` and carries 125/325/421 controls
for LOW/MODERATE/HIGH respectively — rev4 control counts, not rev5's. Every
other fixture in `tests/fixtures/golden-oscal/` (the NIST catalog, the SP
800-53B baseline profiles, the resolved catalogs derived from them) is rev5.

Practically: the vendored `fedramp/` content under `slice-2-medium/` and
`slice-3-full/` cannot legitimately serve as the comparison target for
FR-007/SC-003-style checks (does our rev5-derived output match FedRAMP's
tailoring?) against the rev5 catalog/profiles used everywhere else — the
control id sets and structure don't line up. This was caught by cross-session
review while building out the `slice-1-minimal` golden dataset and confirmed
independently against the vendored XML and its provenance sidecar.

No rev5-compatible FedRAMP source has been identified yet. This is a known,
deliberately-deferred gap, not an oversight: golden-dataset and fixture work
continues without it, and any test or fixture that would otherwise assert an
FR-007/SC-003-style FedRAMP comparison should either skip it explicitly or
note this ADR rather than compare against the rev4 content as if it were
valid. Revisit sourcing a rev5 FedRAMP baseline (OSCAL-native GSA content, or
a resolved-profile export at the right revision) before relying on this
comparison.

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
