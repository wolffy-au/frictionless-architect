"""FastAPI entry point for the modelling-specification package (ADR-0020)."""

from __future__ import annotations

from fastapi import FastAPI
from llm_provider_config import Component, create_settings_router

from modelling_specification.router import router

# T018 (R4): registers the component so its provider/model/credential can be set
# per-component via the mounted settings router or the CLI, same pattern as
# controls-compliance-catalog's own component. `authoring/delta.py` (Phase 3, T025)
# resolves this id through `llm_provider_config.resolve_call` for the NL-to-delta call.
COMPONENT_ID = "modelling-specification.conversational-authoring"

app = FastAPI(title="Modelling Specification")
app.include_router(router)
app.include_router(
    create_settings_router([Component(id=COMPONENT_ID, label="Conversational model authoring (AI)")]),
)
