"""A mountable settings page and JSON API for detector-category/failure-mode config
(ADR-0034/ADR-0020, research.md R5), mirroring `llm_provider_config.router`'s shape.

Single-user local MVP (ADR-0024): there is no authentication, so bind to localhost.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict

from pii_gateway.config import load_config, resolve_context, save_config
from pii_gateway.detectors import ALL_ENTITIES
from pii_gateway.models import DetectorCategoryConfiguration, ScrubAction


class ContextConfigBody(BaseModel):
    """Body of `PUT {prefix}/contexts/{context_id}` (FR-009)."""

    model_config = ConfigDict(extra="forbid")

    active_categories: list[str]
    failure_mode: ScrubAction


def _describe(context: str, config: DetectorCategoryConfiguration) -> dict[str, Any]:
    return {
        "context": context,
        "active_categories": sorted(config.active_categories),
        "failure_mode": config.failure_mode.value,
    }


def create_settings_router(contexts: Sequence[str], prefix: str = "/settings/pii-gateway") -> APIRouter:
    """Build the settings router for the given registered contexts.

    Args:
        contexts: The caller contexts registered at this feature's scope (e.g.
            `"spec-generator"`, `"governance-eval"`, `"conversational-authoring"`).
        prefix: URL prefix the router is mounted under; also substituted into the
            page script.

    Returns:
        A router serving the HTML page at `prefix` and the JSON API beneath it.
    """
    router = APIRouter(prefix=prefix, tags=["pii-gateway-settings"])
    known = set(contexts)

    @router.get("/state")
    def state() -> dict[str, Any]:
        """Return every registered context's active categories and failure-mode."""
        configs = load_config()
        return {
            "available_categories": sorted(ALL_ENTITIES),
            "contexts": [_describe(context, resolve_context(context, configs)) for context in contexts],
        }

    @router.put("/contexts/{context_id}", responses={404: {"description": "Unknown context."}})
    def put_context(context_id: str, body: ContextConfigBody) -> dict[str, str]:
        """Update one context's active categories / failure-mode (404 if unknown)."""
        if context_id not in known:
            raise HTTPException(status_code=404, detail=f"Unknown context {context_id!r}.")
        configs = load_config()
        configs[context_id] = DetectorCategoryConfiguration(
            context=context_id, active_categories=set(body.active_categories), failure_mode=body.failure_mode
        )
        save_config(configs)
        return {"status": "saved"}

    @router.get("", response_class=HTMLResponse)
    def page() -> str:
        """Serve the settings page."""
        return _PAGE.replace("__PREFIX__", prefix)

    return router


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PII Gateway Settings</title>
<style>
  :root { --bg:#f7f7f5; --surface:#fff; --text:#1c1c1a; --faint:#6b6b66; --border:#dcdcd6; --accent:#1f6feb; --ok:#1a7f37; --err:#b42318; }
  @media (prefers-color-scheme: dark) { :root { --bg:#161614; --surface:#1f1f1c; --text:#ecece8; --faint:#9a9a93; --border:#34342f; --accent:#6ea8ff; --ok:#56d364; --err:#ff8b81; } }
  body { margin:0; background:var(--bg); color:var(--text); font:14px/1.5 system-ui, sans-serif; }
  .wrap { max-width:760px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:15px; margin:0 0 12px; }
  .sub { color:var(--faint); margin:0 0 20px; }
  section { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px; margin-bottom:16px; }
  label { display:flex; align-items:center; gap:6px; font-size:13px; margin:4px 0; }
  select { font:inherit; color:var(--text); background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:6px 8px; }
  button { font:inherit; border:1px solid var(--border); background:var(--surface); color:var(--text); border-radius:6px; padding:6px 12px; cursor:pointer; }
  button.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
  .msg { font-size:12.5px; min-height:1.4em; } .msg.ok { color:var(--ok); } .msg.err { color:var(--err); }
</style></head><body><div class="wrap">
<h1>PII gateway settings</h1>
<p class="sub">Which detector categories are active and what happens on a match, per caller context.</p>
<div id="contexts"></div>
</div>
<script>
(function () {
  const base = "__PREFIX__";
  let available = [];
  const el = (tag, attrs, ...kids) => { const n = document.createElement(tag); Object.assign(n, attrs || {}); kids.forEach(k => n.append(k)); return n; };
  const api = async (method, path, body) => {
    const r = await fetch(base + path, { method, headers: {"Content-Type":"application/json"}, body: body ? JSON.stringify(body) : undefined });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || j));
    return j;
  };
  const say = (node, text, ok) => { node.textContent = text; node.className = "msg " + (ok ? "ok" : "err"); };

  function contextSection(ctx) {
    const msg = el("div", {className:"msg"});
    const checkboxInputs = available.map(cat => {
      const input = el("input", {type:"checkbox", checked: ctx.active_categories.includes(cat)});
      input.dataset.cat = cat;
      return input;
    });
    const boxes = checkboxInputs.map((input, i) => el("label", {}, input, available[i]));
    const mode = el("select", {}, ...["redacted_and_proceeded", "flagged_for_review"].map(m => el("option", {value:m, textContent:m, selected: m === ctx.failure_mode})));
    const save = el("button", {className:"primary", textContent:"Save"});
    save.onclick = async () => {
      try {
        const active_categories = checkboxInputs.filter(i => i.checked).map(i => i.dataset.cat);
        await api("PUT", "/contexts/" + ctx.context, {active_categories, failure_mode: mode.value});
        say(msg, "Saved.", true);
      } catch (e) { say(msg, e.message, false); }
    };
    return el("section", {}, el("h2", {}, ctx.context), ...boxes, el("div", {}, mode, save), msg);
  }

  async function load() {
    const s = await api("GET", "/state");
    available = s.available_categories;
    document.getElementById("contexts").replaceChildren(...s.contexts.map(contextSection));
  }
  load().catch(e => { document.querySelector(".wrap").append(el("div", {className:"msg err", textContent:e.message})); });
})();
</script></body></html>
"""
