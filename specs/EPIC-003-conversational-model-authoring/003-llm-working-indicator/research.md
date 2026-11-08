# Research: LLM Working Indicator for Conversational Authoring

## Decision: A transient chat message, not a banner or overlay

**Decision**: The working indicator is an extra chat message (same `#messages` flow as
every other turn), styled distinctly, inserted right after the architect's own message and
removed the moment a reply or failure is ready.

**Rationale**: The issue's own suggested shape is "a 'thinking' message in the chat"; the
chat is already the place every other kind of reply (message, delta summary, PII review,
options, error) appears, so a new UI region would be an inconsistent second place to look.

**Alternatives considered**:

- A banner/status element (like `#render-banner` or `#render-status`) — rejected: those are
  scoped to the render pane's own state, not the chat; reusing them for an unrelated concern
  would conflate two panels' state in one element.
- A full-composer overlay/spinner — rejected: more visually disruptive than the issue asks
  for, and the Send-button-disabled guard already covers "you can't send another one yet"
  (FR-006); no second mechanism is needed for that.

## Decision: Keep it in `ui.py`; do not extract a new shared package yet

**Decision**: The indicator is two small, self-contained JS functions plus a CSS rule, added
to `ui.py`'s existing embedded `<style>`/`<script>`. No new `platform/packages/<name>`
package is created.

**Rationale**: This package already has a precedent for exactly this situation —
`markdown_render.render_message_markdown` (GH #185) was written to take no dependency beyond
its input so another package's chat/LLM UI *could* reuse it as-is, without a second consumer
actually being wired up. ADR-0034's granularity rule is explicit that a shared package is
justified by an actual second consumer, not a hypothetical one; `controls-compliance-catalog`
already has its own, differently-shaped working indicator (a "converting…" status dot) for
its own LLM-backed call, so there is no real second caller asking for *this* indicator today.

**Alternatives considered**:

- Extract a new `platform/packages/<name>` shared package now, since the issue frames this as
  platform functionality — rejected: no second package is adopting it in this change, and
  ADR-0034 rejects a catch-all/pre-emptive shared package without a real second consumer.
- Port `controls-compliance-catalog`'s playground to use the same indicator in this change —
  out of scope: GH #186 is about the conversational authoring chat UI only, and the
  playground's existing indicator is not reported broken.

## Decision: No new server-side state

**Decision**: No new session field, API field, or endpoint is added. "A request is in
flight" is known entirely on the client — it is the thing awaiting its own `fetch()` — so
nothing needs telling the server, and nothing needs telling a second page/tab (single-user
local MVP, ADR-0024).

**Rationale**: `propose` and `propose/resolve-pii`'s existing response shapes already cover
every outcome (`message`, delta, `options`, `pii_review_required`, or a non-2xx error); the
indicator only needs to span the client's own wait for one of those, which the existing
`sendRequest`/PII-resolution click handlers already bound with `try`/`finally` blocks that
re-enable the Send button — the same blocks the indicator's removal piggybacks on.

**Alternatives considered**: A server-pushed "working" event (SSE/websocket) — rejected:
that is the streaming alternative the issue itself puts out of scope, and is unnecessary
when the client already knows it is waiting on its own request.

## Decision: Testing the transient indicator needs a controllable delay

**Decision**: `tests/support/fake_llm.py`'s `FakeCompletion` gains an optional `delay: float`
field (default `0`), slept at the top of `__call__` before returning. One new behave scenario
sets it long enough to assert the indicator is visible mid-flight, then lets the call
complete and asserts the indicator is gone and the reply is shown.

**Rationale**: `FakeCompletion` returns synchronously and instantly today, so a scenario that
only asserts "the indicator appeared, then disappeared" would race the real browser against
an essentially-zero-duration server call. `propose`/`propose/resolve-pii` are sync `def`
FastAPI routes, so FastAPI already runs them in its threadpool — sleeping inside the fake
completion does not block the live `uvicorn` test server (`environment.py`) from serving the
one browser-driven request the scenario makes.

**Alternatives considered**:

- Playwright route interception/delay on the `/propose` fetch — rejected: heavier, and
  bypasses the one seam (`context.fake_llm`) every other scenario already uses to control
  LLM timing and content.
- Asserting only the indicator's *absence* after the reply arrives, never its presence while
  waiting — rejected: that would not actually test the feature (FR-001/FR-002), only that it
  eventually goes away.

## Non-goals carried over from spec.md Assumptions

- Streaming the reply incrementally — explicitly out of scope per the issue.
- A visual design beyond a plain chat message (e.g. an animated spinner icon) — the issue's
  own example ("a 'thinking' message") is the default; a short CSS pulse animation on the
  text is enough to make it visibly distinct from a static message, respecting
  `prefers-reduced-motion`.
