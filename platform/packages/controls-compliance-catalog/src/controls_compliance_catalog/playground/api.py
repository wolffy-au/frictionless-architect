"""Playground routes (GH #76): a dev-tool UI, not a journey-API role (out of scope per the issue)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from controls_compliance_catalog.playground.convert import (
    PlaygroundConversionError,
    convert_control_prose_to_markdown_candidate,
    convert_oscal_control_to_markdown,
)

router = APIRouter(prefix="/playground", tags=["playground"])


class OscalToMarkdownRequest(BaseModel):
    oscal_json: str


class OscalToMarkdownResponse(BaseModel):
    markdown: str


class ProseToMarkdownCandidateRequest(BaseModel):
    prose: str


class ProseToMarkdownCandidateResponse(BaseModel):
    markdown: str


class PlaygroundError(BaseModel):
    error_code: str
    message: str


@router.post(
    "/oscal-to-markdown",
    response_model=OscalToMarkdownResponse,
    responses={422: {"model": PlaygroundError}},
)
def oscal_to_markdown(request: OscalToMarkdownRequest) -> OscalToMarkdownResponse | JSONResponse:
    try:
        markdown = convert_oscal_control_to_markdown(request.oscal_json)
    except PlaygroundConversionError as exc:
        error = PlaygroundError(error_code="invalid_oscal", message=str(exc))
        return JSONResponse(status_code=422, content=error.model_dump())
    return OscalToMarkdownResponse(markdown=markdown)


@router.post(
    "/prose-to-markdown-candidate",
    response_model=ProseToMarkdownCandidateResponse,
    responses={422: {"model": PlaygroundError}},
)
def prose_to_markdown_candidate(
    request: ProseToMarkdownCandidateRequest,
) -> ProseToMarkdownCandidateResponse | JSONResponse:
    try:
        markdown = convert_control_prose_to_markdown_candidate(request.prose)
    except PlaygroundConversionError as exc:
        error = PlaygroundError(error_code="invalid_prose", message=str(exc))
        return JSONResponse(status_code=422, content=error.model_dump())
    return ProseToMarkdownCandidateResponse(markdown=markdown)


_SAMPLE_CONTROL_JSON = """{
  "id": "ac-2",
  "class": "SP800-53",
  "title": "Account Management",
  "parts": [
    {
      "id": "ac-2_smt",
      "name": "statement",
      "prose": "The organization manages information system accounts."
    }
  ]
}"""

_SAMPLE_CONTROL_PROSE = "AC-2 Account Management: The organization manages information system accounts."

_PAGE_TEMPLATE = """\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Control Conversion Playground</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Serif:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {
    --bg:#F7F6F2; --surface:#FFFFFF; --surface-2:#F0EFE9; --border:#DDDAD1;
    --text:#1E1C18; --text-muted:#726F63; --text-faint:#9A9789;
    --accent-ref:#1F6F5C; --accent-ref-soft:#E3F1EC;
    --accent-ai:#5B4FD6; --accent-ai-soft:#ECE9FB;
    --err:#B3432E; --err-soft:#FBEAE5;
    --shadow:0 1px 2px rgba(30,28,24,.06), 0 6px 16px rgba(30,28,24,.06);
    color-scheme: light;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --bg:#17161B; --surface:#1E1D23; --surface-2:#26252C; --border:#36343D;
      --text:#EDEBE6; --text-muted:#A6A398; --text-faint:#716E63;
      --accent-ref:#4FC9A8; --accent-ref-soft:#1D3833;
      --accent-ai:#9B91F0; --accent-ai-soft:#2C2846;
      --err:#E68A73; --err-soft:#3A2420;
      --shadow:0 1px 2px rgba(0,0,0,.3), 0 6px 20px rgba(0,0,0,.35);
      color-scheme: dark;
    }
  }
  :root[data-theme="dark"] {
    --bg:#17161B; --surface:#1E1D23; --surface-2:#26252C; --border:#36343D;
    --text:#EDEBE6; --text-muted:#A6A398; --text-faint:#716E63;
    --accent-ref:#4FC9A8; --accent-ref-soft:#1D3833;
    --accent-ai:#9B91F0; --accent-ai-soft:#2C2846;
    --err:#E68A73; --err-soft:#3A2420;
    --shadow:0 1px 2px rgba(0,0,0,.3), 0 6px 20px rgba(0,0,0,.35);
    color-scheme: dark;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font-family: "IBM Plex Sans", system-ui, sans-serif;
    padding: 28px 20px 48px;
  }
  .wrap { max-width: 1180px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; }
  .eyebrow {
    font-family: "IBM Plex Mono", monospace; font-size: 11px; letter-spacing: .08em;
    text-transform: uppercase; color: var(--text-muted);
  }
  h1 {
    font-family: "IBM Plex Serif", serif; font-weight: 600;
    font-size: clamp(24px, 3vw, 32px); margin: 6px 0 0;
  }
  .sub { color: var(--text-muted); font-size: 14.5px; line-height: 1.55; margin: 6px 0 0; }
  .scope-note {
    display: flex; gap: 8px; align-items: flex-start; background: var(--surface-2);
    border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px;
    font-size: 13px; color: var(--text-muted); line-height: 1.5;
  }
  .scope-note b { color: var(--text); font-weight: 600; }
  .panel {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    box-shadow: var(--shadow); display: flex; flex-direction: column; overflow: hidden;
  }
  .panel-head {
    display: flex; align-items: center; justify-content: space-between; gap: 10px;
    padding: 12px 16px; border-bottom: 1px solid var(--border);
  }
  .panel-title { display: flex; align-items: center; gap: 8px; font-size: 13.5px; font-weight: 600; }
  .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
  .dot.ref { background: var(--accent-ref); }
  .dot.ai { background: var(--accent-ai); }
  .tag {
    font-family: "IBM Plex Mono", monospace; font-size: 10.5px; letter-spacing: .03em;
    padding: 3px 7px; border-radius: 5px; color: var(--text-muted);
    background: var(--surface-2); border: 1px solid var(--border);
  }
  textarea {
    border: 0; resize: vertical; width: 100%; min-height: 160px; padding: 14px 16px;
    font-size: 13.5px; line-height: 1.55; color: var(--text); background: transparent;
    font-family: "IBM Plex Mono", monospace;
  }
  #prose-input:focus { outline: 2px solid var(--accent-ai); outline-offset: -2px; }
  #oscal-json:focus { outline: 2px solid var(--accent-ref); outline-offset: -2px; }
  .panel-foot {
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
    padding: 10px 16px; border-top: 1px solid var(--border); background: var(--surface-2);
  }
  button.run {
    font-family: "IBM Plex Sans", sans-serif; font-weight: 600; font-size: 13px; color: #fff;
    border: 0; border-radius: 999px; padding: 9px 20px; cursor: pointer;
    box-shadow: var(--shadow); transition: transform .12s ease;
  }
  button.run:hover { transform: translateY(-1px); }
  button.run:active { transform: translateY(0); }
  button.run.ref { background: var(--accent-ref); }
  button.run.ai { background: var(--accent-ai); }
  button.run:disabled { opacity: .6; cursor: default; transform: none; }
  .error {
    font-size: 12.5px; color: var(--err); font-family: "IBM Plex Mono", monospace;
  }
  .error:empty { display: none; }
  .inputs { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  .outputs { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  @media (max-width: 760px) {
    .inputs { grid-template-columns: 1fr; }
    .outputs { grid-template-columns: 1fr; }
    .pipeline { grid-template-columns: 1fr; }
  }

  /* Pipeline (loading state) */
  .pipeline { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  .track {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 16px; display: flex; flex-direction: column; gap: 10px;
  }
  .track-label { font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 7px; }
  .stages { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .stage {
    font-family: "IBM Plex Mono", monospace; font-size: 11px; padding: 6px 10px;
    border-radius: 7px; border: 1px solid var(--border); background: var(--surface-2);
    color: var(--text-muted);
  }
  .stage.active.ref { background: var(--accent-ref-soft); color: var(--accent-ref); border-color: transparent; font-weight: 600; }
  .stage.active.ai { background: var(--accent-ai-soft); color: var(--accent-ai); border-color: transparent; font-weight: 600; }
  .arrow { color: var(--text-faint); font-size: 12px; }
  .status { font-size: 12px; color: var(--text-faint); font-family: "IBM Plex Mono", monospace; }
  .status.ok.ref { color: var(--accent-ref); }
  .status.ok.ai { color: var(--accent-ai); }
  .status.err { color: var(--err); }

  /* Outputs + diff toggle */
  .outputs-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  .outputs-head h2 { font-family: "IBM Plex Serif", serif; font-size: 18px; font-weight: 600; margin: 0; }
  .toggle { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-muted); cursor: pointer; user-select: none; }
  .switch { width: 34px; height: 19px; border-radius: 999px; background: var(--surface-2); border: 1px solid var(--border); position: relative; flex: none; }
  .switch .knob { position: absolute; top: 1px; left: 1px; width: 15px; height: 15px; border-radius: 50%; background: var(--text-faint); transition: transform .15s ease, background .15s ease; }
  .toggle.on .switch { background: var(--accent-ai-soft); border-color: var(--accent-ai); }
  .toggle.on .switch .knob { transform: translateX(15px); background: var(--accent-ai); }
  .legend { display: flex; gap: 16px; flex-wrap: wrap; font-size: 11.5px; color: var(--text-muted); }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .swatch { width: 10px; height: 10px; border-radius: 3px; }
  .swatch.add { background: var(--accent-ref-soft); border: 1px solid var(--accent-ref); }
  .swatch.rem { background: var(--err-soft); border: 1px solid var(--err); }
  .md-pane {
    font-family: "IBM Plex Mono", monospace; font-size: 12.5px; line-height: 1.65;
    padding: 16px; margin: 0; max-height: 440px; overflow: auto;
    white-space: pre-wrap; word-break: break-word;
  }
  .md-line { padding: 1px 6px; border-radius: 4px; display: block; }
  .md-line.add { background: var(--accent-ref-soft); color: var(--accent-ref); }
  .md-line.rem { background: var(--err-soft); color: var(--err); text-decoration: line-through; text-decoration-thickness: 1px; }
  .simnote {
    font-size: 11.5px; color: var(--text-faint); font-family: "IBM Plex Mono", monospace;
    padding: 8px 16px; border-top: 1px solid var(--border); background: var(--surface-2);
  }

  footer {
    font-size: 12.5px; color: var(--text-faint); line-height: 1.6;
    border-top: 1px solid var(--border); padding-top: 16px;
  }
</style>
</head>
<body>
<div class="wrap">

  <header>
    <div class="eyebrow">OSCAL conversion component</div>
    <h1>Control Conversion Playground</h1>
    <p class="sub">Paste a control's prose and its OSCAL catalog entry to run both conversion
    paths to Trestle Markdown and compare the AI candidate against the deterministic reference.</p>
    <div class="scope-note">
      <span>&#9432;</span>
      <span><b>Free-form, not dataset-backed.</b> This converts one control at a time,
      ad hoc &mdash; it doesn't browse the golden dataset. The end-to-end journey API is a
      separate, later piece of work with its own role and is out of scope here.</span>
    </div>
  </header>

  <section class="inputs">
    <div class="panel">
      <div class="panel-head">
        <div class="panel-title"><span class="dot ai"></span>Control prose</div>
        <span class="tag">free text</span>
      </div>
      <textarea id="prose-input" spellcheck="false">__SAMPLE_CONTROL_PROSE__</textarea>
      <div class="panel-foot">
        <span class="error" id="candidate-error"></span>
        <button class="run ai" id="convert-candidate-button" type="button">Convert via AI (candidate)</button>
      </div>
    </div>

    <div class="panel">
      <div class="panel-head">
        <div class="panel-title"><span class="dot ref"></span>OSCAL control / catalog JSON</div>
        <span class="tag">JSON</span>
      </div>
      <textarea id="oscal-json" spellcheck="false">__SAMPLE_CONTROL_JSON__</textarea>
      <div class="panel-foot">
        <span class="error" id="playground-error"></span>
        <button class="run ref" id="convert-button" type="button">Convert to Markdown</button>
      </div>
    </div>
  </section>

  <section class="pipeline">
    <div class="track">
      <div class="track-label" style="color:var(--accent-ai)"><span class="dot ai"></span>Candidate path &middot; AI conversion</div>
      <div class="stages">
        <span class="stage active ai">Prose text</span>
        <span class="arrow">&rarr;</span>
        <span class="stage active ai">AI conversion</span>
        <span class="arrow">&rarr;</span>
        <span class="stage active ai">Candidate Markdown</span>
      </div>
      <div class="status" id="candidate-status">ready</div>
    </div>
    <div class="track">
      <div class="track-label" style="color:var(--accent-ref)"><span class="dot ref"></span>Reference path &middot; deterministic</div>
      <div class="stages">
        <span class="stage active ref">OSCAL entry</span>
        <span class="arrow">&rarr;</span>
        <span class="stage active ref">Trestle convert</span>
        <span class="arrow">&rarr;</span>
        <span class="stage active ref">Reference Markdown</span>
      </div>
      <div class="status" id="reference-status">ready</div>
    </div>
  </section>

  <section class="outputs-section" style="display:flex; flex-direction:column; gap:12px;">
    <div class="outputs-head">
      <h2>Trestle Markdown, both paths</h2>
      <div class="toggle on" id="diff-toggle">
        <span class="switch"><span class="knob"></span></span>
        <span id="diff-toggle-label">Highlight differences</span>
      </div>
    </div>
    <div class="legend">
      <span><span class="swatch rem"></span>only in reference (missed by AI)</span>
      <span><span class="swatch add"></span>only in candidate (added by AI)</span>
    </div>
    <div class="outputs">
      <div class="panel">
        <div class="panel-head">
          <div class="panel-title"><span class="dot ai"></span>Candidate Markdown</div>
          <span class="tag">from prose via AI</span>
        </div>
        <div class="md-pane" id="candidate-markdown-output"></div>
        <div class="simnote">AI-generated: converted by the configured LLM provider (see llm-provider-config), so the output can differ from Trestle's exact formatting.</div>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div class="panel-title"><span class="dot ref"></span>Reference Markdown</div>
          <span class="tag">from OSCAL via Trestle</span>
        </div>
        <div class="md-pane" id="markdown-output"></div>
        <div class="simnote">Deterministic: regenerated directly from the pasted OSCAL JSON via compliance-trestle.</div>
      </div>
    </div>
  </section>

  <footer>
    The Control Conversion Playground compares the AI prose-to-Markdown step against Trestle's own
    deterministic OSCAL &rarr; Markdown conversion for the same control, so divergence points at the
    AI step rather than at Trestle. It doesn't browse the golden dataset &mdash; paste any control's
    text ad hoc. A future iteration may let you adjust the conversion prompt here and re-run against
    this same comparison.
  </footer>

</div>
<script>
(function () {
  "use strict";

  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function diffLines(refLines, candLines) {
    const n = refLines.length, m = candLines.length;
    const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
    for (let i = n - 1; i >= 0; i--) {
      for (let j = m - 1; j >= 0; j--) {
        dp[i][j] = refLines[i] === candLines[j]
          ? dp[i + 1][j + 1] + 1
          : Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
    const refOut = [], candOut = [];
    let i = 0, j = 0;
    while (i < n && j < m) {
      if (refLines[i] === candLines[j]) {
        refOut.push({ text: refLines[i], type: "same" });
        candOut.push({ text: candLines[j], type: "same" });
        i++; j++;
      } else if (dp[i + 1][j] >= dp[i][j + 1]) {
        refOut.push({ text: refLines[i], type: "rem" });
        i++;
      } else {
        candOut.push({ text: candLines[j], type: "add" });
        j++;
      }
    }
    while (i < n) { refOut.push({ text: refLines[i], type: "rem" }); i++; }
    while (j < m) { candOut.push({ text: candLines[j], type: "add" }); j++; }
    return { refOut, candOut };
  }

  function renderRows(el, rows, highlight) {
    el.innerHTML = rows.map(r => {
      const cls = highlight && r.type !== "same" ? (" " + r.type) : "";
      return '<span class="md-line' + cls + '">' + (escapeHtml(r.text) || "&nbsp;") + "</span>";
    }).join("\\n");
  }

  function renderPlain(el, text) {
    if (text == null) {
      el.textContent = "";
      return;
    }
    renderRows(el, text.split("\\n").map(t => ({ text: t, type: "same" })), false);
  }

  const refPane = document.getElementById("markdown-output");
  const candPane = document.getElementById("candidate-markdown-output");
  const diffToggle = document.getElementById("diff-toggle");
  const diffLabel = document.getElementById("diff-toggle-label");

  let highlightOn = true;
  let lastRefText = null;
  let lastCandText = null;

  function refreshOutputs() {
    if (highlightOn && lastRefText != null && lastCandText != null) {
      const { refOut, candOut } = diffLines(lastRefText.split("\\n"), lastCandText.split("\\n"));
      renderRows(refPane, refOut, true);
      renderRows(candPane, candOut, true);
    } else {
      renderPlain(refPane, lastRefText);
      renderPlain(candPane, lastCandText);
    }
  }

  diffToggle.addEventListener("click", () => {
    highlightOn = !highlightOn;
    diffToggle.classList.toggle("on", highlightOn);
    diffLabel.textContent = highlightOn ? "Highlight differences" : "Show plain text";
    refreshOutputs();
  });

  function setStatus(el, side, state) {
    el.textContent = state;
    el.className = "status" + (state === "converted" ? " ok " + side : "") + (state === "error" ? " err" : "");
  }

  const refButton = document.getElementById("convert-button");
  const refStatus = document.getElementById("reference-status");
  let refRun = 0;
  async function runReference() {
    const myRun = ++refRun;
    const errorEl = document.getElementById("playground-error");
    errorEl.textContent = "";
    refButton.disabled = true;
    setStatus(refStatus, "ref", "converting\\u2026");
    const oscalJson = document.getElementById("oscal-json").value;
    try {
      const response = await fetch("/playground/oscal-to-markdown", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ oscal_json: oscalJson }),
      });
      const body = await response.json();
      if (myRun !== refRun) return; // a newer run superseded this one
      if (response.ok) {
        lastRefText = body.markdown;
        setStatus(refStatus, "ref", "converted");
      } else {
        lastRefText = null;
        errorEl.textContent = body.message || "Conversion failed.";
        setStatus(refStatus, "ref", "error");
      }
    } finally {
      if (myRun === refRun) {
        refButton.disabled = false;
        refreshOutputs();
      }
    }
  }
  refButton.addEventListener("click", runReference);
  // Trestle's conversion is deterministic and instant, so run it on load and as the OSCAL is edited.
  let refTimer = null;
  document.getElementById("oscal-json").addEventListener("input", () => {
    clearTimeout(refTimer);
    refTimer = setTimeout(runReference, 400);
  });
  runReference();

  const candButton = document.getElementById("convert-candidate-button");
  const candStatus = document.getElementById("candidate-status");
  candButton.addEventListener("click", async () => {
    const errorEl = document.getElementById("candidate-error");
    errorEl.textContent = "";
    candButton.disabled = true;
    setStatus(candStatus, "ai", "converting\\u2026");
    const prose = document.getElementById("prose-input").value;
    try {
      const response = await fetch("/playground/prose-to-markdown-candidate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prose: prose }),
      });
      const body = await response.json();
      if (response.ok) {
        lastCandText = body.markdown;
        setStatus(candStatus, "ai", "converted");
      } else {
        lastCandText = null;
        errorEl.textContent = body.message || "Conversion failed.";
        setStatus(candStatus, "ai", "error");
      }
    } finally {
      candButton.disabled = false;
      refreshOutputs();
    }
  });
})();
</script>
</body>
</html>
"""

_PAGE = _PAGE_TEMPLATE.replace("__SAMPLE_CONTROL_PROSE__", _SAMPLE_CONTROL_PROSE).replace(
    "__SAMPLE_CONTROL_JSON__", _SAMPLE_CONTROL_JSON
)


@router.get("", response_class=HTMLResponse)
def playground_page() -> str:
    return _PAGE
