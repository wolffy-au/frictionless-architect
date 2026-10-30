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

## Run the playground

The playground converts a pasted OSCAL control or catalog (YAML or JSON) to
`compliance-trestle` Markdown, and prose to a candidate control. From the repo root:

```bash
./scripts/run-controls_compliance_catalog.sh   # http://127.0.0.1:8001/catalog
```

It serves `controls_compliance_catalog.app:app` on port 8001 with reload. The
[`portal`](../portal/README.md) mounts the same router at `/catalog` on port 8000.

| Route | Purpose |
| --- | --- |
| `GET /catalog` | The playground page. |
| `POST /catalog/oscal-to-markdown` | OSCAL control or catalog to Trestle Markdown. |
| `POST /catalog/prose-to-markdown-candidate` | Prose to an AI-drafted candidate control. |
| `GET /settings/llm` | LLM provider settings page and JSON API (`llm-provider-config`). |

The prose route calls an LLM through `litellm`, so it needs a provider credential
(for example `ANTHROPIC_API_KEY`) or one set on the settings page. The OSCAL route does not.

## Layout

- `src/controls_compliance_catalog/` — the package.
- `tests/` — its tests, mirroring `src/`.
- `specs/` — this package's feature specs (`ARCHITECTURE.md` §6).
