"""Fill the HTML template with the matrix data."""
import html
import json
import re
from importlib.resources import files

DEFAULT_TITLE = "翻前位置矩陣"
_PLACEHOLDER = re.compile(r"\{\{(TITLE|EYEBROW|FOOTNOTE)\}\}")
DATA_MARK = "/*DATA*/null"


def _texts(data: dict, title: str) -> dict[str, str]:
    meta = data["meta"]
    span = f"{meta['date_from']}～{meta['date_to']}" if meta["date_from"] != meta["date_to"] else meta["date_from"]
    return {
        "TITLE": title,
        "EYEBROW": f"6-max・翻前・{span}",
        "FOOTNOTE": (
            "理論＝理論範圍資料夾（面對 3bet 以開池範圍為分母、面對 4bet 以 3bet 範圍為分母）。"
            f"我＝{meta['hero']} 坐在面對方的手；玩家池＝其他所有人。資料：{meta['hands']:,} 手，{span}。"
        ),
    }


def render_html(data: dict, title: str = DEFAULT_TITLE) -> str:
    template = files("preflop_matrix").joinpath("template.html").read_text(encoding="utf-8")
    texts = {k: html.escape(v) for k, v in _texts(data, title).items()}
    page = _PLACEHOLDER.sub(lambda m: texts[m[1]], template)
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return page.replace(DATA_MARK, payload)
