# Provenance: third_party/oscal-content

- **Upstream repository**: <https://github.com/usnistgov/oscal-content>
- **Commit SHA**: `78650f02ad9321bb7b817846f8fbd4f2bcd620de` (tag `v1.5.0`)
- **Retrieval date**: 2026-10-29
- **License**: Public domain (`LICENSE.md`, retained in this directory)

## Vendored files

- `nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json` — the NIST SP
  800-53 rev5 catalog.
- `nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_{LOW,MODERATE,HIGH,PRIVACY}-baseline_profile.json`
  — the four baseline profiles.
- `LICENSE.md`, `README.md`.

These paths match `source_repo`/`source_path` in the existing
`tests/fixtures/golden-oscal/**/*.provenance.yaml` sidecars for this upstream
repository, confirming this commit is the one already in use for those fixtures.
