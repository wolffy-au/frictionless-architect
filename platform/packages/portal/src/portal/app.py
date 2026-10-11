"""FastAPI entry point for the portal: `uvicorn portal.app:app`."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape

from controls_compliance_catalog.llm_client import COMPONENT_ID as CATALOG_COMPONENT_ID
from controls_compliance_catalog.playground.api import router as playground_router
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from llm_provider_config import Component, create_settings_router


@dataclass(frozen=True)
class MountedUi:
    """A package UI the portal mounts, as the landing page lists it."""

    path: str
    title: str
    role: str


# Packages keep their own routes for now: the playground's page JS calls
# absolute /playground/... URLs, so it can't move under a per-package prefix
# until it uses prefix-relative ones (GH #120).
MOUNTED_UIS: tuple[MountedUi, ...] = (
    MountedUi("/playground", "Control conversion playground", "Compliance Officer / Auditor"),
    MountedUi("/settings/llm", "LLM settings", "All roles"),
)

app = FastAPI(title="Frictionless Architect Portal")
app.include_router(playground_router)
app.include_router(
    create_settings_router([Component(id=CATALOG_COMPONENT_ID, label="Control conversion (AI candidate)")]),
)


def _landing_page() -> str:
    roles: dict[str, list[MountedUi]] = {}
    for ui in MOUNTED_UIS:
        roles.setdefault(ui.role, []).append(ui)
    sections = "".join(
        f"<section><h2>{escape(role)}</h2><ul>"
        + "".join(f'<li><a href="{escape(ui.path)}">{escape(ui.title)}</a></li>' for ui in uis)
        + "</ul></section>"
        for role, uis in roles.items()
    )
    return _PAGE.replace("__SECTIONS__", sections)


@app.get("/", response_class=HTMLResponse)
def landing() -> str:
    """List every mounted UI, grouped by the role it serves."""
    return _landing_page()


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Frictionless Architect</title>
<style>
  :root { --bg:#f7f7f5; --surface:#fff; --text:#1c1c1a; --faint:#6b6b66; --border:#dcdcd6; --accent:#1f6feb; }
  @media (prefers-color-scheme: dark) { :root { --bg:#161614; --surface:#1f1f1c; --text:#ecece8; --faint:#9a9a93; --border:#34342f; --accent:#6ea8ff; } }
  body { margin:0; background:var(--bg); color:var(--text); font:14px/1.5 system-ui, sans-serif; }
  .wrap { max-width:760px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:15px; margin:0 0 8px; }
  .sub { color:var(--faint); margin:0 0 20px; }
  section { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px; margin-bottom:16px; }
  ul { margin:0; padding-left:18px; } a { color:var(--accent); }
</style></head><body><div class="wrap">
<h1>Frictionless Architect</h1>
<p class="sub">The platform's tools, grouped by the role they serve.</p>
__SECTIONS__
</div></body></html>
"""
