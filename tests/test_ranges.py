import pytest
from helpers import range_text

from preflop_matrix.ranges import HANDS, RangeKey, combos, hand_class, load_ranges, parse_filename, parse_range_text, total_share


def test_hand_classes():
    assert len(HANDS) == 169 and len(set(HANDS)) == 169
    assert sum(combos(h) for h in HANDS) == 1326
    assert hand_class("Kh", "As") == "AKo"
    assert hand_class("Ks", "As") == "AKs"
    assert hand_class("9d", "9c") == "99"


def test_parse_range_text_fractions_per_class():
    rng = parse_range_text(range_text({"AA": 1, "AKs": 0.5, "AKo": 0.25, "72o": 1}))
    assert rng["AA"] == 1 and rng["AKs"] == 0.5 and rng["AKo"] == 0.25 and rng["72o"] == 1
    assert rng["KK"] == 0 and len(rng) == 169


def test_missing_weight_defaults_to_one_and_class_weight_is_capped():
    assert parse_range_text("AsAh,AsAd")["AA"] == pytest.approx(2 / 6)
    assert parse_range_text(range_text({"AA": 2}))["AA"] == 1


@pytest.mark.parametrize("text", [
    "AsA: 1", "ZsAh: 1", "AsAh: lots", "AsAh: nan", "AsAh: inf", "AsAh: -0.5",
    "AxAh: 1", "AsAs: 1", "AsAh: 1,AhAs: 0.5", "AsAh: 1,AsAh: 1",
])
def test_bad_range_text_is_a_value_error(text):
    with pytest.raises(ValueError):
        parse_range_text(text)


def test_total_share():
    assert total_share(parse_range_text(range_text({"AA": 1, "KK": 0.5}))) == pytest.approx(9 / 1326)


@pytest.mark.parametrize("stem, key", [
    ("BTN Open 2bb", RangeKey("open", "BTN", None, "raise")),
    ("btn open 2BB", RangeKey("open", "BTN", None, "raise")),
    ("bb VS btn OPEN 2bb CALL", RangeKey("vs_open", "BB", "BTN", "call")),
    ("Btn vs Bb 3Bet 9.5bb 4Bet 22bb", RangeKey("vs_3bet", "BTN", "BB", "4bet")),
    ("Bb vs Btn 4Bet 22bb 5Bet All In", RangeKey("vs_4bet", "BB", "BTN", "5bet_allin")),
    ("BTN vs BB 3bet 9.5bb 4bet all in", RangeKey("vs_3bet", "BTN", "BB", "4bet_allin")),
    ("BTN vs BB 3bet 9.5bb 4bet allin", RangeKey("vs_3bet", "BTN", "BB", "4bet_allin")),
    ("BTN vs BB 3bet 9.5bb 4bet 22bb all in", RangeKey("vs_3bet", "BTN", "BB", "4bet_allin")),
    ("SB Open 3bb", RangeKey("open", "SB", None, "raise")),
    ("BB vs BTN open 2bb call", RangeKey("vs_open", "BB", "BTN", "call")),
    ("BB vs BTN open 2bb 3bet 9.5bb", RangeKey("vs_open", "BB", "BTN", "3bet")),
    ("BB vs HJ open 2bb 3b 10bb", RangeKey("vs_open", "BB", "HJ", "3bet")),
    ("BB vs UTG open call", RangeKey("vs_open", "BB", "UTG", "call")),
    ("BB vs UTG open 3bet 10bb", RangeKey("vs_open", "BB", "UTG", "3bet")),
    ("SB vs CO open 2bb call", RangeKey("vs_open", "SB", "CO", "call")),
    ("BTN vs BB 3bet 9.5bb call", RangeKey("vs_3bet", "BTN", "BB", "call")),
    ("BTN vs BB 3bet 9.5bb 4bet 22bb", RangeKey("vs_3bet", "BTN", "BB", "4bet")),
    ("BB vs BTN 4bet 22bb call", RangeKey("vs_4bet", "BB", "BTN", "call")),
    ("BB vs BTN 4bet 22bb 5bet 5bet 46bb", RangeKey("vs_4bet", "BB", "BTN", "5bet")),
    ("BB vs UTG 4bet 23bb 5bet 48.5bb", RangeKey("vs_4bet", "BB", "UTG", "5bet")),
    ("BTN vs UTG 4bet 5bet 40bb", RangeKey("vs_4bet", "BTN", "UTG", "5bet")),
    ("BB vs BTN 4bet 22bb 5bet all in", RangeKey("vs_4bet", "BB", "BTN", "5bet_allin")),
    ("BTN  Open   2bb", RangeKey("open", "BTN", None, "raise")),
])
def test_two_player_file_names_map_to_nodes(stem, key):
    assert parse_filename(stem) == key


@pytest.mark.parametrize("stem", [
    "BB vs BTN open 2bb SB call call",
    "BB vs BTN open 2bb SB call squeeze 12.5bb",
    "BB vs BTN open 2bb SB 3bet 8.5bb 4bet 19.5bb",
    "BB vs UTG open 2bb HJ call CO call squeeze 12.5bb",
    "BTN vs SB 3bet 8.5bb BB 4bet 19.5bb 5bet 39bb",
    "CO vs HJ 3bet UTG 6.5bb 4bet 15bb",
    "UTG vs HJ 3bet CO 4bet BB 5bet all in",
    "BTN vs SB call BB squeeze 12.5bb call",
    "BTN vs UTG open HJ 3bet CO 4bet 5bet 30bb",
    "BTN vs BB 5bet 46bb all in",
    "CO vs BB 5bet all in call",
    "SB vs BTN 6bet all in call",
    "UTG vs BB open 2bb call",
    "BTN vs BTN open 2bb call",
    "BB vs UTG 4bet 23bb 5bet 48.5bb extra",
    "notes",
])
def test_multiway_and_unknown_file_names_are_ignored(stem):
    assert parse_filename(stem) is None


def test_load_ranges_buckets_every_file(tmp_path):
    (tmp_path / "sub").mkdir()
    files = {"UTG Open 2bb": "AsAh: 1", "BB vs UTG open 2bb call": "KsKh: 1", "BB vs UTG open call": "QsQh: 1",
             "BB vs UTG open 2bb SB call call": "JsJh: 1", "BTN Open 2bb": "AsA: 1"}
    for stem, text in files.items():
        (tmp_path / "sub" / f"{stem}.txt").write_text(text)
    (tmp_path / "sub" / "readme.md").write_text("not a range")
    book = load_ranges(tmp_path)
    assert book.files == 5
    assert set(book.ranges) == {RangeKey("open", "UTG", None, "raise"), RangeKey("vs_open", "BB", "UTG", "call")}
    assert book.get("vs_open", "BB", "UTG", "call")["KK"] == pytest.approx(1 / 6)
    assert book.duplicates == ["BB vs UTG open call.txt"]
    assert book.ignored == ["BB vs UTG open 2bb SB call call.txt"]
    assert len(book.unreadable) == 1 and "BTN Open 2bb.txt" in book.unreadable[0]
    assert book.get("open", "BTN", None, "raise") is None


def test_files_with_a_byte_order_mark_are_read(tmp_path):
    (tmp_path / "UTG Open 2bb.txt").write_bytes("\ufeffAsAh: 1".encode("utf-8"))
    assert load_ranges(tmp_path).get("open", "UTG", None, "raise")["AA"] == pytest.approx(1 / 6)


def test_a_file_with_a_bad_weight_is_unreadable_not_fatal(tmp_path):
    (tmp_path / "UTG Open 2bb.txt").write_text("AsAh: nan")
    (tmp_path / "HJ Open 2bb.txt").write_text("AsAh: 1")
    book = load_ranges(tmp_path)
    assert list(book.ranges) == [RangeKey("open", "HJ", None, "raise")] and len(book.unreadable) == 1
