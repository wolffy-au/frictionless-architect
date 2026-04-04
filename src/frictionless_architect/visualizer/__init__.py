"""FastAPI entry point for the schema visualiser."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from frictionless_architect.visualizer.api import get_schema_service, router
from frictionless_architect.visualizer.config import get_visualizer_settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    yield
    get_schema_service().loader.close()


app = FastAPI(title="Neo4j Schema Visualiser", lifespan=lifespan)
app.include_router(router)

static_dir = Path(__file__).resolve().parent / "static"
app.mount("/schema-visualizer/static", StaticFiles(directory=static_dir), name="schema_visualizer_static")

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


@app.get("/schema-visualizer")
async def visualizer(request: Request) -> Any:
    current_settings = get_visualizer_settings()
    return templates.TemplateResponse(
        "schema_visualizer.html",
        {"request": request, "warning_text": current_settings.warning_text},
    )
