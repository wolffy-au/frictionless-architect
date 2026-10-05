"""The app's shutdown stops the SC-006 retry and closes the Neo4j driver."""

from __future__ import annotations

import asyncio

import pytest

from frictionless_architect import app as app_mod
from frictionless_architect.visualizer import api as api_mod


@pytest.mark.asyncio
async def test_shutdown_cancels_a_pending_retry_and_closes_the_loader(schema_client_recovering_sample):
    """Fail the first load so a retry is pending, with an interval long enough that it cannot finish."""
    service = api_mod.get_schema_service()
    service.settings.retry_interval_seconds = 300
    assert (await schema_client_recovering_sample.get("/schema-payload")).status_code == 503
    retry = service._retry_task
    assert retry is not None and not retry.done()

    closed: list[bool] = []
    service.loader.close = lambda: closed.append(True)  # type: ignore[method-assign]

    async with app_mod.lifespan(app_mod.app):
        pass

    await asyncio.sleep(0)
    assert retry.cancelled()
    assert service._retry_task is None
    assert closed == [True]
