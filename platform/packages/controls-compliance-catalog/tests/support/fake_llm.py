"""A fake ``litellm.completion`` for tests: records calls and returns canned Markdown."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def fake_markdown_for(prose: str) -> str:
    """Deterministic Trestle-shaped Markdown derived from the prose's 'ID Title: statement' shape."""
    head, _, statement = prose.partition(":")
    title = head.strip() or "Control"
    return f"# {title}\n\n## Control Statement\n\n{statement.strip() or prose.strip()}\n"


class FakeCompletion:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        content = self.content
        if content is None:
            content = fake_markdown_for(kwargs["messages"][-1]["content"])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
