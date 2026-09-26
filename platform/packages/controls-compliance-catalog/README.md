# controls-compliance-catalog

Subsystem 1 of the Frictionless Architecture Platform: policy/standard documents
to OSCAL Catalogs and Profiles, via AI-assisted Markdown conversion and a
`compliance-trestle` round-trip, and Profile resolution to Resolved Catalogs.

- First extraction into the `platform/` monorepo
  ([ADR-0005](../../../docs/adr/0005-visualiser-api-ui-split-first-extraction.md),
  `ARCHITECTURE.md` §8.1).
- Home of the policy-to-OSCAL pipeline
  ([#44](https://github.com/wolffy-au/frictionless-architect/issues/44)).
- Modelled as `Controls & Compliance Catalog` in `architecture/model/`, realised by the
  `packages/controls-compliance-catalog` Artifact.

## Development

From `platform/` (one shared lock for every package — ADR-0002):

```bash
poetry install
poetry run pytest packages/controls-compliance-catalog/tests
```

`bash scripts/platform_checks.sh` from the repo root runs the full package gate
(pyright, mypy, pytest with 90% coverage) for every package.

## Layout

- `src/controls_compliance_catalog/` — the package.
- `tests/` — its tests, mirroring `src/`.
- `specs/` — this package's feature specs (`ARCHITECTURE.md` §6).
