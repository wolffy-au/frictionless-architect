"""Unit tests for markdown_render.py -- sanitised server-side rendering of the LLM's
free-text chat replies (GH #185)."""

from __future__ import annotations

from modelling_specification.markdown_render import render_message_markdown


def test_renders_bold_and_a_bullet_list() -> None:
    html = render_message_markdown("Here is **bold** text:\n\n- one\n- two")

    assert "<strong>bold</strong>" in html
    assert "<li>one</li>" in html
    assert "<li>two</li>" in html


def test_renders_a_fenced_code_block_with_special_characters_preserved() -> None:
    html = render_message_markdown('```\ncode with "quotes" & <angles>\n```')

    assert "<pre>" in html
    assert "<code>" in html
    assert 'code with "quotes" &amp; &lt;angles&gt;' in html


def test_renders_a_safe_https_link_with_target_and_rel() -> None:
    html = render_message_markdown("[docs](https://example.com/docs)")

    assert '<a href="https://example.com/docs"' in html
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html


def test_strips_a_javascript_scheme_link_leaving_no_href() -> None:
    html = render_message_markdown("[click me](javascript:alert(1))")

    assert "javascript:" not in html
    assert "click me" in html


def test_strips_a_raw_script_tag_and_its_content() -> None:
    html = render_message_markdown("<script>alert(1)</script>plain text")

    assert "<script" not in html
    assert "alert(1)" not in html
    assert "plain text" in html


def test_strips_an_event_handler_attribute_on_a_disallowed_tag() -> None:
    html = render_message_markdown('<img src="x" onerror="alert(1)">after')

    assert "onerror" not in html
    assert "<img" not in html
    assert "after" in html


def test_single_newlines_within_a_paragraph_become_line_breaks() -> None:
    html = render_message_markdown("line one\nline two")

    assert "<br" in html
    assert "line one" in html
    assert "line two" in html
