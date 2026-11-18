"""Command line entry point: preflop-matrix --hands DIR --ranges DIR -o out.html."""
import argparse
import json
import sys
from pathlib import Path

from preflop_matrix.matrix import build_matrix
from preflop_matrix.parser import LoadResult, load_hands
from preflop_matrix.ranges import RangeBook, load_ranges
from preflop_matrix.render import DEFAULT_TITLE, render_html

EXIT_BAD_INPUT, EXIT_FAILED = 2, 1


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="preflop-matrix", description="6-max 翻前位置矩陣熱力圖（理論 / Hero / 玩家池）")
    p.add_argument("--hands", required=True, metavar="DIR", help="GG 手牌資料夾（遞迴掃描 .txt）")
    p.add_argument("--ranges", required=True, metavar="DIR", help="理論範圍資料夾（.txt）")
    p.add_argument("-o", "--out", default="preflop_matrix.html", metavar="FILE", help="輸出 HTML（預設 preflop_matrix.html）")
    p.add_argument("--hero", default="Hero", help="Hero 的玩家名稱（預設 Hero）")
    p.add_argument("--title", default=DEFAULT_TITLE, help=f"頁面標題（預設 {DEFAULT_TITLE}）")
    p.add_argument("--json", dest="json_path", metavar="PATH", help="另存矩陣資料 JSON")
    return p


def _error(message: str) -> None:
    print(f"錯誤：{message}", file=sys.stderr)


def _hands_summary(r: LoadResult) -> list[str]:
    lines = [f"手牌：掃描 {r.files} 個檔案，採用 {len(r.hands)} 手；重複略過 {r.duplicates}、"
             f"非 6 人桌排除 {r.not_six_max}、無法解析略過 {r.unparseable}、無法讀取的檔案 {r.unreadable_files}"]
    lines += [f"  無法解析範例：{s}" for s in r.error_samples]
    return lines


def _ranges_summary(book: RangeBook) -> list[str]:
    lines = [f"理論範圍：{book.files} 個檔案，對應到節點 {len(book.ranges)} 個；"
             f"忽略（多人或不認得）{len(book.ignored)}、重複 {len(book.duplicates)}、無法讀取 {len(book.unreadable)}"]
    lines += [f"  無法讀取：{s}" for s in book.unreadable]
    lines += [f"  重複的節點檔（只用第一個）：{s}" for s in book.duplicates]
    return lines


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    hands_dir, ranges_dir = Path(args.hands).expanduser(), Path(args.ranges).expanduser()
    for label, path in (("手牌", hands_dir), ("理論範圍", ranges_dir)):
        if not path.is_dir():
            _error(f"{label}資料夾不存在或不是資料夾：{path}")
            return EXIT_BAD_INPUT

    loaded = load_hands(hands_dir)
    print("\n".join(_hands_summary(loaded)))
    if not loaded.hands:
        _error(f"{hands_dir} 底下沒有可用的手牌（需要 GG 格式、6 人桌的 .txt）")
        return EXIT_FAILED
    book = load_ranges(ranges_dir)
    print("\n".join(_ranges_summary(book)))
    if book.files == 0:
        _error(f"{ranges_dir} 底下沒有 .txt 範圍檔")
        return EXIT_FAILED

    data = build_matrix(loaded.hands, book, args.hero)
    if data["meta"]["hero_hands"] == 0:
        print(f"警告：所有手牌都沒有名為 {args.hero!r} 的玩家，「我」欄會是空的（可用 --hero 指定）", file=sys.stderr)
    try:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_html(data, args.title), encoding="utf-8")
        if args.json_path:
            json_path = Path(args.json_path).expanduser()
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as err:
        _error(f"無法寫入輸出：{err}")
        return EXIT_FAILED
    print(f"已輸出：{out}" + (f"、{args.json_path}" if args.json_path else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
