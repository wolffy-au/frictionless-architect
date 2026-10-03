"""FastAPI entry point for the controls-compliance-catalog package."""

from __future__ import annotations

from fastapi import FastAPI
from llm_provider_config import Component, create_settings_router

from controls_compliance_catalog.llm_client import COMPONENT_ID
from controls_compliance_catalog.playground.api import router as playground_router

app = FastAPI(title="Controls & Compliance Catalog")
app.include_router(playground_router)
app.include_router(
    create_settings_router([Component(id=COMPONENT_ID, label="Control conversion (AI candidate)")]),
)
