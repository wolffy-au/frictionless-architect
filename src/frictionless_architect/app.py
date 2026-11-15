"""FastAPI entry point for the platform app.

Currently serves the schema visualiser JSON API and its placeholder landing page (``GET /``).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from frictionless_architect.visualizer.api import get_schema_service, router
from frictionless_architect.visualizer.placeholder_page import router as placeholder_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Run the app, then stop the load retry and close the shared Neo4j driver on shutdown.

    Args:
        _: The FastAPI application (unused).

    Yields:
        Control to the running application.
    """
    try:
        yield
    finally:
        service = get_schema_service()
        await service.stop_retry()
        service.loader.close()


app = FastAPI(title="Frictionless Architect", lifespan=lifespan)
app.include_router(router)
app.include_router(placeholder_router)
