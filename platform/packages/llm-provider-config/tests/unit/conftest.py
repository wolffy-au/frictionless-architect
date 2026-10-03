"""Shared fixtures: an in-memory keyring, a failing one, and a clean environment."""

from collections.abc import Iterator

import keyring
import pytest
from keyring.backend import KeyringBackend
from keyring.backends.fail import Keyring as FailKeyring
from keyring.errors import PasswordDeleteError


class InMemoryKeyring(KeyringBackend):
    priority = 1  # pyright: ignore[reportAssignmentType]

    def __init__(self) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        try:
            del self._store[(service, username)]
        except KeyError as exc:
            raise PasswordDeleteError("not found") from exc


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY", "LLM_PROVIDER_CONFIG_PATH"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def fake_keyring() -> Iterator[InMemoryKeyring]:
    previous = keyring.get_keyring()
    backend = InMemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


@pytest.fixture
def no_keyring() -> Iterator[None]:
    previous = keyring.get_keyring()
    keyring.set_keyring(FailKeyring())  # type: ignore[no-untyped-call]
    yield
    keyring.set_keyring(previous)
