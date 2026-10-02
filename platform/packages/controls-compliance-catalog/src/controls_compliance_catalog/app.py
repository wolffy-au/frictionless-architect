"""FastAPI entry point for the controls-compliance-catalog package."""

from __future__ import annotations

from fastapi import FastAPI

from controls_compliance_catalog.playground.api import router as playground_router

app = FastAPI(title="Controls & Compliance Catalog")
app.include_router(playground_router)
