# ADR-0030: Vendor OSCAL/FedRAMP content as submodules; consume trestle as a dependency

- **Status:** Accepted
- **Date:** 2026-09-20
- **Sources:** conversation record (this ADR is not yet back-filled from any narrative doc)

## Context

The architecture model already commits to OSCAL-based compliance in its vision:
`process-policy-authoring`/`fn-policy-authoring` ("Policy & Standards Authoring")
and `process-oscal-conversion`/`fn-oscal-conversion` ("OSCAL Catalog & Profile
Generation") name "Trestle Markdown" and a "Trestle round-trip" in prose
(origin: GH #7), and a full artefact chain of `bo-oscal-*`/`art-oscal-*`
DataObjects models Catalog, Profile, Component Definition, SSP, and Assessment
Results. None of this is backed by real content or tooling: `sample-data/oscal/`
holds only two illustrative PlantUML diagrams, `third_party/` holds only the
`it4it` submodule, `.claude/skills/fork-sync/forks.yml` has a commented-out
`oscal-cli` stub, and `ARCHITECTURE.md` lists "which OSCAL tool?" as an open
question. `ADR-0002` names "OSCAL tooling" as an anticipated fork category but
never confirms an upstream.

`ADR-0029` established the vendoring pattern for IT4IT: a `third_party/` git
submodule holding raw `elements.yaml`/`relationships.yaml` in this repo's own
schema, merged into the first-party model by `build.py` through one shared
`det_id()`/`NS` pass, distinguished by an id prefix (`it4it-`). That pattern
doesn't transfer directly here: NIST/FedRAMP OSCAL content is real OSCAL
JSON/XML data in OSCAL's own schema, not ArchiMate model YAML, and
`compliance-trestle` is a Python library/CLI, not a reference model — neither
is something `build.py`'s `det_id()` pass has any business merging.

## Decision

Split the vendoring approach by what each upstream actually is:

- **Vendor as plain `third_party/` git submodules** (no `fork-sync` entry —
  static reference content, not a patched fork):
  - `third_party/oscal` ← `usnistgov/OSCAL` (public domain/CC0) — OSCAL
    schemas/models, the ground truth for the spec-alignment review (GH #24).
  - `third_party/oscal-content` ← `usnistgov/oscal-content` (public domain) —
    the real NIST SP 800-53 rev5 catalog and LOW/MODERATE/HIGH/PRIVACY
    baseline profiles as OSCAL JSON, giving `Policy & Standards Authoring`
    concrete example input instead of only illustrative diagrams.
  - `third_party/fedramp-automation` ← `GSA/fedramp-automation` (public
    domain/CC0) — FedRAMP's own OSCAL baselines/profiles layered on the NIST
    catalog.
  - None of these are consumed by `build.py` — they're read-only reference/
    example content, not ArchiMate model data to merge.
- **Consume `compliance-trestle` as an ordinary Poetry main/runtime
  dependency**, not a `third_party/` submodule. Per `ADR-0002`, `third_party/`
  is for forks we track and potentially patch; we only need trestle's
  published library/CLI behaviour (Markdown-authoring and OSCAL round-trip),
  so it's declared in `pyproject.toml` like any other dependency
  (`neo4j`, `httpx`, ...), not vendored as source.
- **Model trestle in the architecture model** as `ext-trestle`, an
  `ApplicationComponent` in the existing "External systems" convention
  (`elements.yaml`, alongside `ext-llm`/`ext-regsources`) — no new `props`
  vocabulary. Its relationship into `fn-oscal-conversion` reads as
  "invokes"/"realizes" (`Serving`/`Realization`), not `Flow`/`Access` like the
  peer-system externals, and its `desc` states "third-party Python
  library/CLI dependency, not vendored source" so it isn't confused with the
  `it4it-` vendored-content pattern.
- License compatibility: Apache-2.0 (`compliance-trestle`) and public
  domain/CC0 (the three vendored repos) are all compatible with this repo's
  AGPL-3.0 licensing — no copyleft conflict, no NOTICE-file relicensing risk.

This resolves `ARCHITECTURE.md`'s open question ("which OSCAL tool?"): the
answer is "consumed as a dependency, not forked," and the NIST/FedRAMP catalog
content itself isn't a "tool" requiring a fork decision at all.

## Consequences

- `sample-data/oscal/` and future tests can reference real catalog/profile
  files from the vendored submodules as worked examples/fixtures (tracked as
  a follow-up, not built as part of this decision).
- CI must check out git submodules (`actions/checkout` with
  `submodules: true`) or `third_party/*` — including the pre-existing `it4it`
  submodule — silently appears empty in CI (tracked separately as GH #21).
- No first-party build step depends on the vendored OSCAL/FedRAMP paths, so
  there's no `VENDORED_MODELS`-style wiring needed in `build.py`, unlike
  `ADR-0029`'s IT4IT case.
- `compliance-trestle` version upgrades follow the normal `poetry update` /
  Dependabot flow, not `fork-sync`.
- If a future need arises to fork and patch `compliance-trestle` (rather than
  consume it as published), that supersedes this decision and needs its own
  ADR — the `third_party/` + `fork-sync` mechanism from `ADR-0002` would then
  apply instead.

## Alternatives considered

- **Vendor `compliance-trestle` as a `third_party/` submodule** (mirroring
  IT4IT) — rejected: we don't need to fork or patch its source, only consume
  its published library/CLI behaviour; `third_party/` is reserved for forks
  we track per `ADR-0002`, and using it here would create maintenance
  overhead (submodule pinning, no dependency-resolution/version-conflict
  checking) with no corresponding benefit over an ordinary dependency.
- **Merge NIST/FedRAMP OSCAL content into `build.py` like IT4IT** — rejected:
  OSCAL catalogs/profiles are real OSCAL JSON/XML, not ArchiMate model YAML;
  there's nothing for `det_id()` to hash or merge, and doing so would
  conflate reference compliance content with the architecture model itself.
- **Leave OSCAL/trestle as prose-only vision, no real content** — rejected:
  the model has referenced "Trestle Markdown" and "OSCAL Catalogs and
  Profiles" since GH #7 with nothing to check it against; the spec-alignment
  review (GH #24) needs real OSCAL schema content as ground truth.
