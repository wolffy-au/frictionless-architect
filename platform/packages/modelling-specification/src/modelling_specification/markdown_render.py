"""Render untrusted LLM chat text as sanitised HTML (GH #185).

`propose`/`resolve-pii` surface the LLM's free-text replies (``status: "message"``)
to the architect in `ui.py`'s chat pane. That text is Markdown but is never trusted
raw HTML: it is parsed with `markdown`, then every tag and attribute outside a small
allowlist is stripped by `nh3` (the Ammonia HTML sanitiser) before the result is sent
to the client, which inserts it directly as HTML.
"""

from __future__ import annotations

import markdown
import nh3

_ALLOWED_TAGS = {
    "p",
    "br",
    "strong",
    "em",
    "code",
    "pre",
    "ul",
    "ol",
    "li",
    "h1",
    "h2",
    "h3",
    "a",
}
_ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def render_message_markdown(text: str) -> str:
    """Turn `text` (untrusted Markdown) into sanitised, display-ready HTML."""
    unsafe_html = markdown.markdown(text, extensions=["fenced_code", "sane_lists", "nl2br"])
    return nh3.clean(
        unsafe_html,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        set_tag_attribute_values={"a": {"target": "_blank"}},
        link_rel="noopener noreferrer",
    )
