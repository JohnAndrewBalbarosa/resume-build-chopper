from __future__ import annotations

from resume_builder.extraction.rules import apply_rules
from resume_builder.industry import ExtractionRule

_HTML = """
<html><body>
  <header class="nav">Home About Contact</header>
  <main><article class="post">Built a C++ compiler with lexical analysis.</article></main>
  <footer id="foot">copyright 2026</footer>
</body></html>
"""


def test_drop_selectors_remove_chrome():
    rule = ExtractionRule(source_id="x", drop_selectors=["header.nav", "#foot"])
    text = apply_rules(_HTML, rule)
    assert "C++ compiler" in text
    assert "Home About" not in text
    assert "copyright" not in text


def test_keep_selectors_restrict_to_content():
    rule = ExtractionRule(source_id="x", keep_selectors=["article.post"])
    text = apply_rules(_HTML, rule)
    assert text.strip() == "Built a C++ compiler with lexical analysis."


def test_empty_rule_keeps_all_text():
    text = apply_rules(_HTML, ExtractionRule(source_id="x"))
    assert "C++ compiler" in text and "Home About" in text


def test_keep_regex_filters_lines():
    rule = ExtractionRule(source_id="x", keep_regex=["C\\+\\+"])
    text = apply_rules(_HTML, rule)
    assert "C++ compiler" in text
    assert "copyright" not in text


def test_garbage_html_returns_empty():
    assert apply_rules("", ExtractionRule(source_id="x")) == ""


def test_malformed_keep_regex_does_not_raise():
    rule = ExtractionRule(source_id="x", keep_regex=["[unclosed"])
    text = apply_rules(_HTML, rule)  # malformed pattern must not raise
    assert "C++ compiler" in text   # falls back to unfiltered content
