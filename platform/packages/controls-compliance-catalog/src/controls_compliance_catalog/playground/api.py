"""Playground routes (GH #76): a dev-tool UI, not a journey-API role (out of scope per the issue)."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from controls_compliance_catalog.playground.convert import PlaygroundConversionError, convert_oscal_control_to_markdown

router = APIRouter(prefix="/playground", tags=["playground"])


class OscalToMarkdownRequest(BaseModel):
    oscal_json: str


class OscalToMarkdownResponse(BaseModel):
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

_PAGE = f"""\
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Control Conversion Playground</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }}
  textarea {{ width: 100%; height: 220px; font-family: ui-monospace, monospace; }}
  pre {{ background: #f5f5f5; padding: 1rem; white-space: pre-wrap; }}
  #playground-error {{ color: #b00020; }}
  button {{ margin-top: 0.5rem; padding: 0.5rem 1rem; }}
</style>
</head>
<body>
<h1>Control Conversion Playground</h1>
<p>Reference path only (GH #76, swimlane 1): paste an OSCAL control or catalog and run it
through compliance-trestle's own OSCAL &rarr; Markdown conversion.</p>
<label for="oscal-json">OSCAL control / catalog JSON</label>
<textarea id="oscal-json">{_SAMPLE_CONTROL_JSON}</textarea>
<div>
  <button id="convert-button" type="button">Convert to Markdown</button>
</div>
<p id="playground-error"></p>
<h2>Trestle Markdown output</h2>
<pre id="markdown-output"></pre>
<script>
document.getElementById("convert-button").addEventListener("click", async () => {{
  const errorEl = document.getElementById("playground-error");
  const outputEl = document.getElementById("markdown-output");
  errorEl.textContent = "";
  outputEl.textContent = "";
  const oscalJson = document.getElementById("oscal-json").value;
  const response = await fetch("/playground/oscal-to-markdown", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{ oscal_json: oscalJson }}),
  }});
  const body = await response.json();
  if (response.ok) {{
    outputEl.textContent = body.markdown;
  }} else {{
    errorEl.textContent = body.message || "Conversion failed.";
  }}
}});
</script>
</body>
</html>
"""


@router.get("", response_class=HTMLResponse)
def playground_page() -> str:
    return _PAGE
