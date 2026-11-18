from decimal import Decimal

import pytest
from helpers import calls, folds, make_hand, raises

from preflop_matrix.parser import ParseError, TableSizeError, load_hands, parse_hand, split_hands


def five_handed(hand_id):
    return "\n".join(line for line in make_hand([], hand_id=hand_id).split("\n") if "p_UTG (" not in line)


def test_parse_hand_fields():
    hand = parse_hand(make_hand([folds("UTG"), raises("HJ", 2), folds("CO"), calls("BTN"), folds("SB"), folds("BB")],
                                hand_id="RC42", day="2026/09/30"))
    assert hand.hand_id == "RC42"
    assert hand.date == "2026-09-30"
    assert hand.bb == Decimal("0.1")
    assert hand.positions["Hero"] == "BB" and hand.positions["p_HJ"] == "HJ"
    assert [(a.player, a.kind) for a in hand.actions] == [
        ("p_UTG", "fold"), ("p_HJ", "raise"), ("p_CO", "fold"), ("p_BTN", "call"), ("p_SB", "fold"), ("Hero", "fold")]
    assert hand.actions[1].to_amount == Decimal("0.20")


def test_bb_is_the_header_big_blind_not_the_posted_amount():
    text = make_hand([folds("UTG")]).replace("Hero: posts big blind $0.1", "Hero: posts big blind $0.04 and is all-in")
    assert parse_hand(text).bb == Decimal("0.1")


def test_trailing_whitespace_is_ignored():
    text = make_hand([folds("UTG"), raises("HJ", 2)]).replace("p_UTG: folds", "p_UTG: folds   ").replace("\n", " \n")
    assert [a.kind for a in parse_hand(text).actions] == ["fold", "raise"]


def test_empty_button_seat_has_its_own_error():
    with pytest.raises(ParseError, match="button seat 9 is empty") as exc:
        parse_hand(make_hand([folds("UTG")], button=9))
    assert exc.type is ParseError


def test_wrong_table_size_message_names_the_player_count():
    with pytest.raises(TableSizeError, match="5 players"):
        parse_hand(five_handed("RC1"))


def test_positions_must_agree_with_who_posted_the_blinds():
    swapped = make_hand([folds("UTG")]).replace("p_SB: posts small blind", "p_UTG: posts small blind")
    with pytest.raises(ParseError, match="blinds"):
        parse_hand(swapped)
    no_sb = "\n".join(line for line in make_hand([folds("UTG")]).split("\n") if "small blind" not in line)
    with pytest.raises(ParseError, match="blinds"):
        parse_hand(no_sb)


def test_allin_flag_and_check_are_kept():
    hand = parse_hand(make_hand([raises("UTG", 100, allin=True), ("BB", "checks")]))
    assert hand.actions[0].allin is True and hand.actions[1].kind == "check"


def test_postflop_lines_are_not_read():
    text = make_hand([raises("CO", 2), folds("BTN"), folds("SB"), calls("BB")],
                     extra_lines=["*** FLOP *** [2c 7d 9h]", "garbage that is not a real action"])
    assert len(parse_hand(text).actions) == 4


@pytest.mark.parametrize("mangle", [
    lambda t: t.replace("Poker Hand #", "Poker Game #"),
    lambda t: t.replace("*** HOLE CARDS ***\n", ""),
    lambda t: t.replace("*** SUMMARY ***", "*** SUMMARY **"),
    lambda t: t.replace("p_UTG: folds", "p_UTG: does a handstand"),
    lambda t: t.replace("p_UTG: folds", "ghost: folds"),
    lambda t: t.replace("big blind", "huge blind"),
])
def test_unparseable_hand_raises_parse_error(mangle):
    with pytest.raises(ParseError):
        parse_hand(mangle(make_hand([folds("UTG"), raises("HJ", 2)])))


def test_not_six_players_is_table_size_error():
    with pytest.raises(TableSizeError):
        parse_hand(five_handed("RC1"))


def test_split_hands():
    text = make_hand([], hand_id="RC1") + make_hand([], hand_id="RC2")
    assert len(split_hands(text)) == 2


def test_load_hands_recurses_dedupes_and_counts(tmp_path):
    (tmp_path / "gg" / "sub").mkdir(parents=True)
    ok = make_hand([folds("UTG")], hand_id="RC1")
    (tmp_path / "gg" / "a.txt").write_text(ok + make_hand([folds("UTG")], hand_id="RC2"))
    (tmp_path / "gg" / "sub" / "b.txt").write_text(ok)                       # duplicate of RC1
    (tmp_path / "gg" / "sub" / "c.txt").write_text(make_hand([], hand_id="RC3").replace("big blind", "huge blind"))
    (tmp_path / "d.txt").write_text(five_handed("RC4"))
    (tmp_path / "ignored.csv").write_text(ok)
    result = load_hands(tmp_path)
    assert sorted(h.hand_id for h in result.hands) == ["RC1", "RC2"]
    assert (result.files, result.duplicates, result.unparseable, result.not_six_max) == (4, 1, 1, 1)
    assert len(result.error_samples) == 1 and "c.txt" in result.error_samples[0]


def test_duplicate_unparseable_hand_is_counted_once(tmp_path):
    bad = make_hand([], hand_id="RC7").replace("big blind", "huge blind")
    (tmp_path / "a.txt").write_text(bad)
    (tmp_path / "b.txt").write_text(bad)
    result = load_hands(tmp_path)
    assert (result.unparseable, result.duplicates, len(result.error_samples)) == (1, 1, 1)


def test_load_hands_reads_a_byte_order_mark(tmp_path):
    (tmp_path / "a.txt").write_bytes(("\ufeff" + make_hand([folds("UTG")], hand_id="RC1")).encode("utf-8"))
    assert [h.hand_id for h in load_hands(tmp_path).hands] == ["RC1"]


def test_load_hands_empty_folder(tmp_path):
    result = load_hands(tmp_path)
    assert result.hands == [] and result.files == 0
