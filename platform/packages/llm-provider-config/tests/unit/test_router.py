from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from llm_provider_config import router as router_module
from llm_provider_config.credentials import SERVICE_NAME
from llm_provider_config.router import Component, create_settings_router
from llm_provider_config.store import load_settings

COMPONENT = Component(id="pkg.feature", label="Feature")
OLLAMA = {"provider": "ollama", "model": "gemma4:12b", "params": {"temperature": 0}}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_keyring: None) -> Iterator[TestClient]:
    monkeypatch.setenv("LLM_PROVIDER_CONFIG_PATH", str(tmp_path / "llm.toml"))
    app = FastAPI()
    app.include_router(create_settings_router([COMPONENT]))
    yield TestClient(app)


def test_state_starts_empty(client: TestClient) -> None:
    body = client.get("/settings/llm/state").json()
    assert body["default"] is None
    assert body["components"] == [{"id": "pkg.feature", "label": "Feature", "override": None}]
    assert {p["id"] for p in body["providers"]} == {"openai", "gemini", "anthropic", "ollama"}


def test_page_is_served_with_prefix(client: TestClient) -> None:
    page = client.get("/settings/llm")
    assert page.status_code == 200
    assert 'const base = "/settings/llm"' in page.text


def test_default_and_override_round_trip(client: TestClient) -> None:
    assert client.put("/settings/llm/default", json=OLLAMA).status_code == 200
    override = {"provider": "anthropic", "model": "claude-sonnet-5-5"}
    assert client.put("/settings/llm/components/pkg.feature", json=override).status_code == 200

    state = client.get("/settings/llm/state").json()
    assert state["default"]["model"] == "gemma4:12b"
    assert state["components"][0]["override"]["provider"] == "anthropic"
    assert load_settings().resolve("pkg.feature").provider.value == "anthropic"

    assert client.delete("/settings/llm/components/pkg.feature").status_code == 200
    assert load_settings().resolve("pkg.feature").provider.value == "ollama"
    assert load_settings().default is not None  # clearing an override keeps the default


def test_unknown_component_is_rejected(client: TestClient) -> None:
    assert client.put("/settings/llm/components/nope", json=OLLAMA).status_code == 404
    assert client.delete("/settings/llm/components/nope").status_code == 404
    assert client.post("/settings/llm/test", json={"component": "nope"}).status_code == 404


def test_invalid_settings_are_rejected(client: TestClient) -> None:
    assert client.put("/settings/llm/default", json={"provider": "bogus", "model": "x"}).status_code == 422
    assert client.put("/settings/llm/default", json={"provider": "ollama", "model": ""}).status_code == 422


def test_key_is_stored_in_keychain_and_never_returned(client: TestClient, fake_keyring: Any) -> None:
    client.put("/settings/llm/default", json={"provider": "openai", "model": "gpt-x"})
    assert client.put("/settings/llm/keys/openai", json={"api_key": "sk-secret"}).status_code == 200
    assert fake_keyring.get_password(SERVICE_NAME, "openai") == "sk-secret"

    state = client.get("/settings/llm/state")
    assert state.json()["default"]["key_source"] == "keychain"
    assert "sk-secret" not in state.text

    assert client.delete("/settings/llm/keys/openai").status_code == 200
    assert client.get("/settings/llm/state").json()["default"]["key_source"] == "missing"
    assert client.delete("/settings/llm/keys/openai").status_code == 404


def test_key_without_keychain_points_at_env_var(client: TestClient, no_keyring: None) -> None:
    response = client.put("/settings/llm/keys/openai", json={"api_key": "sk-x"})
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_ollama_key_is_refused(client: TestClient) -> None:
    assert client.put("/settings/llm/keys/ollama", json={"api_key": "x"}).status_code == 422


def test_key_source_reports_environment(client: TestClient, no_keyring: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    client.put("/settings/llm/default", json={"provider": "openai", "model": "gpt-x"})
    assert client.get("/settings/llm/state").json()["default"]["key_source"] == "environment"


def test_connection_test_reports_not_configured(client: TestClient) -> None:
    body = client.post("/settings/llm/test", json={}).json()
    assert body["ok"] is False
    assert "No LLM provider is configured" in body["message"]


def test_connection_test_success_and_failure(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    client.put("/settings/llm/default", json=OLLAMA)
    seen: dict[str, Any] = {}

    def fake_completion(**kwargs: Any) -> object:
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(router_module, "completion", fake_completion)
    body = client.post("/settings/llm/test", json={"component": "pkg.feature"}).json()
    assert body == {"ok": True, "message": "ollama_chat/gemma4:12b responded."}
    assert seen["model"] == "ollama_chat/gemma4:12b"

    def failing_completion(**kwargs: Any) -> object:
        raise RuntimeError("connection refused")

    monkeypatch.setattr(router_module, "completion", failing_completion)
    body = client.post("/settings/llm/test", json={}).json()
    assert body["ok"] is False
    assert "connection refused" in body["message"]
