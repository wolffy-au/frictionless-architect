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
  #render-pane { padding: 14px; overflow: auto; }
  #render-pane svg { max-width: 100%; height: auto; }
  .show-row { display: flex; gap: 8px; align-items: center; }
  .error { color: var(--err); font-size: 12.5px; }
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
      <label><input type="checkbox" id="auto-render-toggle" disabled> Auto-render on apply</label>
    </div>
    <div id="messages"></div>
    <div class="state-row">
      <select id="state-select">
        <option value="" selected disabled>Choose a state&hellip;</option>
        <option value="Current">Current</option>
        <option value="Transition">Transition</option>
        <option value="Target">Target</option>
      </select>
      <button id="apply" class="primary" disabled>Apply</button>
      <span id="apply-error" class="error"></span>
    </div>
    <div class="composer">
      <textarea id="chat-input" placeholder="e.g. add an application function for X, served to the EA role"></textarea>
      <button id="send" class="primary" type="button">Send</button>
    </div>
  </section>

  <section class="panel">
    <div class="panel-head">
      <span>Render</span>
      <div class="show-row">
        <input type="text" id="show-input" placeholder="describe a view to show">
        <button id="show" type="button">Show</button>
      </div>
    </div>
    <div id="render-pane"></div>
  </section>
</div>
<script>
(function () {
  "use strict";

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
  const stateSelect = document.getElementById("state-select");
  const applyButton = document.getElementById("apply");
  const applyError = document.getElementById("apply-error");
  const chatInput = document.getElementById("chat-input");
  const sendButton = document.getElementById("send");
  const autoRenderToggle = document.getElementById("auto-render-toggle");
  const showInput = document.getElementById("show-input");
  const showButton = document.getElementById("show");
  const renderPane = document.getElementById("render-pane");

  function addMessage(role, html) {
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.innerHTML = html;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
  }

  function requireState() {
    if (!stateSelect.value) {
      applyError.textContent = "Choose a Current/Transition/Target state first.";
      return null;
    }
    applyError.textContent = "";
    return stateSelect.value;
  }

  // R17: Apply stays disabled until both a validated delta is pending and a state is chosen.
  function updateApplyButton() {
    applyButton.disabled = !(currentDeltaValidated && stateSelect.value);
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

  async function showRender(params) {
    const query = new URLSearchParams({ ...params, format: "svg" });
    const response = await fetch("/authoring/render?" + query.toString());
    if (response.status === 300) {
      const body = await response.json();
      addMessage("agent", "Which view did you mean? " + escapeHtml((body.ambiguous_candidates || []).join(", ")));
      return;
    }
    if (!response.ok) {
      addMessage("agent", '<span class="error">No view resolves from that -- try naming the object or describing the view differently.</span>');
      return;
    }
    renderPane.innerHTML = await response.text();
  }

  function renderDecisionResult(result) {
    if (!result) return;
    addMessage("agent", "Applied as <b>" + escapeHtml(result.state_classification) + "</b>."
      + (result.override_decision_id ? " Recorded as override decision " + escapeHtml(result.override_decision_id) + "." : ""));
    stateSelect.value = "";
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
        if (action !== "reject") {
          const state = requireState();
          if (!state) return;
          body.state_classification = state;
        }
        const result = await decide(deltaId, body);
        if (action === "reject") {
          if (result) addMessage("agent", "Discarded.");
          resetPendingDelta();
          return;
        }
        renderDecisionResult(result);
        if (result && result.status === "applied") {
          await maybeAutoRender(currentElements, currentRelationships);
          resetPendingDelta();
        }
      });
    });
  }

  function renderProposeResponse(body) {
    const findingsHtml = renderFindings(body);
    const div = addMessage("agent", (findingsHtml || "Looks good -- no objections.") );
    wireDecisionButtons(div, body.delta_id);
    currentDeltaId = body.delta_id;
    currentDeltaValidated = body.status === "validated";
    currentElements = body.elements || [];
    currentRelationships = body.relationships || [];
    updateApplyButton();
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
    // Enabled only once loaded, so a toggle can never race the initial GET and
    // get silently reverted by it (the checkbox starts `disabled` in markup;
    // Playwright/user interaction waits for actionability, i.e. this).
    autoRenderToggle.disabled = false;
  }

  sendButton.addEventListener("click", async () => {
    const request = chatInput.value.trim();
    if (!request) return;
    addMessage("user", escapeHtml(request));
    chatInput.value = "";
    sendButton.disabled = true;
    try {
      const response = await fetch("/authoring/sessions/" + sessionId + "/propose", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ request: request }),
      });
      const body = await response.json();
      if (!response.ok) {
        addMessage("agent", '<span class="error">' + escapeHtml(body.detail || "Could not propose a change from that.") + "</span>");
        return;
      }
      renderProposeResponse(body);
    } finally {
      sendButton.disabled = false;
    }
  });

  applyButton.addEventListener("click", async () => {
    const state = requireState();
    if (!state || !currentDeltaId) return;
    const deltaId = currentDeltaId;
    const result = await decide(deltaId, { action: "apply", state_classification: state });
    renderDecisionResult(result);
    if (result && result.status === "applied") {
      await maybeAutoRender(currentElements, currentRelationships);
      resetPendingDelta();
    }
  });

  stateSelect.addEventListener("change", () => {
    applyError.textContent = "";
    updateApplyButton();
  });

  autoRenderToggle.addEventListener("change", async () => {
    autoRenderEnabled = autoRenderToggle.checked;
    await fetch("/authoring/config", {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ auto_render: autoRenderEnabled }),
    });
  });

  showButton.addEventListener("click", async () => {
    const description = showInput.value.trim();
    if (!description) return;
    await showRender({ description: description });
  });

  (async function init() {
    await initSession();
    await initConfig();
  })();
})();
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def authoring_page() -> str:
    return _PAGE
