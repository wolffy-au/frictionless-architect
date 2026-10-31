# Provenance: third_party/oscal

- **Upstream repository**: <https://github.com/usnistgov/OSCAL>
- **Commit SHA**: `e061961c7702afeabffdf5e59894d35e748dade1` (tag `v1.2.3`)
- **Retrieval date**: 2026-10-29
- **License**: Public domain / CC0 (`LICENSE.md`, retained in this directory)

## Vendored files

Schema files are published by this upstream only as GitHub Release assets for
tag `v1.2.3` (the OSCAL git tree itself carries no built schema output), so they
were retrieved from the `v1.2.3` release rather than the git tree:

- `oscal_catalog_schema.json`, `oscal_catalog_schema.xsd`
- `oscal_profile_schema.json`, `oscal_profile_schema.xsd`

`LICENSE.md` and `README.md` were retrieved from the git tree at the same commit.

Only the Catalog and Profile schema modules are vendored — this repo's
schema-alignment tooling validates OSCAL Catalog and Profile documents
(Resolved-Catalog stays a distinct, not-yet-consumed module; see
`platform/packages/controls-compliance-catalog/specs/001-oscal-ai-conversion/plan.md`).
