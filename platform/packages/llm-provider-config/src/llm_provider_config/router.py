"""A mountable settings page and JSON API for LLM provider configuration (ADR-0034).

Each subsystem UI mounts `create_settings_router(...)` and declares the components that
use an LLM; a future portal can mount the same router. The page edits the global default,
per-component overrides and API keys (written to the OS keychain, never echoed back).
Single-user local MVP (ADR-0024): there is no authentication, so bind to localhost.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from keyring.errors import KeyringError
from litellm import completion
from pydantic import BaseModel, Field

from llm_provider_config.credentials import (
    ENV_VARS,
    MissingCredentialError,
    delete_api_key,
    key_source,
    set_api_key,
)
from llm_provider_config.resolve import resolve_call
from llm_provider_config.settings import LlmSettings, NotConfiguredError, Provider, ProviderSettings
from llm_provider_config.store import default_config_path, load_settings, save_settings


@dataclass(frozen=True)
class Component:
    """A subsystem feature that calls an LLM and can have its own override."""

    id: str
    label: str


class KeyBody(BaseModel):
    api_key: str = Field(min_length=1)


class ConnectionTestBody(BaseModel):
    component: str | None = None


def _describe(settings: ProviderSettings | None) -> dict[str, Any] | None:
    if settings is None:
        return None
    return {
        **settings.model_dump(mode="json", exclude_none=True),
        "key_source": key_source(settings),
    }


def _require_component(known: dict[str, Component], component_id: str) -> None:
    if component_id not in known:
        raise HTTPException(status_code=404, detail=f"Unknown component {component_id!r}.")


def _settings_routes(router: APIRouter, components: Sequence[Component], known: dict[str, Component]) -> None:
    @router.get("/state")
    def state() -> dict[str, Any]:
        settings = load_settings()
        return {
            "config_path": str(default_config_path()),
            "providers": [
                {"id": provider.value, "needs_key": provider is not Provider.OLLAMA, "env_var": ENV_VARS.get(provider)}
                for provider in Provider
            ],
            "default": _describe(settings.default),
            "components": [
                {
                    "id": component.id,
                    "label": component.label,
                    "override": _describe(settings.components.get(component.id)),
                }
                for component in components
            ],
        }

    @router.put("/default")
    def put_default(body: ProviderSettings) -> dict[str, str]:
        settings = load_settings()
        save_settings(LlmSettings(default=body, components=settings.components))
        return {"status": "saved"}

    @router.put("/components/{component_id}")
    def put_override(component_id: str, body: ProviderSettings) -> dict[str, str]:
        _require_component(known, component_id)
        settings = load_settings()
        save_settings(LlmSettings(default=settings.default, components={**settings.components, component_id: body}))
        return {"status": "saved"}

    @router.delete("/components/{component_id}")
    def delete_override(component_id: str) -> dict[str, str]:
        _require_component(known, component_id)
        settings = load_settings()
        remaining = {key: value for key, value in settings.components.items() if key != component_id}
        save_settings(LlmSettings(default=settings.default, components=remaining))
        return {"status": "removed"}


def _key_routes(router: APIRouter) -> None:
    @router.put("/keys/{provider}")
    def put_key(provider: Provider, body: KeyBody) -> dict[str, str]:
        if provider is Provider.OLLAMA:
            raise HTTPException(status_code=422, detail="Ollama does not use an API key.")
        try:
            set_api_key(provider.value, body.api_key)
        except KeyringError as exc:
            env_var = ENV_VARS[provider]
            raise HTTPException(
                status_code=503,
                detail=f"No usable OS keychain here ({exc}). Set {env_var} in the server's environment instead.",
            ) from exc
        return {"status": "stored"}

    @router.delete("/keys/{provider}")
    def remove_key(provider: Provider) -> dict[str, str]:
        try:
            delete_api_key(provider.value)
        except KeyringError as exc:
            raise HTTPException(status_code=404, detail=f"No stored key to remove ({exc}).") from exc
        return {"status": "removed"}


def _test_route(router: APIRouter, known: dict[str, Component]) -> None:
    @router.post("/test")
    def test_connection(body: ConnectionTestBody) -> dict[str, Any]:
        target = body.component or next(iter(known), "")
        if body.component is not None:
            _require_component(known, body.component)
        try:
            call = resolve_call(target)
        except (NotConfiguredError, MissingCredentialError) as exc:
            return {"ok": False, "message": str(exc)}
        try:
            completion(
                messages=[{"role": "user", "content": "Reply with the single word: OK"}],
                max_tokens=16,
                **call.completion_kwargs(),
            )
        except Exception as exc:  # litellm raises many provider-specific error types
            return {"ok": False, "message": f"The call to {call.model} failed: {exc}"}
        return {"ok": True, "message": f"{call.model} responded."}


def create_settings_router(components: Sequence[Component], prefix: str = "/settings/llm") -> APIRouter:
    """Build the settings router for the given LLM-using components."""
    router = APIRouter(prefix=prefix, tags=["llm-settings"])
    known = {component.id: component for component in components}
    _settings_routes(router, components, known)
    _key_routes(router)
    _test_route(router, known)

    @router.get("", response_class=HTMLResponse)
    def page() -> str:
        return _PAGE.replace("__PREFIX__", prefix)

    return router


_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>LLM Settings</title>
<style>
  :root { --bg:#f7f7f5; --surface:#fff; --text:#1c1c1a; --faint:#6b6b66; --border:#dcdcd6; --accent:#1f6feb; --ok:#1a7f37; --err:#b42318; }
  @media (prefers-color-scheme: dark) { :root { --bg:#161614; --surface:#1f1f1c; --text:#ecece8; --faint:#9a9a93; --border:#34342f; --accent:#6ea8ff; --ok:#56d364; --err:#ff8b81; } }
  body { margin:0; background:var(--bg); color:var(--text); font:14px/1.5 system-ui, sans-serif; }
  .wrap { max-width:760px; margin:0 auto; padding:24px 16px 48px; }
  h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:15px; margin:0 0 12px; }
  .sub { color:var(--faint); margin:0 0 20px; }
  section { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:16px; margin-bottom:16px; }
  .row { display:flex; flex-wrap:wrap; gap:10px; align-items:end; margin-bottom:10px; }
  label { display:flex; flex-direction:column; gap:4px; font-size:12px; color:var(--faint); flex:1 1 150px; }
  input, select { font:inherit; color:var(--text); background:var(--bg); border:1px solid var(--border); border-radius:6px; padding:6px 8px; }
  button { font:inherit; border:1px solid var(--border); background:var(--surface); color:var(--text); border-radius:6px; padding:6px 12px; cursor:pointer; }
  button.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
  .msg { font-size:12.5px; min-height:1.4em; } .msg.ok { color:var(--ok); } .msg.err { color:var(--err); }
  .pill { font-size:11.5px; color:var(--faint); } code { font-size:12px; }
</style></head><body><div class="wrap">
<h1>LLM settings</h1>
<p class="sub">Provider and model used for AI features. Stored in <code id="config-path"></code>; API keys go to the OS keychain and are never shown again.</p>
<section id="default-section"><h2>Global default</h2><div id="default-form"></div></section>
<section><h2>API keys</h2><div id="keys"></div></section>
<section><h2>Per-component overrides</h2><p class="sub">An override replaces the global default for one feature.</p><div id="components"></div></section>
</div>
<script>
(function () {
  const base = "__PREFIX__";
  let providers = [];
  const el = (tag, attrs, ...kids) => { const n = document.createElement(tag); Object.assign(n, attrs || {}); kids.forEach(k => n.append(k)); return n; };
  const api = async (method, path, body) => {
    const r = await fetch(base + path, { method, headers: {"Content-Type":"application/json"}, body: body ? JSON.stringify(body) : undefined });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail || j));
    return j;
  };
  const say = (node, text, ok) => { node.textContent = text; node.className = "msg " + (ok ? "ok" : "err"); };

  function settingsForm(current, onSave, onClear, testComponent) {
    const prov = el("select"); providers.forEach(p => prov.append(el("option", {value:p.id, textContent:p.id})));
    const model = el("input", {placeholder:"e.g. gemma4:12b"});
    const base_ = el("input", {placeholder:"optional, e.g. http://localhost:11434"});
    const params = el("input", {placeholder:'{"temperature": 0}'});
    if (current) { prov.value = current.provider; model.value = current.model; base_.value = current.api_base || ""; params.value = JSON.stringify(current.params || {}); }
    else params.value = "{}";
    const msg = el("div", {className:"msg"});
    const save = el("button", {className:"primary", textContent:"Save"});
    save.onclick = async () => {
      try {
        const body = {provider:prov.value, model:model.value, params:JSON.parse(params.value || "{}")};
        if (base_.value) body.api_base = base_.value;
        await onSave(body); say(msg, "Saved.", true); load();
      } catch (e) { say(msg, e.message, false); }
    };
    const test = el("button", {textContent:"Test connection"});
    test.onclick = async () => {
      say(msg, "Testing\\u2026", true);
      try { const r = await api("POST", "/test", {component: testComponent}); say(msg, r.message, r.ok); }
      catch (e) { say(msg, e.message, false); }
    };
    const row = el("div", {className:"row"},
      el("label", {}, "Provider", prov), el("label", {}, "Model", model),
      el("label", {}, "API base", base_), el("label", {}, "Params (JSON)", params));
    const actions = el("div", {className:"row"}, save, test);
    if (onClear) { const clear = el("button", {textContent:"Use default"}); clear.onclick = async () => { await onClear(); load(); }; actions.append(clear); }
    return el("div", {}, row, actions, msg);
  }

  async function load() {
    const s = await api("GET", "/state");
    providers = s.providers;
    document.getElementById("config-path").textContent = s.config_path;
    const def = document.getElementById("default-form"); def.replaceChildren(
      settingsForm(s.default, b => api("PUT", "/default", b), null, null));

    const keys = document.getElementById("keys"); keys.replaceChildren();
    s.providers.filter(p => p.needs_key).forEach(p => {
      const input = el("input", {type:"password", placeholder:"paste key to store in keychain", autocomplete:"off"});
      const msg = el("div", {className:"msg"});
      const store = el("button", {textContent:"Store"});
      store.onclick = async () => {
        try { await api("PUT", "/keys/" + p.id, {api_key: input.value}); input.value = ""; say(msg, "Stored in keychain.", true); load(); }
        catch (e) { say(msg, e.message, false); }
      };
      const remove = el("button", {textContent:"Remove"});
      remove.onclick = async () => { try { await api("DELETE", "/keys/" + p.id); say(msg, "Removed.", true); load(); } catch (e) { say(msg, e.message, false); } };
      keys.append(el("div", {className:"row"}, el("label", {}, p.id + " key", input), store, remove), msg);
      const cfg = [s.default, ...s.components.map(c => c.override)].filter(x => x && x.provider === p.id)[0];
      if (cfg) keys.append(el("div", {className:"pill"}, "Currently resolved from: " + cfg.key_source));
      else keys.append(el("div", {className:"pill"}, "env fallback: " + p.env_var));
    });

    const comps = document.getElementById("components"); comps.replaceChildren();
    s.components.forEach(c => {
      comps.append(el("h2", {}, c.label, " ", el("span", {className:"pill"}, c.override ? "override" : "inherits default")));
      comps.append(el("div", {className:"pill"}, c.id));
      comps.append(settingsForm(c.override, b => api("PUT", "/components/" + c.id, b),
        c.override ? () => api("DELETE", "/components/" + c.id) : null, c.id));
    });
  }
  load().catch(e => { document.querySelector(".wrap").append(el("div", {className:"msg err", textContent:e.message})); });
})();
</script></body></html>
"""
