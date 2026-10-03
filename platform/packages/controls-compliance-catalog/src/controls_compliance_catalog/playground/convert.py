"""Deterministic OSCAL control -> Trestle Markdown conversion (reference path, GH #76).

This is the playground's "known quantity" swimlane: compliance-trestle's own
OSCAL -> Markdown conversion, run against pasted OSCAL (a single control, or a
full catalog) instead of a Trestle workspace file. The AI prose -> Markdown
candidate path (GH #76's second swimlane) is deliberately out of scope here.
"""

from __future__ import annotations

import pathlib
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Any

import yaml
from trestle.core.catalog.catalog_api import CatalogAPI
from trestle.core.control_context import ContextPurpose, ControlContext
from trestle.oscal.catalog import Catalog

from controls_compliance_catalog.llm_client import LlmConversionError, convert_chunk
from controls_compliance_catalog.playground.prompts import PromptConfigError, load_system_prompt

_PROSE_PROMPT_NAME = "prose_to_trestle_markdown"


class PlaygroundConversionError(Exception):
    """Raised when pasted OSCAL input can't be converted to Trestle Markdown."""


def _as_catalog(oscal_data: dict[str, Any]) -> Catalog:
    is_full_catalog = "controls" in oscal_data or "groups" in oscal_data
    catalog_dict: dict[str, Any] = {
        "uuid": oscal_data.get("uuid", str(uuid.uuid4())),
        "metadata": {
            "title": "Control conversion playground output",
            "last-modified": datetime.now(timezone.utc).isoformat(),
            "version": "0.0.0",
            "oscal-version": "1.1.3",
        },
    }
    if is_full_catalog:
        if "controls" in oscal_data:
            catalog_dict["controls"] = oscal_data["controls"]
        if "groups" in oscal_data:
            catalog_dict["groups"] = oscal_data["groups"]
    else:
        catalog_dict["controls"] = [oscal_data]

    try:
        return Catalog.model_validate(catalog_dict)
    except Exception as exc:  # trestle/pydantic raise various validation error types
        raise PlaygroundConversionError(f"Pasted content is not a valid OSCAL control or catalog: {exc}") from exc


def convert_oscal_control_to_markdown(raw_oscal: str) -> str:
    """Convert pasted OSCAL YAML (a control, or a full catalog) into Trestle Markdown.

    JSON is also accepted, since JSON is (almost entirely) a subset of YAML.

    Uses compliance-trestle's own deterministic conversion (``CatalogAPI.write_catalog_as_markdown``)
    -- the same code path as the ``trestle author catalog-generate`` CLI command -- never a
    hand-rolled template, so the output is a faithful reference for comparison against the AI path.
    """
    try:
        oscal_data = yaml.safe_load(raw_oscal)
    except yaml.YAMLError as exc:
        raise PlaygroundConversionError(f"Pasted OSCAL content is not valid YAML: {exc}") from exc

    if not isinstance(oscal_data, dict):
        raise PlaygroundConversionError("Pasted OSCAL content is not valid YAML: expected a mapping (an OSCAL control or catalog)")

    catalog = _as_catalog(oscal_data)

    with tempfile.TemporaryDirectory() as tmp_dir:
        trestle_root = pathlib.Path(tmp_dir)
        md_root = trestle_root / "md"
        context = ControlContext.generate(ContextPurpose.CATALOG, True, trestle_root, md_root, set_parameters_flag=True)
        CatalogAPI(catalog=catalog, context=context).write_catalog_as_markdown()

        markdown_files = sorted(md_root.rglob("*.md"))
        if not markdown_files:
            raise PlaygroundConversionError("Trestle produced no Markdown for the pasted control(s).")
        return "\n\n".join(path.read_text() for path in markdown_files)


def convert_control_prose_to_markdown_candidate(prose: str) -> str:
    """Convert pasted control prose into a *candidate* Trestle Markdown via the AI path.

    This is GH #76's second swimlane: an LLM-assisted conversion, offered for comparison
    against the deterministic reference path above -- never treated as authoritative on
    its own. Calls through ``llm_client.convert_chunk`` (spec 001-oscal-ai-conversion R2).
    """
    try:
        return convert_chunk(prose, load_system_prompt(_PROSE_PROMPT_NAME))
    except (LlmConversionError, PromptConfigError) as exc:
        raise PlaygroundConversionError(str(exc)) from exc
