"""Thin LLM client for prose -> Trestle Markdown AI conversion (spec 001-oscal-ai-conversion R2).

Provider, model and credential come from ``llm-provider-config`` (ADR-0034), resolved for
the ``candidate-conversion`` component, so a per-component override in the user's settings
file wins over the global default. ``convert_chunk`` stays the call-site contract.
"""

from __future__ import annotations

import re
from typing import Any

from litellm import completion
from llm_provider_config import MissingCredentialError, NotConfiguredError, resolve_call

COMPONENT_ID = "controls-compliance-catalog.candidate-conversion"

# Models often wrap Markdown output in a single ```markdown fence despite being told not to.
_SURROUNDING_FENCE = re.compile(r"\A\s*```[A-Za-z]*\n(.*?)\n```\s*\Z", re.DOTALL)


class LlmConversionError(Exception):
    """Raised when the AI conversion step fails (configuration, credential, provider, or empty response)."""


def _message_content(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    message = getattr(choices[0], "message", None) if choices else None
    content = getattr(message, "content", None)
    return content if isinstance(content, str) else ""


def convert_chunk(prompt: str, system: str) -> str:
    stripped = prompt.strip()
    if not stripped:
        raise LlmConversionError("Cannot convert empty prose to Markdown.")

    try:
        call = resolve_call(COMPONENT_ID)
    except (NotConfiguredError, MissingCredentialError) as exc:
        raise LlmConversionError(str(exc)) from exc

    messages = [{"role": "system", "content": system}, {"role": "user", "content": stripped}]
    try:
        response = completion(messages=messages, **call.completion_kwargs())
    except Exception as exc:  # noqa: BLE001 - litellm raises a wide family of provider/network errors
        raise LlmConversionError(f"The LLM call failed ({call.model}): {exc}") from exc

    content = _message_content(response).strip()
    if not content:
        raise LlmConversionError(f"The LLM returned an empty response ({call.model}).")
    fenced = _SURROUNDING_FENCE.match(content)
    return (fenced.group(1) if fenced else content).strip() + "\n"
