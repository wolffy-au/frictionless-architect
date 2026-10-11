"""A fake ``litellm.completion`` for tests: records calls and returns a canned delta."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any


def fake_delta_for(request: str) -> str:
    """A deterministic candidate-delta JSON string derived from the request text."""
    return json.dumps(
        {
            "elements": [{"type": "ApplicationFunction", "name": request.strip()}],
            "relationships": [],
        }
    )


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
            content = fake_delta_for(kwargs["messages"][-1]["content"])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
