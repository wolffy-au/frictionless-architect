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
    # R18: the pane inlines the SVG response body directly (no <img>).
    svg = context.page.locator("#render-pane svg")
    svg.wait_for()
    pane_box = context.page.locator("#render-pane").bounding_box()
    svg_box = svg.bounding_box()
    # Fit-to-pane: the diagram is stretched to the pane, not left at its intrinsic size.
    assert svg_box["width"] <= pane_box["width"] + 1, (svg_box, pane_box)
    assert svg_box["width"] >= pane_box["width"] * 0.5 or svg_box["height"] >= pane_box["height"] * 0.5, (
        svg_box,
        pane_box,
    )

    # R19: horizontal split -- the render panel sits *below* the chat panel and
    # spans the same width, not side by side with it.
    panels = context.page.locator("section.panel")
    chat_box = panels.nth(0).bounding_box()
    render_box = panels.nth(1).bounding_box()
    assert render_box["y"] >= chat_box["y"] + chat_box["height"] - 1, (chat_box, render_box)
    assert abs(render_box["width"] - chat_box["width"]) <= 1, (chat_box, render_box)


@when("the architect zooms in on the diagram")
def step_zoom_in(context: Context) -> None:
    context.zoom_before = context.page.locator("#render-pane svg").bounding_box()["width"]
    context.page.click("#zoom-in")


@then("the diagram is larger")
def step_diagram_larger(context: Context) -> None:
    after = context.page.locator("#render-pane svg").bounding_box()["width"]
    assert after > context.zoom_before * 1.1, (context.zoom_before, after)


@when("the architect drags the diagram")
def step_drag_diagram(context: Context) -> None:
    context.pan_before = context.page.locator("#render-pane svg").bounding_box()
    pane = context.page.locator("#render-pane").bounding_box()
    x, y = pane["x"] + pane["width"] / 2, pane["y"] + pane["height"] / 2
    context.page.mouse.move(x, y)
    context.page.mouse.down()
    context.page.mouse.move(x + 60, y + 40, steps=4)
    context.page.mouse.up()


@then("the diagram has moved with the mouse")
def step_diagram_moved(context: Context) -> None:
    after = context.page.locator("#render-pane svg").bounding_box()
    assert abs((after["x"] - context.pan_before["x"]) - 60) <= 2, (context.pan_before, after)
    assert abs((after["y"] - context.pan_before["y"]) - 40) <= 2, (context.pan_before, after)
    # Dragging and double-clicking the diagram must not leave a text selection behind.
    context.page.dblclick("#render-pane")
    assert context.page.evaluate("window.getSelection().toString()") == ""


@when("the architect resets the diagram size")
def step_reset_size(context: Context) -> None:
    context.page.click("#zoom-fit")


@then("the diagram is back to its fitted size")
def step_fitted(context: Context) -> None:
    after = context.page.locator("#render-pane svg").bounding_box()["width"]
    assert abs(after - context.zoom_before) <= 2, (context.zoom_before, after)


@when('the architect picks the view "{view_id}" from the list')
def step_pick_view(context: Context, view_id: str) -> None:
    context.page.locator("#view-select:not([disabled])").wait_for()
    context.page.select_option("#view-select", view_id)


@step("the server has forgotten the architect's session")
def step_server_forgot_session(context: Context) -> None:
    from modelling_specification import router as router_mod
    from modelling_specification.authoring.state import SessionStore

    context.page.wait_for_function("document.querySelector('#auto-render-toggle:not([disabled])') !== null")
    router_mod._store = SessionStore()


@when("the architect sends that request by pressing Enter")
def step_send_with_enter(context: Context) -> None:
    context.page.fill("#chat-input", "the architect's request")
    context.page.press("#chat-input", "Enter")
    context.page.wait_for_selector("#messages .msg.agent")


@then('the view "{view_id}" is still selected')
def step_view_still_selected(context: Context, view_id: str) -> None:
    context.page.locator("#render-pane svg").wait_for()
    assert context.page.eval_on_selector("#view-select", "el => el.value") == view_id


@then("no view question is asked")
def step_no_view_question(context: Context) -> None:
    assert context.page.inner_text("#render-status") == ""
