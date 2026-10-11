"""Contract tests for `GET`/`PUT /authoring/config` -- the auto-render toggle
(FR-011, contracts/api.md)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from modelling_specification.app import app

client = TestClient(app)


def test_get_config_defaults_to_auto_render_false() -> None:
    response = client.get("/authoring/config")

    assert response.status_code == 200
    assert response.json() == {"auto_render": False}


def test_put_config_updates_and_echoes_the_new_value() -> None:
    response = client.put("/authoring/config", json={"auto_render": True})

    assert response.status_code == 200
    assert response.json() == {"auto_render": True}
    assert client.get("/authoring/config").json() == {"auto_render": True}

    # reset for other tests sharing the process-wide config
    client.put("/authoring/config", json={"auto_render": False})
