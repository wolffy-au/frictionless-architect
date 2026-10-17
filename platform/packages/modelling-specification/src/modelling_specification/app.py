"""FastAPI entry point for the modelling-specification package (ADR-0020)."""

from __future__ import annotations

from fastapi import FastAPI
from llm_provider_config import Component, create_settings_router

from modelling_specification.authoring.delta import COMPONENT_ID
from modelling_specification.router import router
from modelling_specification.ui import router as ui_router

# Registers the component (T018, R4) so its provider/model/credential can be set
# per-component via the mounted settings router or the CLI, same pattern as
# controls-compliance-catalog's own component. `COMPONENT_ID` is defined once, in
# `authoring/delta.py`, which resolves it through `llm_provider_config.resolve_call`
# for the natural-language-to-delta call.

app = FastAPI(title="Modelling Specification")
app.include_router(router)
app.include_router(ui_router)
app.include_router(
    create_settings_router([Component(id=COMPONENT_ID, label="Conversational model authoring (AI)")]),
)
