"""Split-screen conversational authoring UI (GH #108, R15-R19): a self-contained
`GET /authoring/` page, mirroring `controls_compliance_catalog.playground.api`'s
`_PAGE_TEMPLATE`/`_PAGE` module-level-string pattern -- no Jinja2, no static-asset
pipeline, no JS framework build step. A plain fetch() client over the existing
`sessions`/`propose`/`propose/select`/`propose/resolve-pii`/`decide`/`render`/`config`
JSON contract (contracts/api.md); `session_id`/`delta_id` live in page-scoped JS state
only (R16), nothing new server-side. `renderProposeResponse` branches on `propose`'s
`status`: a `"message"` -- the LLM's free-text reply, which may be Markdown and is
rendered as sanitised HTML via `renderMarkdown`, never inserted as raw HTML (GH #185) --
a set of `"options"` to pick from via `propose/select` (ADR-0041), a PII/PHI match
flagged for review via `propose/resolve-pii` (`"pii_review_required"`, ADR-0014
amendment), or the single-delta validated/flagged path, which lists every kind of
proposed change in the chat and previews it (FR-012a).
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
  .msg.agent p, .msg.agent ul, .msg.agent ol, .msg.agent pre, .msg.agent h1, .msg.agent h2, .msg.agent h3 { margin: 0 0 8px; }
  .msg.agent > :last-child { margin-bottom: 0; }
  .msg.agent ul, .msg.agent ol { padding-left: 20px; }
  .msg.agent h1, .msg.agent h2, .msg.agent h3 { font-size: 1.05em; }
  .msg.agent code { background: var(--surface-2); border-radius: 4px; padding: 1px 4px; font-size: .95em; }
  .msg.agent pre { background: var(--surface-2); border-radius: 6px; padding: 8px 10px; overflow-x: auto; }
  .msg.agent pre code { background: none; padding: 0; }
  .msg.agent a { color: var(--accent); }
  .finding, .duplicate, .pattern, .option, .pii { border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; margin-top: 6px; background: var(--surface-2); }
  .finding { border-color: var(--err); background: var(--err-soft); }
  .option .sub { margin: 4px 0 0; }
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
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Minimal, dependency-free Markdown -> sanitised HTML (GH #185), safe over untrusted
  // LLM text: every line is escaped via escapeHtml before any markup is layered on, so
  // syntax this doesn't recognise -- including a literal "<script>" in the model's own
  // reply -- renders as text rather than live DOM. Only this fixed, allowlisted set of
  // tags is ever emitted: headings, paragraphs, lists, code (inline/fenced), bold,
  // italic, and http(s)/mailto links. Self-contained (only escapeHtml as a dependency)
  // so another package's chat/LLM UI can copy it as-is, per the issue's suggestion of a
  // shared rendering helper.
  function renderMarkdown(text) {
    const LINK_SCHEME = /^(https?:|mailto:)/i;

    function renderInline(raw) {
      let out = escapeHtml(raw);
      out = out.replace(/`([^`]+)`/g, (_, code) => "<code>" + code + "</code>");
      out = out.replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>");
      out = out.replace(/\\*([^*\\s][^*]*?)\\*/g, "<em>$1</em>");
      out = out.replace(/_([^_\\s][^_]*?)_/g, "<em>$1</em>");
      out = out.replace(/\\[([^\\]]+)\\]\\(([^)\\s]+)\\)/g, (match, label, url) =>
        LINK_SCHEME.test(url)
          ? '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + label + "</a>"
          : match);
      return out;
    }

    const lines = String(text).replace(/\\r\\n/g, "\\n").split("\\n");
    const blocks = [];
    let paragraph = [];
    const flushParagraph = () => {
      if (paragraph.length) {
        blocks.push("<p>" + paragraph.join("<br>") + "</p>");
        paragraph = [];
      }
    };

    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      if (/^```/.test(line)) {
        flushParagraph();
        const codeLines = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) {
          codeLines.push(escapeHtml(lines[i]));
          i++;
        }
        i++; // skip the closing fence, if any
        blocks.push("<pre><code>" + codeLines.join("\\n") + "</code></pre>");
        continue;
      }
      const heading = line.match(/^(#{1,6})\\s+(.+)$/);
      if (heading) {
        flushParagraph();
        const level = heading[1].length;
        blocks.push("<h" + level + ">" + renderInline(heading[2]) + "</h" + level + ">");
        i++;
        continue;
      }
      if (/^[-*]\\s+/.test(line)) {
        flushParagraph();
        const items = [];
        while (i < lines.length && /^[-*]\\s+/.test(lines[i])) {
          items.push("<li>" + renderInline(lines[i].replace(/^[-*]\\s+/, "")) + "</li>");
          i++;
        }
        blocks.push("<ul>" + items.join("") + "</ul>");
        continue;
      }
      if (/^\\d+\\.\\s+/.test(line)) {
        flushParagraph();
        const items = [];
        while (i < lines.length && /^\\d+\\.\\s+/.test(lines[i])) {
          items.push("<li>" + renderInline(lines[i].replace(/^\\d+\\.\\s+/, "")) + "</li>");
          i++;
        }
        blocks.push("<ol>" + items.join("") + "</ol>");
        continue;
      }
      if (line.trim() === "") {
        flushParagraph();
        i++;
        continue;
      }
      paragraph.push(renderInline(line));
      i++;
    }
    flushParagraph();
    return blocks.join("");
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
    renderBanner.textContent = "Preview \u2014 not written yet. New elements are marked +, renamed ones ~. Click Apply to write this to the model.";
    loadDiagram();
  }

  // A view the delta proposes isn't in the picker until it is written, but the
  // preview still has to select it.
  function ensureViewOption(viewId, name) {
    if ([...viewSelect.options].some((o) => o.value === viewId)) return;
    const option = document.createElement("option");
    option.value = viewId;
    option.textContent = (name || viewId) + " (proposed)";
    option.dataset.proposed = "true";
    viewSelect.appendChild(option);
  }

  // Applied, a proposed view becomes an ordinary one; discarded, it goes -- along
  // with its preview, since there is no such view left to show instead.
  function settleProposedViews(applied) {
    for (const option of [...viewSelect.options]) {
      if (!option.dataset.proposed) continue;
      if (applied) {
        option.textContent = option.textContent.replace(/ \\(proposed\\)$/, "");
        delete option.dataset.proposed;
      } else {
        if (viewSelect.value === option.value) {
          viewSelect.value = "";
          renderCanvas.innerHTML = "";
          loadDiagram();
        }
        option.remove();
      }
    }
  }

  // A delta that is about a particular view is previewed in that view, whichever one
  // happens to be selected.
  function selectDeltaView(body) {
    const proposed = (body.views || []).at(-1);
    const edited = (body.view_membership_edits || []).at(-1);
    if (proposed) ensureViewOption(proposed.id, proposed.name);
    const viewId = proposed ? proposed.id : edited && edited.view_id;
    if (viewId) viewSelect.value = viewId;
  }

  // After a change is written (or discarded), show the model as it now is.
  async function afterDecision(applied, elements, relationships) {
    renderBanner.textContent = "";
    settleProposedViews(applied);
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

  function describeElements(elements) {
    return (elements || []).map((e) => escapeHtml((e.name || e.id) + " (" + e.type + ")")).join(", ");
  }

  function describeRelationships(relationships, elements) {
    const names = {};
    for (const e of elements || []) if (e.id) names[e.id] = e.name || e.id;
    return (relationships || []).map((r) => {
      const source = names[r.source] || r.source;
      const target = names[r.target] || r.target;
      return escapeHtml(r.type + ": " + source + " -> " + target + (r.label ? " (" + r.label + ")" : ""));
    }).join(", ");
  }

  function describeMembershipEdits(edits) {
    return (edits || []).map((edit) => {
      const changes = [
        ...(edit.add || []).map((id) => "+" + id),
        ...(edit.remove || []).map((id) => "-" + id),
      ];
      return escapeHtml(edit.view_id + ": " + changes.join(", "));
    }).join("; ");
  }

  function describeViews(views) {
    return (views || []).map((v) => escapeHtml(v.name || v.id)).join(", ");
  }

  function describeRenames(edits) {
    return (edits || []).map((e) => escapeHtml(e.id + " -> " + e.name)).join(", ");
  }

  const DELTA_PARTS = [
    ["Adds", "elements", (body) => describeElements(body.elements)],
    ["Relationships", "relationships", (body) => describeRelationships(body.relationships, body.elements)],
    ["New views", "views", (body) => describeViews(body.views)],
    ["View membership", "view_membership_edits", (body) => describeMembershipEdits(body.view_membership_edits)],
    ["Renames", "element_edits", (body) => describeRenames(body.element_edits)],
    ["Removes elements", "element_removals", (body) => escapeHtml((body.element_removals || []).join(", "))],
    ["Removes relationships", "relationship_removals",
      (body) => describeRelationships(body.relationship_removals, [])],
  ];

  function deltaHasChanges(body) {
    return DELTA_PARTS.some(([, key]) => (body[key] || []).length);
  }

  // Everything the pending delta would change, whatever its kind.
  function describeProposal(body) {
    const lines = DELTA_PARTS
      .filter(([, key]) => (body[key] || []).length)
      .map(([label, , describe]) => '<div class="sub">' + label + ": " + describe(body) + "</div>");
    return lines.length ? "<div>Proposed so far:</div>" + lines.join("") : "";
  }

  // Read-only version of renderFindings for an as-yet-unpicked option: shows what
  // picking it would flag, without reject/override actions -- there is no delta to
  // act on until `propose/select` turns this option into one.
  function renderOptionCaveats(option) {
    const parts = [];
    const notes = (option.notes || []).map((n) => '<div class="finding">Corrected: ' + escapeHtml(n) + "</div>");
    parts.push(...notes);
    const validation = option.validation_result;
    if (validation && !validation.clean) {
      for (const finding of validation.findings) {
        parts.push(
          '<div class="finding">' + escapeHtml(finding.detail)
          + (finding.proposed_fix ? "<br><i>Suggested fix: " + escapeHtml(finding.proposed_fix) + "</i>" : "")
          + "</div>"
        );
      }
    }
    for (const dup of option.duplicates || []) {
      parts.push(
        '<div class="duplicate">Looks like a duplicate of <b>' + escapeHtml(dup.existing_element_id)
        + "</b> (matched on " + escapeHtml(dup.matched_fields.join(", ")) + ")</div>"
      );
    }
    for (const pattern of option.pattern_suggestions || []) {
      parts.push(
        '<div class="pattern">An established pattern uses an intermediary '
        + escapeHtml((pattern.established_pattern.intermediary_types || []).join(", ")) + " here.</div>"
      );
    }
    return parts.join("");
  }

  async function selectOption(index) {
    const response = await fetch(
      "/authoring/sessions/" + sessionId + "/propose/select",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ option_index: index }) }
    );
    const result = await response.json();
    if (!response.ok) {
      addMessage("agent", '<span class="error">' + escapeHtml(result.detail || "That option could not be picked.") + "</span>");
      return null;
    }
    return result;
  }

  // The architect asked for a way forward rather than describing one concrete
  // change (FR-001 "ways forward", GH #68): show each candidate with its rationale
  // so they can pick one via `propose/select`, which turns it into a normal delta.
  function renderOptions(body) {
    const blocks = (body.options || []).map((option, index) => {
      const elementsDesc = describeElements(option.elements);
      const relationshipsDesc = describeRelationships(option.relationships, option.elements);
      return (
        '<div class="option">'
        + "<div>" + escapeHtml(option.rationale) + "</div>"
        + (option.convention_refs && option.convention_refs.length
            ? '<div class="sub">Grounded in: ' + escapeHtml(option.convention_refs.join(", ")) + "</div>" : "")
        + (elementsDesc ? '<div class="sub">Adds: ' + elementsDesc + "</div>" : "")
        + (relationshipsDesc ? '<div class="sub">Relationships: ' + relationshipsDesc + "</div>" : "")
        + renderOptionCaveats(option)
        + '<div class="actions"><button data-option-index="' + index + '">Pick this option</button></div>'
        + "</div>"
      );
    });
    const div = addMessage("agent", "Here are some ways forward:" + blocks.join(""));
    div.querySelectorAll("button[data-option-index]").forEach((button) => {
      button.addEventListener("click", async () => {
        div.querySelectorAll("button[data-option-index]").forEach((b) => { b.disabled = true; });
        const result = await selectOption(Number(button.dataset.optionIndex));
        if (result) renderProposeResponse(result);
      });
    });
  }

  async function resolvePii(resolution, editedText) {
    const body = { resolution };
    if (editedText !== undefined) body.edited_text = editedText;
    const response = await fetch(
      "/authoring/sessions/" + sessionId + "/propose/resolve-pii",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    );
    const result = await response.json();
    if (!response.ok) {
      addMessage("agent", '<span class="error">' + escapeHtml(result.detail || "That could not be resolved.") + "</span>");
      return null;
    }
    return result;
  }

  // `propose` paused before making the LLM call because `scrub()` flagged a PII/PHI
  // match in the request text (ADR-0014 amendment): show what was flagged and let
  // the architect resolve it via `propose/resolve-pii`, whose response is the same
  // `message`/`options`/delta shape `propose` itself returns -- or, for "Edit text"
  // with a still-flagged replacement, another `pii_review_required` to resolve.
  function renderPiiReview(body) {
    const matchesHtml = (body.matches || []).map((m) =>
      '<div class="pii">Flagged as <b>' + escapeHtml(m.category) + "</b> (confidence "
      + Math.round(m.confidence * 100) + "%)</div>"
    ).join("");
    const div = addMessage(
      "agent",
      "This looks like it may contain personal information:" + matchesHtml
      + '<div class="actions">'
      + '<button data-pii-action="redact">Redact and continue</button>'
      + '<button data-pii-action="allow">Send as-is</button>'
      + '<button data-pii-action="edit">Edit text</button>'
      + "</div>"
    );
    div.querySelectorAll("button[data-pii-action]").forEach((button) => {
      button.addEventListener("click", async () => {
        const action = button.dataset.piiAction;
        let editedText;
        if (action === "edit") {
          editedText = window.prompt("Replace the flagged text with:", "");
          if (!editedText || !editedText.trim()) return;
        }
        div.querySelectorAll("button[data-pii-action]").forEach((b) => { b.disabled = true; });
        const result = await resolvePii(action, editedText);
        if (result) {
          renderProposeResponse(result);
        } else {
          // resolvePii() already showed the error (e.g. "allow" rejected after a
          // detector-engine error, ADR-0046) -- re-enable so redact/edit, which the
          // pending confirmation is still open for, remain reachable.
          div.querySelectorAll("button[data-pii-action]").forEach((b) => { b.disabled = false; });
        }
      });
    });
  }

  function renderProposeResponse(body) {
    if (body.status === "message") {
      // The LLM asked a question or made a suggestion instead of proposing a delta.
      // body.message is untrusted LLM output and may be Markdown (GH #185):
      // render it as formatted HTML via the sanitising renderMarkdown, never as raw HTML.
      addMessage("agent", renderMarkdown(body.message));
      return body;
    }
    if (body.status === "pii_review_required") {
      // No delta yet -- the architect must resolve the flagged match first.
      renderPiiReview(body);
      resetPendingDelta();
      return body;
    }
    if (body.status === "options") {
      // No concrete delta yet -- the architect still has to pick one of the options.
      renderOptions(body);
      resetPendingDelta();
      return body;
    }
    const notes = (body.notes || []).map((n) => '<div class="finding">Corrected: ' + escapeHtml(n) + "</div>").join("");
    const changed = deltaHasChanges(body);
    const findingsHtml = notes + renderFindings(body);
    const div = addMessage("agent", describeProposal(body) + (findingsHtml
      || "Looks good -- no objections. Nothing is written until you click Apply."));
    wireDecisionButtons(div, body.delta_id);
    currentDeltaId = body.delta_id;
    currentDeltaValidated = body.status === "validated" && changed;
    currentElements = body.elements || [];
    currentRelationships = body.relationships || [];
    updateApplyButton();
    if (changed) {
      selectDeltaView(body);
      showPreview();
    }
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
    """Serve the split-screen conversational authoring page.

    Returns:
        The self-contained `_PAGE` HTML/CSS/JS document described in this module's
        docstring; there is no templating or per-request state.
    """
    return _PAGE
