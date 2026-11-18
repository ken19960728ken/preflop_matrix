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


def test_render_escapes_script_terminators_in_data():
    data = build_matrix([], RangeBook(), "x</script><b>")
    page = render_html(data)
    assert "</script><b>" not in page
    assert payload(page)["meta"]["hero"] == "x</script><b>"
