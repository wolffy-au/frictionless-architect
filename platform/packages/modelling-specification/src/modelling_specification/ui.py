"""Split-screen conversational authoring UI (GH #108, R15-R19): a self-contained
`GET /authoring/` page, mirroring `controls_compliance_catalog.playground.api`'s
`_PAGE_TEMPLATE`/`_PAGE` module-level-string pattern -- no Jinja2, no static-asset
pipeline, no JS framework build step. A plain fetch() client over the existing
`sessions`/`propose`/`decide`/`render`/`config` JSON contract (contracts/api.md);
`session_id`/`delta_id` live in page-scoped JS state only (R16), nothing new
server-side.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/authoring", tags=["authoring-ui"])

_PAGE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Conversational Model Authoring</title>
<style>
  :root {
    --bg:#F7F6F2; --surface:#FFFFFF; --surface-2:#F0EFE9; --border:#DDDAD1;
    --text:#1E1C18; --text-muted:#726F63;
    --accent:#1F6F5C; --accent-soft:#E3F1EC;
    --err:#B3432E; --err-soft:#FBEAE5;
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg:#17161B; --surface:#1E1D23; --surface-2:#26252C; --border:#36343D;
      --text:#EDEBE6; --text-muted:#A6A398;
      --accent:#4FC9A8; --accent-soft:#1D3833;
      --err:#E68A73; --err-soft:#3A2420;
      color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --bg:#17161B; --surface:#1E1D23; --surface-2:#26252C; --border:#36343D;
    --text:#EDEBE6; --text-muted:#A6A398;
    --accent:#4FC9A8; --accent-soft:#1D3833;
    --err:#E68A73; --err-soft:#3A2420;
    color-scheme: dark;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: system-ui, sans-serif; padding: 20px;
  }
  .wrap { max-width: 1180px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
  h1 { font-size: 20px; margin: 0; }
  .sub { color: var(--text-muted); font-size: 13px; margin: 4px 0 0; }
  .panel {
    background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
    overflow: hidden;
  }
  .panel-head {
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
    padding: 10px 14px; border-bottom: 1px solid var(--border); background: var(--surface-2);
    font-size: 13px; font-weight: 600;
  }
  .head-actions { display: flex; align-items: center; gap: 16px; }
  .head-actions a { color: var(--accent); font-weight: 400; font-size: 12.5px; }
  .panel-head label { font-weight: 400; font-size: 12.5px; display: flex; align-items: center; gap: 6px; }
  #messages { padding: 12px 14px; max-height: 320px; overflow-y: auto; display: flex; flex-direction: column; gap: 10px; }
  .msg { font-size: 13px; line-height: 1.5; }
  .msg.user { color: var(--text-muted); }
  .finding, .duplicate, .pattern { border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; margin-top: 6px; background: var(--surface-2); }
  .finding { border-color: var(--err); background: var(--err-soft); }
  .actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
  button { font: inherit; font-size: 12.5px; padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
  button:hover { background: var(--surface-2); }
  button:disabled { opacity: .5; cursor: default; }
  button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
  .composer { display: flex; gap: 8px; padding: 10px 14px; border-top: 1px solid var(--border); }
  textarea, input[type=text] { font: inherit; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; background: var(--bg); color: var(--text); }
  #chat-input { flex: 1; min-height: 44px; resize: vertical; }
  .state-row { display: flex; gap: 8px; align-items: center; padding: 10px 14px; border-top: 1px solid var(--border); }
  select { font: inherit; font-size: 13px; padding: 7px 10px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--text); }
  #render-pane { height: 70vh; min-height: 320px; overflow: hidden; position: relative; cursor: grab; touch-action: none; background: #fff; user-select: none; -webkit-user-select: none; }
  #render-pane.panning { cursor: grabbing; }
  #render-canvas { position: absolute; top: 0; left: 0; transform-origin: 0 0; will-change: transform; }
  #render-canvas svg { display: block; max-width: none; }
  .zoom-controls { display: flex; gap: 6px; align-items: center; }
  .zoom-controls button { padding: 4px 9px; }
  #zoom-level { font-size: 12px; color: var(--text-muted); min-width: 44px; text-align: right; }
  .show-row { display: flex; gap: 8px; align-items: center; }
  .error { color: var(--err); font-size: 12.5px; }
  #render-banner:not(:empty) { padding: 8px 14px; background: var(--accent-soft); color: var(--accent); font-size: 12.5px; font-weight: 600; border-bottom: 1px solid var(--border); }
  #render-status { padding: 0 14px; }
  #render-status:not(:empty) { padding: 8px 14px; border-bottom: 1px solid var(--border); }
  #view-select { max-width: 480px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Conversational Model Authoring</h1>
    <p class="sub">Describe a change in plain language; review what the agent proposes before anything is written.</p>
  </header>

  <section class="panel">
    <div class="panel-head">
      <span>Chat</span>
      <span class="head-actions">
        <a href="/settings/llm" target="_blank" rel="noopener">LLM settings</a>
        <label><input type="checkbox" id="auto-render-toggle" disabled> Auto-render on apply</label>
      </span>
    </div>
    <div id="messages"></div>
    <div class="state-row">
      <button id="apply" class="primary" disabled>Apply</button>
    </div>
    <div class="composer">
      <textarea id="chat-input" placeholder="e.g. add an application function for X, served to the EA role (Enter to send, Shift+Enter for a new line)"></textarea>
      <button id="send" class="primary" type="button">Send</button>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <span>Render</span>
      <div class="show-row">
        <select id="view-select" disabled><option value="" selected disabled>Choose a view&hellip;</option></select>
      </div>
    </div>
    <div id="render-banner"></div>
    <div id="render-status" class="error"></div>
    <div class="state-row zoom-controls">
      <button id="zoom-out" type="button" title="Zoom out">&minus;</button>
      <button id="zoom-in" type="button" title="Zoom in">+</button>
      <button id="zoom-fit" type="button" title="Fit the whole diagram in the pane">Fit</button>
      <button id="zoom-fit-width" type="button" title="Fit the diagram to the pane width">Fit width</button>
      <button id="zoom-100" type="button" title="Actual size">100%</button>
      <span id="zoom-level"></span>
      <span class="sub">Scroll to zoom, drag to pan, double-click to fit.</span>
    </div>
    <div id="render-pane"><div id="render-canvas"></div></div>
  </section>
</div>
<script>
(function () {
  "use strict";

  // Per-browser preferences, restored on load. Storage can be blocked or throw, so
  // every access is guarded and the page works fine without it.
  const prefs = {
    get(key) { try { return window.localStorage.getItem("authoring." + key); } catch (e) { return null; } },
    set(key, value) { try { window.localStorage.setItem("authoring." + key, value); } catch (e) { /* ignore */ } },
  };

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  let sessionId = null;
  let currentDeltaId = null;
  let currentDeltaValidated = false;
  let currentElements = [];
  let currentRelationships = [];
  let autoRenderEnabled = false;

  const messagesEl = document.getElementById("messages");
  const renderBanner = document.getElementById("render-banner");
  const applyButton = document.getElementById("apply");
  const chatInput = document.getElementById("chat-input");
  const sendButton = document.getElementById("send");
  const autoRenderToggle = document.getElementById("auto-render-toggle");
  const viewSelect = document.getElementById("view-select");
  const renderStatus = document.getElementById("render-status");
  const renderPane = document.getElementById("render-pane");
  const renderCanvas = document.getElementById("render-canvas");
  const zoomLevel = document.getElementById("zoom-level");

  function addMessage(role, html) {
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.innerHTML = html;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  // Apply needs a validated delta; nothing is written until it is clicked.
  function updateApplyButton() {
    applyButton.disabled = !currentDeltaValidated;
  }

  async function decide(deltaId, body) {
    const response = await fetch(
      "/authoring/sessions/" + sessionId + "/deltas/" + deltaId + "/decide",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    );
    const result = await response.json();
    if (!response.ok) {
      addMessage("agent", '<span class="error">' + escapeHtml(result.detail || "That decision could not be applied.") + "</span>");
      return null;
    }
    return result;
  }

  function firstAffectedObjectId(elements, relationships) {
    if (elements && elements.length) return elements[0].id;
    if (relationships && relationships.length) return relationships[0].target;
    return null;
  }

  async function maybeAutoRender(elements, relationships) {
    if (!autoRenderEnabled) return;
    const objectId = firstAffectedObjectId(elements, relationships);
    if (!objectId) return;
    await showRender({ object_id: objectId });
  }

  // The view on screen, kept in sync from the server's X-View-Id header.
  let currentViewId = null;

  async function showRender(params) {
    renderStatus.textContent = "";
    const query = new URLSearchParams({ ...params, format: "svg" });
    const response = await fetch("/authoring/render?" + query.toString());
    if (response.status === 300) {
      const body = await response.json();
      const candidates = body.ambiguous_candidates || [];
      // An element that sits in several views: keep the one already on screen.
      if (currentViewId && candidates.includes(currentViewId)) {
        return showRender({ object_id: currentViewId });
      }
      renderStatus.textContent = "Which view did you mean? Pick one above: " + candidates.join(", ");
      return;
    }
    if (!response.ok) {
      renderStatus.textContent = "No view resolves from that.";
      return;
    }
    renderBanner.textContent = "";
    currentViewId = response.headers.get("X-View-Id");
    if (currentViewId) {
      viewSelect.value = currentViewId;
      prefs.set("view", currentViewId);
    }
    renderCanvas.innerHTML = await response.text();
    loadDiagram();
  }

  // Pan/zoom: one transform (translate + scale) on the canvas around the inlined <svg>.
  const view = { scale: 1, x: 0, y: 0, w: 0, h: 0 };
  const MIN_SCALE = 0.02, MAX_SCALE = 16;

  function applyView() {
    renderCanvas.style.transform = "translate(" + view.x + "px," + view.y + "px) scale(" + view.scale + ")";
    zoomLevel.textContent = view.w ? Math.round(view.scale * 100) + "%" : "";
  }

  function loadDiagram() {
    const svg = renderCanvas.querySelector("svg");
    if (!svg) { view.w = view.h = 0; applyView(); return; }
    renderCanvas.style.transform = "none";
    svg.style.width = svg.style.height = "";
    const box = svg.getBoundingClientRect();
    view.w = box.width || 300;
    view.h = box.height || 150;
    svg.style.width = view.w + "px";
    svg.style.height = view.h + "px";
    fitDiagram(false);
  }

  function centre() {
    view.x = (renderPane.clientWidth - view.w * view.scale) / 2;
    view.y = (renderPane.clientHeight - view.h * view.scale) / 2;
  }

  function fitDiagram(widthOnly) {
    if (!view.w) return;
    const pad = 16;
    const sw = (renderPane.clientWidth - pad) / view.w;
    const sh = (renderPane.clientHeight - pad) / view.h;
    view.scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, widthOnly ? sw : Math.min(sw, sh)));
    centre();
    if (widthOnly) view.y = pad / 2;
    applyView();
  }

  function zoomAt(factor, cx, cy) {
    if (!view.w) return;
    const next = Math.min(MAX_SCALE, Math.max(MIN_SCALE, view.scale * factor));
    const k = next / view.scale;
    view.x = cx - (cx - view.x) * k;
    view.y = cy - (cy - view.y) * k;
    view.scale = next;
    applyView();
  }

  function zoomCentre(factor) {
    zoomAt(factor, renderPane.clientWidth / 2, renderPane.clientHeight / 2);
  }

  renderPane.addEventListener("wheel", (event) => {
    event.preventDefault();
    const rect = renderPane.getBoundingClientRect();
    zoomAt(Math.exp(-event.deltaY * 0.0015), event.clientX - rect.left, event.clientY - rect.top);
  }, { passive: false });

  let drag = null;
  renderPane.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || !view.w) return;
    drag = { px: event.clientX, py: event.clientY, x: view.x, y: view.y };
    renderPane.setPointerCapture(event.pointerId);
    renderPane.classList.add("panning");
  });
  renderPane.addEventListener("pointermove", (event) => {
    if (!drag) return;
    view.x = drag.x + event.clientX - drag.px;
    view.y = drag.y + event.clientY - drag.py;
    applyView();
  });
  const endDrag = () => { drag = null; renderPane.classList.remove("panning"); };
  renderPane.addEventListener("pointerup", endDrag);
  renderPane.addEventListener("pointercancel", endDrag);
  renderPane.addEventListener("dblclick", () => fitDiagram(false));
  window.addEventListener("resize", () => { if (view.w) fitDiagram(false); });

  document.getElementById("zoom-in").addEventListener("click", () => zoomCentre(1.25));
  document.getElementById("zoom-out").addEventListener("click", () => zoomCentre(0.8));
  document.getElementById("zoom-fit").addEventListener("click", () => fitDiagram(false));
  document.getElementById("zoom-fit-width").addEventListener("click", () => fitDiagram(true));
  document.getElementById("zoom-100").addEventListener("click", () => {
    if (!view.w) return;
    view.scale = 1;
    centre();
    applyView();
  });

  function renderDecisionResult(result) {
    if (!result) return;
    addMessage("agent", "Applied to the model."
      + (result.override_decision_id ? " Recorded as override decision " + escapeHtml(result.override_decision_id) + "." : ""));
  }

  // Render the delta as it would look, in memory -- nothing is written until Apply.
  async function showPreview() {
    if (!currentDeltaId) return;
    renderStatus.textContent = "";
    const params = new URLSearchParams();
    if (viewSelect.value) params.set("view_id", viewSelect.value);
    const response = await fetch(
      "/authoring/sessions/" + sessionId + "/deltas/" + currentDeltaId + "/preview?" + params.toString());
    if (response.status === 300 || response.status === 404) {
      renderStatus.textContent = "Choose a view above to preview this change in.";
      return;
    }
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      renderStatus.textContent = body.detail || "This change cannot be previewed.";
      return;
    }
    currentViewId = response.headers.get("X-View-Id");
    if (currentViewId) { viewSelect.value = currentViewId; prefs.set("view", currentViewId); }
    renderCanvas.innerHTML = await response.text();
    renderBanner.textContent = "Preview \u2014 not written yet. New elements are marked +. Click Apply to write this to the model.";
    loadDiagram();
  }

  // After a change is written (or discarded), show the model as it now is.
  async function afterDecision(applied, elements, relationships) {
    renderBanner.textContent = "";
    if (viewSelect.value) await showRender({ object_id: viewSelect.value });
    else if (applied) await maybeAutoRender(elements, relationships);
  }

  function resetPendingDelta() {
    currentDeltaId = null;
    currentDeltaValidated = false;
    currentElements = [];
    currentRelationships = [];
    updateApplyButton();
  }

  function renderFindings(body) {
    const parts = [];
    const validation = body.validation_result;
    if (validation && !validation.clean) {
      for (const finding of validation.findings) {
        parts.push(
          '<div class="finding">' + escapeHtml(finding.detail)
          + (finding.proposed_fix ? "<br><i>Suggested fix: " + escapeHtml(finding.proposed_fix) + "</i>" : "")
          + "</div>"
        );
      }
      parts.push(
        '<div class="actions">'
        + '<button data-action="reject">Reject</button>'
        + '<button data-action="override">Override</button>'
        + "</div>"
      );
    }
    for (const dup of body.duplicates || []) {
      parts.push(
        '<div class="duplicate">Looks like a duplicate of <b>' + escapeHtml(dup.existing_element_id)
        + "</b> (matched on " + escapeHtml(dup.matched_fields.join(", ")) + ')'
        + '<div class="actions">'
        + '<button data-action="keep-both">Keep both</button>'
        + '<button data-action="merge" data-target="' + escapeHtml(dup.existing_element_id) + '">Merge</button>'
        + '<button data-action="reject">Reject</button>'
        + '<button data-action="override">Override</button>'
        + "</div></div>"
      );
    }
    for (const pattern of body.pattern_suggestions || []) {
      parts.push(
        '<div class="pattern">An established pattern uses an intermediary '
        + escapeHtml((pattern.established_pattern.intermediary_types || []).join(", ")) + " here."
        + '<div class="actions">'
        + '<button data-action="accept-pattern">Accept pattern</button>'
        + '<button data-action="keep-direct">Keep direct</button>'
        + '<button data-action="override">Override</button>'
        + "</div></div>"
      );
    }
    return parts.join("");
  }

  function wireDecisionButtons(container, deltaId) {
    container.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", async () => {
        const action = button.dataset.action;
        const body = { action };
        if (action === "merge") {
          body.duplicate_decision = "merge";
          body.target_existing_id = button.dataset.target;
        }
        if (action === "override") {
          const rationale = window.prompt("Optional rationale for overriding this objection:", "");
          if (rationale) body.rationale = rationale;
        }
        const result = await decide(deltaId, body);
        if (action === "reject") {
          if (result) addMessage("agent", "Discarded.");
          resetPendingDelta();
          await afterDecision(false, [], []);
          return;
        }
        renderDecisionResult(result);
        if (result && result.status === "applied") {
          const [els, rels] = [currentElements, currentRelationships];
          resetPendingDelta();
          await afterDecision(true, els, rels);
        }
      });
    });
  }

  function renderProposeResponse(body) {
    const notes = (body.notes || []).map((n) => '<div class="finding">Corrected: ' + escapeHtml(n) + "</div>").join("");
    const empty = !(body.elements || []).length && !(body.relationships || []).length;
    const findingsHtml = notes + renderFindings(body);
    const div = addMessage("agent", findingsHtml
      || "Looks good -- no objections. Nothing is written until you click Apply.");
    wireDecisionButtons(div, body.delta_id);
    currentDeltaId = body.delta_id;
    currentDeltaValidated = body.status === "validated" && !empty;
    currentElements = body.elements || [];
    currentRelationships = body.relationships || [];
    updateApplyButton();
    if (!empty) showPreview();
    return body;
  }

  async function initSession() {
    const response = await fetch("/authoring/sessions", { method: "POST" });
    const body = await response.json();
    sessionId = body.session_id;
  }

  async function initConfig() {
    const response = await fetch("/authoring/config");
    const body = await response.json();
    autoRenderEnabled = !!body.auto_render;
    autoRenderToggle.checked = autoRenderEnabled;
    const savedAutoRender = prefs.get("autoRender");
    if (savedAutoRender !== null && (savedAutoRender === "true") !== autoRenderEnabled) {
      autoRenderEnabled = savedAutoRender === "true";
      autoRenderToggle.checked = autoRenderEnabled;
      await fetch("/authoring/config", {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ auto_render: autoRenderEnabled }),
      });
    }
    // Enabled only once loaded, so a toggle can never race the initial GET and
    // get silently reverted by it (the checkbox starts `disabled` in markup;
    // Playwright/user interaction waits for actionability, i.e. this).
    autoRenderToggle.disabled = false;
  }

  // The server's session store is in memory, so a restart (e.g. uvicorn --reload)
  // forgets the page's session; start a fresh one and retry once.
  async function postPropose(request) {
    const send = () => fetch("/authoring/sessions/" + sessionId + "/propose", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request: request }),
    });
    let response = await send();
    if (response.status === 404) {
      await initSession();
      response = await send();
    }
    return response;
  }

  async function sendRequest() {
    const request = chatInput.value.trim();
    if (!request || sendButton.disabled) return;
    addMessage("user", escapeHtml(request));
    chatInput.value = "";
    sendButton.disabled = true;
    try {
      const response = await postPropose(request);
      const body = await response.json();
      if (!response.ok) {
        addMessage("agent", '<span class="error">' + escapeHtml(body.detail || "Could not propose a change from that.") + "</span>");
        return;
      }
      renderProposeResponse(body);
    } finally {
      sendButton.disabled = false;
    }
  }

  sendButton.addEventListener("click", sendRequest);
  chatInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      sendRequest();
    }
  });

  applyButton.addEventListener("click", async () => {
    if (!currentDeltaId) return;
    const result = await decide(currentDeltaId, { action: "apply" });
    renderDecisionResult(result);
    if (result && result.status === "applied") {
      const [els, rels] = [currentElements, currentRelationships];
      resetPendingDelta();
      await afterDecision(true, els, rels);
    }
  });

  autoRenderToggle.addEventListener("change", async () => {
    autoRenderEnabled = autoRenderToggle.checked;
    prefs.set("autoRender", autoRenderEnabled);
    await fetch("/authoring/config", {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ auto_render: autoRenderEnabled }),
    });
  });

  async function showSelectedView() {
    if (!viewSelect.value) return;
    if (currentDeltaId) await showPreview();
    else await showRender({ object_id: viewSelect.value });
  }

  viewSelect.addEventListener("change", showSelectedView);

  async function initViews() {
    const response = await fetch("/authoring/views");
    const views = await response.json();
    for (const view of views) {
      const option = document.createElement("option");
      option.value = view.id;
      option.textContent = view.name;
      viewSelect.appendChild(option);
    }
    viewSelect.disabled = false;
    const savedView = prefs.get("view");
    if (savedView && [...viewSelect.options].some((o) => o.value === savedView)) {
      viewSelect.value = savedView;
      await showSelectedView();
    }
  }

  (async function init() {
    await initSession();
    await initConfig();
    await initViews();
  })();
})();
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def authoring_page() -> str:
    return _PAGE
