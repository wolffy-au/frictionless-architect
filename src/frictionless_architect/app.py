"""FastAPI entry point for the platform app (currently serves the schema visualiser API)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from frictionless_architect.visualizer.api import get_schema_service, router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Run the app, then close the shared Neo4j driver on shutdown.

    Args:
        _: The FastAPI application (unused).

    Yields:
        Control to the running application.
    """
    yield
    get_schema_service().loader.close()


app = FastAPI(title="Frictionless Architect", lifespan=lifespan)
app.include_router(router)
