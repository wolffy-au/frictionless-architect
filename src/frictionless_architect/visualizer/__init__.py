"""FastAPI entry point for the schema visualiser."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from frictionless_architect.visualizer.api import get_schema_service, router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    yield
    get_schema_service().loader.close()


app = FastAPI(title="Neo4j Schema Visualiser", lifespan=lifespan)
app.include_router(router)
