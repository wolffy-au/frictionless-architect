"""Playwright-driven steps for the control conversion playground."""

from __future__ import annotations

from behave import given, then, when
from behave.runner import Context


@given("the control conversion playground is open")
def step_open_playground(context: Context) -> None:
    context.page.goto(f"{context.base_url}/playground")


@when("I paste the following OSCAL control YAML:")
def step_paste_oscal_yaml(context: Context) -> None:
    context.page.fill("#oscal-input", context.text)


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


@when("I open the LLM settings from the playground")
def step_open_llm_settings(context: Context) -> None:
    context.page.click("#llm-settings-link")
    context.page.wait_for_selector("#default-form select")


@when('I save the global default as provider "{provider}" and model "{model}"')
def step_save_default(context: Context, provider: str, model: str) -> None:
    form = "#default-form"
    context.page.select_option(f"{form} select", provider)
    context.page.fill(f"{form} input >> nth=0", model)
    context.page.click(f"{form} button.primary")
    context.page.wait_for_selector(f"{form} .msg.ok")


@then('the settings page should list the component "{label}" as inheriting the default')
def step_component_inherits(context: Context, label: str) -> None:
    context.page.wait_for_selector("#components h2")
    heading = context.page.inner_text("#components h2")
    assert label in heading and "inherits default" in heading, heading


@then("the reference Markdown pane should show each line once, with no extra line breaks")
def step_no_extra_breaks(context: Context) -> None:
    context.page.wait_for_selector("#markdown-output .md-line")
    rendered = context.page.inner_text("#markdown-output").rstrip("\n").split("\n")
    rows = context.page.locator("#markdown-output .md-line").count()
    assert len(rendered) == rows, f"{rows} rows rendered as {len(rendered)} lines"


@when('I click the copy button for "{target}"')
def step_click_copy(context: Context, target: str) -> None:
    context.page.wait_for_selector("#markdown-output .md-line")
    context.page.click(f'button.copy[data-copy-from="{target}"]')
    context.page.wait_for_selector(f'button.copy[data-copy-from="{target}"]:has-text("Copied")')


@then('the clipboard should contain "{expected}"')
def step_clipboard_contains(context: Context, expected: str) -> None:
    text = context.page.evaluate("navigator.clipboard.readText()")
    assert expected in text, f"expected {expected!r} in clipboard, got {text!r}"


@then("the clipboard should hold the reference Markdown without extra line breaks")
def step_clipboard_matches_rows(context: Context) -> None:
    text = context.page.evaluate("navigator.clipboard.readText()")
    rows = context.page.locator("#markdown-output .md-line").count()
    assert len(text.rstrip("\n").split("\n")) == rows, f"{rows} rows but clipboard has {text!r}"


@then("the changed words should be highlighted in both Markdown panes")
def step_word_level_highlight(context: Context) -> None:
    context.page.wait_for_selector("#candidate-markdown-output .md-line")
    context.page.wait_for_selector("#candidate-markdown-output .w.add")
    context.page.wait_for_selector("#markdown-output .w.rem")
    # A modified line keeps its unchanged words unhighlighted.
    unchanged = context.page.inner_text("#candidate-markdown-output .md-line.paired")
    highlighted = context.page.locator("#candidate-markdown-output .md-line.paired .w.add").all_inner_texts()
    assert any(word not in highlighted for word in unchanged.split()), unchanged
