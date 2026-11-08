# ADR-0047: Untrusted LLM chat replies are rendered via `markdown` + `nh3`, server-side

- **Status:** Proposed
- **Date:** 2026-11-08
- **Sources:** GH #185; commit `a38a89d` (`fix(modelling-specification): sanitise and render
  chat Markdown`); commit `c5f103a` (`fix(modelling-specification): render chat Markdown
  server-side`); `platform/packages/modelling-specification/src/modelling_specification/markdown_render.py`;
  `platform/packages/modelling-specification/pyproject.toml`

## Context

`propose`/`resolve-pii`'s `status: "message"` replies are LLM free text shown verbatim in
`ui.py`'s chat pane. Before GH #185 the text was HTML-escaped and shown with
`white-space: pre-wrap`, so Markdown in a reply (bold, lists, headings) rendered as literal
syntax. GH #185 fixed this in two steps within the same change window, neither captured as
an ADR: first a hand-rolled, dependency-free `renderMarkdown()` in the client-side script
(every line escaped before any markup was layered on, a fixed allowlisted tag set), then a
same-day follow-up replacing it with server-side rendering — `router.py` now runs the raw
LLM text through `markdown.markdown()` and sanitises the result with `nh3.clean()` against
an explicit tag/attribute/URL-scheme allowlist before sending `message_html` to the client,
which inserts it directly as HTML. This is a security-relevant decision (XSS surface on
untrusted model output) with a real alternative already tried and discarded in the same
window, and no existing ADR covers it. `ADR-0044`'s test 2 (a runtime dependency decided by
its own ADR gets a Technology-layer element) would apply to `markdown`/`nh3` once this
record is ratified — neither currently has a model element.

## Decision

> DRAFT — confirm: Untrusted LLM chat replies are never inserted as raw/escaped-only text or
> parsed by hand-rolled client-side Markdown. `router.py` renders them server-side with the
> `markdown` library (`fenced_code`, `sane_lists`, `nl2br` extensions) and sanitises the
> output with `nh3` (the Ammonia HTML sanitiser) against a fixed allowlist
> (`p, br, strong, em, code, pre, ul, ol, li, h1, h2, h3, a`; only `href`/`title` on `a`;
> only `http`/`https`/`mailto` URL schemes; links forced to `target="_blank"` with
> `rel="noopener noreferrer"`). The sanitised `message_html` is sent alongside the raw text
> and the client inserts it directly, trusting the server's sanitisation rather than
> re-implementing allowlist logic in JavaScript.

## Consequences

> DRAFT — confirm:

- `markdown` and `nh3` become runtime dependencies of `modelling-specification`
  (`platform/pyproject.toml`); under ADR-0044 test 2 this decision, once accepted, obliges a
  `SystemSoftware` element (and `Serving` edge to `fn-conversational-authoring`) for at least
  `nh3` — the security-relevant sanitiser — as a follow-up model change (not made by this
  record).
- The allowlist is a single point of control for what HTML an LLM reply can ever produce in
  the chat pane; widening it is a decision, not a drive-by edit.
- The brief hand-rolled client-side renderer from GH #185's first commit (`a38a89d`) was
  superseded same-day by `c5f103a` and is gone from the codebase; nothing to mark superseded
  in the ADR log since neither step was ever recorded here.
- Revisit if a second package needs to render untrusted LLM/chat text: GH #185's own commit
  message flagged `render_message_markdown`'s dependency-free shape as reusable "as-is", but
  per ADR-0034's granularity rule no second consumer exists yet, so it stays in
  `modelling-specification` rather than becoming a shared package.

## Alternatives considered

- **Hand-rolled client-side Markdown-to-HTML with a JS allowlist** (GH #185's first commit,
  `a38a89d`) — tried, then rejected: re-implements allowlist-based HTML sanitisation by hand
  for security-sensitive untrusted content instead of using a maintained sanitiser.
- **HTML-escape and display as preformatted text (original behaviour)** — rejected: this was
  the bug GH #185 was filed against; Markdown syntax rendered as literal text.
