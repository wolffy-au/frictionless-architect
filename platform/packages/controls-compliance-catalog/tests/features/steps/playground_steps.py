"""Playwright-driven steps for the control conversion playground."""

from __future__ import annotations

from behave import given, then, when
from behave.runner import Context


@given("the control conversion playground is open")
def step_open_playground(context: Context) -> None:
    context.page.goto(f"{context.base_url}/playground")


@when("I paste the following OSCAL control JSON:")
def step_paste_oscal_json(context: Context) -> None:
    context.page.fill("#oscal-json", context.text)


@when('I click "Convert to Markdown"')
def step_click_convert(context: Context) -> None:
    context.page.click("#convert-button")


@then('the Trestle Markdown output should contain "{expected}"')
def step_markdown_output_contains(context: Context, expected: str) -> None:
    context.page.wait_for_selector("#markdown-output:not(:empty)")
    output = context.page.inner_text("#markdown-output")
    assert expected in output, f"expected {expected!r} in markdown output, got: {output!r}"


@then('the playground should show an error containing "{expected}"')
def step_error_contains(context: Context, expected: str) -> None:
    context.page.wait_for_selector("#playground-error:not(:empty)")
    error_text = context.page.inner_text("#playground-error")
    assert expected in error_text, f"expected {expected!r} in error, got: {error_text!r}"
