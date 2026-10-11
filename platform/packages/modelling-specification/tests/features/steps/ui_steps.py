"""Step definitions for the split-screen authoring UI scenarios (T070, R15-R19).

Drives `context.page` (Playwright, T068) against `context.base_url` -- the live
`uvicorn` server started in `environment.py` -- rather than `context.client`
(`TestClient`), since a browser cannot drive an ASGI `TestClient` directly. The
`Given an architect describes...` steps reused from `authoring_steps.py` still set
`context.fake_llm.content`/stub `rendering.py`, which the live server (same process,
same module objects) picks up identically.
"""

from __future__ import annotations

from behave import given, step, then, when
from behave.runner import Context


@given("the architect opens the authoring UI")
def step_open_ui(context: Context) -> None:
    context.page.goto(context.base_url + "/authoring/")
    context.page.wait_for_selector("#chat-input")


@when("the architect sends that request in the UI")
def step_send_request(context: Context) -> None:
    context.page.fill("#chat-input", "the architect's request")
    context.page.click("#send")
    context.page.wait_for_selector("#messages .msg.agent")


@then("the chat pane shows no objections")
def step_chat_shows_no_objections(context: Context) -> None:
    context.page.locator("#messages").get_by_text("no objections", exact=False).wait_for()


@when('the architect picks the state "{state}" and clicks Apply in the UI')
def step_pick_state_and_apply(context: Context, state: str) -> None:
    context.page.select_option("#state-select", state)
    context.page.click("#apply")
    context.page.locator("#messages").get_by_text("Applied as", exact=False).wait_for()


@then("the chat pane confirms the change was applied")
def step_chat_confirms_applied(context: Context) -> None:
    context.page.locator("#messages").get_by_text("Applied as", exact=False).wait_for()


@step("the architect turns on auto-render in the UI")
def step_turn_on_auto_render(context: Context) -> None:
    context.page.check("#auto-render-toggle")


@then("the render pane displays an SVG diagram spanning the full pane width")
def step_render_pane_has_svg(context: Context) -> None:
    # R18: the pane inlines the SVG response body directly and scales it to the
    # available width via CSS (`max-width: 100%`), rather than a fixed-size <img>.
    svg = context.page.locator("#render-pane svg")
    svg.wait_for()
    max_width = svg.evaluate("el => getComputedStyle(el).maxWidth")
    assert max_width == "100%", max_width

    # R19: horizontal split -- the render panel sits *below* the chat panel and
    # spans the same width, not side by side with it.
    panels = context.page.locator("section.panel")
    chat_box = panels.nth(0).bounding_box()
    render_box = panels.nth(1).bounding_box()
    assert render_box["y"] >= chat_box["y"] + chat_box["height"] - 1, (chat_box, render_box)
    assert abs(render_box["width"] - chat_box["width"]) <= 1, (chat_box, render_box)
