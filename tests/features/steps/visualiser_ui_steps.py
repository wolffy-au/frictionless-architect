"""Steps for the visualiser placeholder page (FR-001, FR-002, FR-009), driven via
Playwright against the live app the @ui harness in environment.py boots."""

# pyright: reportCallIssue=false
# mypy: disable-error-code="untyped-decorator,no-any-return"
from __future__ import annotations

from typing import Any

import httpx
from behave import then, when  # type: ignore[import-untyped]


@when("a browser opens the visualiser placeholder page")
def step_open_placeholder_page(context: Any) -> None:
    context.console_errors = []
    context.page.on(
        "console",
        lambda msg: context.console_errors.append(msg.text) if msg.type == "error" else None,
    )
    context.page.goto(f"{context.base_url}/")


@then("the page loads with no JavaScript console error")
def step_no_console_error(context: Any) -> None:
    assert context.console_errors == [], f"console errors: {context.console_errors}"


@then("the rendered status text confirms the page loaded")
def step_status_text(context: Any) -> None:
    status_text = context.page.locator('[data-testid="status"]').inner_text()
    assert "loaded" in status_text.lower(), f"unexpected status text: {status_text!r}"


@then("the schema summary reflects the sample-data fallback")
def step_schema_summary(context: Any) -> None:
    response = httpx.get(f"{context.base_url}/schema-payload")
    response.raise_for_status()
    expected_count = len(response.json()["elements"])

    summary_text = context.page.locator('[data-testid="schema-summary"]').inner_text()
    assert str(expected_count) in summary_text, (
        f"schema summary {summary_text!r} does not reflect element count {expected_count}"
    )
