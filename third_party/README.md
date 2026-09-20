# Vendored third-party content

Each subdirectory here is a git submodule pinned to an upstream commit — read-only
reference/example content, not modified in this repo. See
[ADR-0002](../docs/adr/0002-poetry-monorepo-forks-as-submodules.md) for the
general vendoring pattern and the ADRs linked below for each vendor's own
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
schemas (XML/JSON/YAML) for machine-readable security control catalogs,
control baselines, system security plans, component definitions, and
assessment artefacts.

**License:** public domain (US government work) / CC0 1.0 Universal.

Vendored as reference/example input, not modified here. It is the ground
truth for the schema-alignment review in
[GH #24](https://github.com/wolffy-au/frictionless-architect/issues/24), and
gives `process-oscal-conversion`/`fn-oscal-conversion` ("OSCAL Catalog &
Profile Generation") a real schema to check against. Not consumed by
`build.py` — see [ADR-0030](../docs/adr/0030-vendor-oscal-reference-content.md).

## `oscal-content`

Upstream: [`usnistgov/oscal-content`](https://github.com/usnistgov/oscal-content)

The real NIST SP 800-53 rev5 control catalog, and the LOW / MODERATE / HIGH /
PRIVACY baseline profiles, expressed as OSCAL JSON/XML — published by NIST
alongside the `oscal` schemas themselves.

**License:** public domain (US government work) / CC0 1.0 Universal.

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
`..._MODERATE...`, and `..._HIGH...`. Unlike `oscal`/`oscal-content`, it is a
processing tool (not a pure content mirror): it has no PRIVACY baseline, and
its own source is CC0-licensed but the repo also vendors Go dependencies
under their own (non-CC0) licenses — see its `LICENSE.md`.

Vendored as reference/example input, not modified here. ADR-0030 needs a
follow-up amendment to record this substitution.
