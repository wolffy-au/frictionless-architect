# golden-oscal fixtures

A vendored, provenance-tracked copy of the NIST/FedRAMP source material this
project's policy-to-OSCAL pipeline is tested against.

## Why this exists

`third_party/` (git submodules pinned to `oscal-content`, `fedramp-automation`,
`oscal`, `it4it`) gives live access to upstream NIST/FedRAMP OSCAL content, but
a submodule is only as durable as the repo it points at. GSA's own
`fedramp-automation` repository has previously disappeared from the internet
entirely — a pinned commit SHA doesn't help if the remote it needs to fetch
from is gone. Tests and QA workflows should not depend on those repos staying
reachable.

This directory holds a **frozen, self-contained snapshot** of exactly the
source material needed for golden-dataset testing, captured with full
provenance so it can be verified, refreshed, or audited later. `third_party/`
remains available for reference and exploration, but nothing under `tests/`
should read from it directly.

## Layout

- `standards/` — standalone verbatim NIST publication PDFs (SP 800-53 Rev 5,
  CSF 2.0, FIPS 199, FIPS 200), downloaded directly from nist.gov. These are
  the *independent* ground truth for tracing OSCAL-embedded control prose
  back to its original published source — used to QA the agentic
  prose-to-OSCAL conversion pipeline, not just to validate OSCAL structure.
- `slice-0-conversion/` — conversion-only starter (no profiles); see below.
- `slice-1-minimal/`, `slice-2-medium/`, `slice-3-full/` — the same three
  axes of OSCAL content (catalog, profiles, FedRAMP resolved baselines, CSF),
  each slice a strict superset of scope over the last. See below.

Every OSCAL `.json` file also has a sibling `.yaml` (same basename), a lossless
re-serialisation of the JSON, so both OSCAL formats Trestle reads are covered. The YAML
checksums live in each sidecar's `yaml_representation` block. FedRAMP XML has no YAML
sibling.

## Tier / slice growth model

| Slice | Scope | Status |
|---|---|---|
| `slice-0-conversion` | Conversion only, no profiles: 2 simple base controls (PS-9, SC-25) with catalog + Trestle Markdown. Easiest starting point for the AI converter | populated |
| `slice-1-minimal` | Exactly 5 entries (AC-2 + its AC-2.1/AC-2.11 enhancements, AU-2, IA-3) chosen to show both enhancement-set growth and presence/absence across the SP 800-53B baselines. Split into `1a-conversion/` (standard → Markdown, User Stories 1→2) and `1b-resolution/` (profile + catalog → resolved catalog, User Story 3). No FedRAMP excerpt (dropped for simplicity — see slice-1's own README) | populated |
| `slice-2-medium` | Full AC and AU control families — catalog, baseline profiles, FedRAMP excerpts, Trestle Markdown | populated |
| `slice-3-full` | Complete files: full catalog, all baselines (incl. PRIVACY), all FedRAMP resolved baselines, full CSF 2.0 catalog | populated |

Each slice is meant to be usable independently — a test that only needs
cross-baseline behavior for a handful of controls should use `slice-1-minimal`
rather than loading the full catalog. Add `slice-4-*` etc. the same way if a
narrower or differently-scoped tier is ever needed; there's nothing special
about the number 3.

## Provenance sidecar convention

Every vendored file (or tightly-coupled group of files from one source) has a
`<name>.provenance.yaml` sidecar next to it recording: the exact source
(submodule + commit SHA, or an external URL), license, capture date,
extraction method, and a sha256 checksum. See any existing sidecar for the
schema. When refreshing a fixture from a newer upstream commit, update its
sidecar's `source_commit`/`sha256`/`captured_date` in the same change.

## Known issues

- The vendored `fedramp/` content (`slice-2-medium/`, `slice-3-full/`) is SP
  800-53 **rev4** (OSCAL `1.0.0-milestone3`), not rev5 — it is not a valid
  comparison target against the rev5 catalog/profiles used everywhere else
  in this fixture set. See `docs/adr/0030-vendor-oscal-reference-content.md`'s
  2026-09-28 "Known issue" note. No rev5-compatible FedRAMP source has been
  identified yet.

## What's deliberately not here

- The FedRAMP profile *delta* document (the tailoring diff before it's merged
  with its parent SP 800-53B baseline) — only the resolved,
  self-contained profile-as-catalog form is vendored. Decided with the repo
  owner; revisit if delta-level testing is ever needed.
- FIPS 199/200 as OSCAL — NIST never published one. Their standalone PDFs are
  vendored in `standards/` for QA reference; the OSCAL-side operationalization
  of what they define is the SP 800-53B baseline profiles.
