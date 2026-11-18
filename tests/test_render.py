import json
import re

from preflop_matrix.matrix import build_matrix
from preflop_matrix.ranges import RangeBook
from preflop_matrix.render import render_html


def payload(page: str) -> dict:
    return json.loads(re.search(r"const D = (.*);\n", page)[1])


def test_render_embeds_data_and_fills_placeholders():
    data = build_matrix([], RangeBook(), "Hero")
    page = render_html(data, "我的 <矩陣> & 測試")
    assert payload(page) == data
    assert "<title>我的 &lt;矩陣&gt; &amp; 測試</title>" in page
    assert "{{" not in page and "/*DATA*/" not in page
    assert page.startswith("<!doctype html>")


def test_data_mark_or_placeholders_in_user_text_do_not_leak():
    data = build_matrix([], RangeBook(), "{{TITLE}}")
    page = render_html(data, "/*DATA*/null {{FOOTNOTE}}")
    assert payload(page) == data
    assert "<title>/*DATA*/null {{FOOTNOTE}}</title>" in page
    assert page.count("const D = ") == 1


def test_render_includes_the_original_space_section_without_canned_commentary():
    page = render_html(build_matrix([], RangeBook(), "Hero"))
    assert 'id="a-3b"' in page and 'id="a-4b"' in page and 'id="a-5b"' in page and "awall(" in page
    assert "ka-3b" not in page and "ka-4b" not in page and "k-open" not in page


def test_render_escapes_script_terminators_in_data():
    data = build_matrix([], RangeBook(), "x</script><b>")
    page = render_html(data)
    assert "</script><b>" not in page
    assert payload(page)["meta"]["hero"] == "x</script><b>"
