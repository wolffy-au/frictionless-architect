"""Unit tests for the visualiser settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from frictionless_architect.visualizer.config import VisualizerSettings


def test_retry_interval_defaults_to_the_five_minute_cap() -> None:
    assert VisualizerSettings().retry_interval_seconds == 300


@pytest.mark.parametrize("value", (0, 1, 300))
def test_retry_interval_accepts_values_up_to_the_cap(value: int) -> None:
    assert VisualizerSettings(retry_interval_seconds=value).retry_interval_seconds == value


@pytest.mark.parametrize("value", (301, 3600, -1))
def test_retry_interval_rejects_values_outside_the_sc006_bound(value: int) -> None:
    with pytest.raises(ValidationError):
        VisualizerSettings(retry_interval_seconds=value)


def test_retry_interval_is_read_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRICTIONLESS_ARCHITECT_RETRY_INTERVAL_SECONDS", "42")
    assert VisualizerSettings().retry_interval_seconds == 42
