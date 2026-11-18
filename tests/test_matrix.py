import pytest

from helpers import calls, folds, make_hand, raises
from preflop_matrix.matrix import build_matrix
from preflop_matrix.parser import parse_hand
from preflop_matrix.ranges import load_ranges

SHARE = 1326


def build(ranges_folder, hands=(), hero="Hero"):
    return build_matrix([parse_hand(h) for h in hands], load_ranges(ranges_folder), hero)


def test_layout_has_every_cell(write_ranges):
    data = build(write_ranges({}))
    assert list(data["open"]) == ["UTG", "HJ", "CO", "BTN", "SB"]
    for node in ("vs_open", "vs_3bet", "vs_4bet", "vs_5bet"):
        assert len(data[node]) == 15 and "UTG>HJ" in data[node] and "SB>BB" in data[node] and "BB>UTG" not in data[node]
    assert data["open"]["UTG"] == {"th": None, "me": None, "pool": None}
    assert data["vs_5bet"]["UTG>BB"] == {"th": None, "me": None, "pool": None}


def test_open_theory_is_the_combo_share(write_ranges):
    data = build(write_ranges({"UTG Open 2bb": {"AA": 1, "KK": 0.5}}))
    assert data["open"]["UTG"]["th"]["r"] == pytest.approx(9 / SHARE)
    assert data["open"]["HJ"]["th"] is None


def test_vs_open_theory_needs_both_call_and_3bet(write_ranges):
    both = build(write_ranges({"BB vs UTG open 2bb call": {"AA": 0.5}, "BB vs UTG open 2bb 3bet 9bb": {"AA": 0.5, "KK": 1}}))
    assert both["vs_open"]["UTG>BB"]["th"] == {"c": pytest.approx(3 / SHARE), "r": pytest.approx(9 / SHARE)}
    only_call = build(write_ranges({"BB vs UTG open 2bb call": {"AA": 0.5}}))
    assert only_call["vs_open"]["UTG>BB"]["th"] is None


def test_vs_3bet_theory_is_conditional_on_the_open_range(write_ranges):
    data = build(write_ranges({"UTG Open 2bb": {"AA": 1, "KK": 1},
                               "UTG vs BB 3bet 10bb call": {"AA": 0.5},
                               "UTG vs BB 3bet 10bb 4bet 23bb": {"AA": 0.5, "KK": 1}}))
    assert data["vs_3bet"]["UTG>BB"]["th"] == {"c": pytest.approx(3 / 12), "r": pytest.approx(9 / 12)}


def test_later_street_weights_are_joint_and_capped_at_the_base(write_ranges):
    data = build(write_ranges({"UTG Open 2bb": {"AA": 0.5, "KK": 0.5},
                               "UTG vs BB 3bet 10bb call": {"AA": 0.9},
                               "UTG vs BB 3bet 10bb 4bet 23bb": {"KK": 0.25}}))
    assert data["vs_3bet"]["UTG>BB"]["th"] == {"c": pytest.approx(0.5), "r": pytest.approx(0.25)}


def test_vs_3bet_theory_missing_when_any_range_is_missing(write_ranges):
    data = build(write_ranges({"UTG vs BB 3bet 10bb call": {"AA": 1}, "UTG vs BB 3bet 10bb 4bet 23bb": {"AA": 1}}))
    assert data["vs_3bet"]["UTG>BB"]["th"] is None


def test_vs_4bet_theory_uses_the_3bet_range_as_base_and_adds_the_all_in_range(write_ranges):
    files = {"BB vs UTG open 2bb 3bet 9bb": {"AA": 1, "KK": 1}, "BB vs UTG 4bet 23bb call": {"KK": 1},
             "BB vs UTG 4bet 23bb 5bet 48bb": {"AA": 0.75}, "BB vs UTG 4bet 23bb 5bet all in": {"AA": 0.75}}
    th = build(write_ranges(files))["vs_4bet"]["UTG>BB"]["th"]
    assert th == {"c": pytest.approx(6 / 12), "r": pytest.approx(6 / 12)}


def test_vs_4bet_theory_works_with_only_one_5bet_file(write_ranges):
    files = {"BB vs UTG open 2bb 3bet 9bb": {"AA": 1, "KK": 1}, "BB vs UTG 4bet 23bb call": {"KK": 1},
             "BB vs UTG 4bet 23bb 5bet all in": {"AA": 0.5}}
    assert build(write_ranges(files))["vs_4bet"]["UTG>BB"]["th"]["r"] == pytest.approx(3 / 12)
    files.pop("BB vs UTG 4bet 23bb 5bet all in")
    assert build(write_ranges(files))["vs_4bet"]["UTG>BB"]["th"] is None


def test_observed_frequencies_split_me_and_pool(write_ranges):
    rest = [folds("HJ"), folds("CO"), folds("BTN"), folds("SB")]
    hands = [
        make_hand([raises("UTG", 2)] + rest + [calls("BB")], hand_id="A"),                      # Hero BB calls
        make_hand([raises("UTG", 2)] + rest + [raises("BB", 9), folds("UTG")], hand_id="B"),    # Hero BB 3bets
        make_hand([raises("UTG", 2)] + rest + [folds("BB")], hand_id="C", hero="SB"),           # pool BB folds
    ]
    data = build(write_ranges({}), hands)
    assert data["vs_open"]["UTG>BB"]["me"] == {"c": 0.5, "r": 0.5, "n": 2}
    assert data["vs_open"]["UTG>BB"]["pool"] == {"c": 0.0, "r": 0.0, "n": 1}
    assert data["open"]["UTG"]["pool"] == {"r": 1.0, "n": 3}
    assert data["open"]["UTG"]["me"] is None
    assert data["vs_3bet"]["UTG>BB"]["pool"] == {"c": 0.0, "r": 0.0, "n": 1}
    assert data["vs_open"]["UTG>BB"]["th"] is None


def test_open_rate_counts_limps_in_the_denominator(write_ranges):
    hands = [make_hand([folds("UTG"), folds("HJ"), folds("CO"), folds("BTN"), calls("SB"), ("BB", "checks")], hand_id="A"),
             make_hand([folds("UTG"), folds("HJ"), folds("CO"), folds("BTN"), raises("SB", 3), folds("BB")], hand_id="B"),
             make_hand([folds("UTG"), folds("HJ"), folds("CO"), folds("BTN"), folds("SB")], hand_id="C")]
    assert build(write_ranges({}), hands)["open"]["SB"]["pool"] == {"r": pytest.approx(1 / 3), "n": 3}


def test_vs_4bet_and_vs_5bet_cells_are_keyed_opener_first(write_ranges):
    hand = make_hand([folds("UTG"), folds("HJ"), raises("CO", 2), raises("BTN", 7), folds("SB"), folds("BB"),
                      raises("CO", 18), raises("BTN", 40), calls("CO")], hero="CO")
    data = build(write_ranges({}), [hand])
    assert data["vs_3bet"]["CO>BTN"]["me"] == {"c": 0.0, "r": 1.0, "n": 1}
    assert data["vs_4bet"]["CO>BTN"]["pool"] == {"c": 0.0, "r": 1.0, "n": 1}
    assert data["vs_5bet"]["CO>BTN"]["me"] == {"c": 1.0, "r": 0.0, "n": 1}


def test_meta(write_ranges):
    hands = [make_hand([], hand_id="A", day="2026/09/30"), make_hand([], hand_id="B", day="2026/10/06", hero="SB")]
    assert build(write_ranges({}), hands)["meta"] == {
        "hands": 2, "hero": "Hero", "hero_hands": 2, "date_from": "2026-09-30", "date_to": "2026-10-06"}
    assert build(write_ranges({}), hands, hero="Nobody")["meta"]["hero_hands"] == 0
