# portal

Host package (not one of the six subsystems) that serves the platform packages'
UIs from one app. It mounts each package's router and owns only page chrome,
navigation and the role landing page — never feature logic.

- Decided in the [ADR-0020](../../../docs/adr/0020-per-subsystem-uis.md) update of
  2026-10-11 ([#120](https://github.com/wolffy-au/frictionless-architect/issues/120)).
- Each package keeps its own `app.py` for standalone development; the portal
  path-depends on them.

## Run

```bash
cd platform
poetry run uvicorn portal.app:app --reload
```

Open `http://127.0.0.1:8000/` for the landing page.

## Mounted UIs

| Path | UI | Package |
|---|---|---|
| `/catalog` | Control conversion playground | `controls-compliance-catalog` |
| `/settings/llm` | LLM settings, mounted once for every package | `llm-provider-config` |

To add a package UI: include its router in `src/portal/app.py` and add a
`MountedUi` entry so the landing page lists it.
