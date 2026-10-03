"""Smoke test: the package installs into the platform/ workspace and exposes its API."""

import llm_provider_config


def test_package_exports_resolve_call_and_settings_types() -> None:
    for name in ("resolve_call", "LlmSettings", "ProviderSettings", "set_api_key", "load_settings"):
        assert name in llm_provider_config.__all__
