# Provenance: third_party/fedramp-automation

- **Upstream repository**: <https://github.com/GoComply/fedramp>
- **Commit SHA**: `22fdd080273f5ec98c1c9c07f677659046af63f5` (tag `v0.1.4-25-g22fdd08`)
- **Retrieval date**: 2026-10-29
- **License**: CC0 core (`LICENSE.md`, retained in this directory). This vendored
  subset does not include this upstream's vendored Go dependency tree
  (`vendor/`), avoiding its non-CC0-licensed dependency surface.

## Vendored files

- `bundled/catalogs/FedRAMP_{LOW,MODERATE,HIGH}-baseline-resolved-profile_catalog.xml`
  — the three FedRAMP resolved baseline catalogs.
- `LICENSE.md`, `README.md`.

**No PRIVACY baseline exists upstream** — only LOW/MODERATE/HIGH resolved
baseline catalogs are published by this repository.

**Known issue carried over from ADR-0030**: these resolved-baseline catalogs
ship SP 800-53 **Revision 4** content, not Revision 5 (`oscal-version`
`1.0.0-milestone3`; rev4 control counts). This is an upstream limitation of
`GoComply/fedramp`, not an artifact of vendoring — see ADR-0030's 2026-09-28
"Known issue" note for detail.

This commit matches `source_repo`/`source_commit` already recorded in the
existing `tests/fixtures/golden-oscal/**/*.provenance.yaml` sidecars for this
upstream repository.
