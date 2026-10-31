# Vendored third-party content

`it4it` is a git submodule pinned to an upstream commit. `oscal`, `oscal-content`,
and `fedramp-automation` are plain vendored copies of only the files this repo's
tooling actually reads, each with its own `PROVENANCE.md` (upstream repo, commit
SHA, retrieval date) and a retained copy of the upstream `LICENSE.md` — not git
submodules, since none of the three is forked or patched (GH #167). All four are
read-only reference/example content, not modified in this repo. See
[ADR-0002](../docs/adr/0002-poetry-monorepo-forks-as-submodules.md) for the
submodule vendoring pattern and the ADRs linked below for each vendor's own
decision record.

## `it4it`

Upstream: [`wolffy-au/frictionless-it4it`](https://github.com/wolffy-au/frictionless-it4it)

IT4IT reference model content (`elements.yaml`/`relationships.yaml` in this
repo's own ArchiMate schema), merged into the first-party architecture model
by `architecture/model/build.py` through one shared `det_id()`/`NS` pass,
distinguished by the `it4it-` id prefix. See
[ADR-0029](../docs/adr/0029-it4it-as-vendored-touchpoint-model.md).

## `oscal`

Upstream: [`usnistgov/OSCAL`](https://github.com/usnistgov/OSCAL)

The Open Security Controls Assessment Language (OSCAL) — NIST's model and
schemas for machine-readable security control catalogs, control baselines,
system security plans, component definitions, and assessment artefacts.
Vendored here: only the Catalog and Profile schema modules
(`oscal_catalog_schema.{json,xsd}`, `oscal_profile_schema.{json,xsd}`),
retrieved from a GitHub Release rather than the git tree — OSCAL publishes its
built schemas only as release assets. See `PROVENANCE.md` for the pinned
commit/tag and retrieval date.

**License:** public domain (US government work) / CC0 1.0 Universal
(`LICENSE.md`, retained alongside the vendored files).

Vendored as reference/example input, not modified here. It is the ground
truth for the schema-alignment review in
[GH #24](https://github.com/wolffy-au/frictionless-architect/issues/24), and
gives `process-oscal-conversion`/`fn-oscal-conversion` ("OSCAL Catalog &
Profile Generation") a real schema to check against. Not consumed by
`build.py` — see [ADR-0030](../docs/adr/0030-vendor-oscal-reference-content.md).

## `oscal-content`

Upstream: [`usnistgov/oscal-content`](https://github.com/usnistgov/oscal-content)

The real NIST SP 800-53 rev5 control catalog, and the LOW / MODERATE / HIGH /
PRIVACY baseline profiles, expressed as OSCAL JSON — published by NIST
alongside the `oscal` schemas themselves. Vendored here at their existing
upstream-relative subpaths under `nist.gov/SP800-53/rev5/json/`. See
`PROVENANCE.md` for the pinned commit and retrieval date.

**License:** public domain (US government work) / CC0 1.0 Universal
(`LICENSE.md`, retained alongside the vendored files).

Vendored as reference/example input, not modified here. It gives
`process-policy-authoring`/`fn-policy-authoring` ("Policy & Standards
Authoring") concrete example input instead of only illustrative diagrams. Not
consumed by `build.py` — see
[ADR-0030](../docs/adr/0030-vendor-oscal-reference-content.md).

## `fedramp-automation`

Upstream: [`GoComply/fedramp`](https://github.com/GoComply/fedramp)

ADR-0030 originally named `GSA/fedramp-automation` as this submodule's
source; that repo has been removed from GitHub since the ADR was written —
confirmed 404 on both the web UI and the API, not a rename/redirect. GSA
appears to have consolidated FedRAMP OSCAL content onto
[automate.fedramp.gov](https://automate.fedramp.gov), a documentation site
rather than a git-hosted source, so it isn't a submodule-able replacement.

`GoComply/fedramp` is used instead: an active open-source CLI for processing
OSCAL-based FedRAMP SSPs, which bundles resolved FedRAMP baseline catalogs at
`bundled/catalogs/` — `FedRAMP_LOW-baseline-resolved-profile_catalog.xml`,
`..._MODERATE...`, and `..._HIGH...`, the only three files vendored here (no
PRIVACY baseline exists upstream). Unlike `oscal`/`oscal-content`, it is a
processing tool (not a pure content mirror): its own source is CC0-licensed,
but vendoring only the resolved baseline catalogs (not the whole repo) avoids
pulling in the Go dependency tree it bundles under non-CC0 licenses — see its
`LICENSE.md`, retained alongside the vendored files. See `PROVENANCE.md` for
the pinned commit and retrieval date, and
[ADR-0030](../docs/adr/0030-vendor-oscal-reference-content.md)'s 2026-09-28
"Known issue" note on this content's rev4/rev5 mismatch.

Vendored as reference/example input, not modified here.
