"""Thin LLM client for prose -> Trestle Markdown AI conversion (spec 001-oscal-ai-conversion R2).

Stubbed for now: no provider credentials are configured in this environment, so
`convert_chunk` returns a clearly-labeled placeholder instead of calling litellm.
"""

from __future__ import annotations

import re

_STUB_LABEL = (
    "[STUB AI OUTPUT — no LLM provider is configured yet; see "
    "controls_compliance_catalog.llm_client for the real litellm wiring]"
)

# Loosely matches "AC-2 Account Management: <statement>" style prose, so the stub can
# shape its placeholder like real Trestle Markdown ("# <id> - [] <title>" + a
# "## Control Statement" section) instead of just echoing the raw prose back.
_ID_TITLE_STATEMENT = re.compile(r"^\s*([A-Za-z]{2,3}-\d+)\s+(.+?):\s*(.*)$", re.DOTALL)


class LlmConversionError(Exception):
    """Raised when the AI conversion step fails (network, provider, or empty response)."""


def _as_stub_markdown(prose: str) -> str:
    match = _ID_TITLE_STATEMENT.match(prose)
    if not match:
        return prose
    control_id, title, statement = match.groups()
    return f"# {control_id.lower()} - \\[\\] {title.strip()}\n\n## Control Statement\n\n{statement.strip()}\n"


def convert_chunk(prompt: str, system: str) -> str:  # noqa: ARG001 - system kept for the real litellm call
    stripped = prompt.strip()
    if not stripped:
        raise LlmConversionError("Cannot convert empty prose to Markdown.")
    return f"{_STUB_LABEL}\n\n\n{_as_stub_markdown(stripped)}"
