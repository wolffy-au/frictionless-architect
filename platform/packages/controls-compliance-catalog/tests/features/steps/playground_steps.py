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


@when("I paste the following control prose:")
def step_paste_control_prose(context: Context) -> None:
    context.page.fill("#prose-input", context.text)


@when('I click "Convert via AI (candidate)"')
def step_click_convert_candidate(context: Context) -> None:
    context.page.click("#convert-candidate-button")


@then('the candidate Markdown output should contain "{expected}"')
def step_candidate_output_contains(context: Context, expected: str) -> None:
    context.page.wait_for_selector("#candidate-markdown-output:not(:empty)")
    output = context.page.inner_text("#candidate-markdown-output")
    assert expected in output, f"expected {expected!r} in candidate output, got: {output!r}"


@then('the playground should show a candidate error containing "{expected}"')
def step_candidate_error_contains(context: Context, expected: str) -> None:
    context.page.wait_for_selector("#candidate-error:not(:empty)")
    error_text = context.page.inner_text("#candidate-error")
    assert expected in error_text, f"expected {expected!r} in candidate error, got: {error_text!r}"
