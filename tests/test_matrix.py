import pytest
from helpers import calls, folds, make_hand, raises

from preflop_matrix.matrix import build_matrix, missing_actions
from preflop_matrix.parser import parse_hand
from preflop_matrix.ranges import HANDS, load_ranges

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


def test_vs_open_theory(write_ranges):
    both = build(write_ranges({"BB vs UTG open 2bb call": {"AA": 0.5}, "BB vs UTG open 2bb 3bet 9bb": {"AA": 0.5, "KK": 1}}))
    assert both["vs_open"]["UTG>BB"]["th"] == {"c": pytest.approx(3 / SHARE), "r": pytest.approx(9 / SHARE)}


def test_vs_open_missing_action_counts_as_zero(write_ranges):
    only_call = build(write_ranges({"BB vs UTG open 2bb call": {"AA": 0.5}}))
    assert only_call["vs_open"]["UTG>BB"]["th"] == {"c": pytest.approx(3 / SHARE), "r": 0.0}
    only_raise = build(write_ranges({"BB vs UTG open 2bb 3bet 9bb": {"AA": 0.5}}))
    assert only_raise["vs_open"]["UTG>BB"]["th"] == {"c": 0.0, "r": pytest.approx(3 / SHARE)}
    assert build(write_ranges({}))["vs_open"]["UTG>BB"]["th"] is None


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


def test_vs_3bet_missing_action_counts_as_zero_but_the_base_is_required(write_ranges):
    base = {"UTG Open 2bb": {"AA": 1, "KK": 1}}
    only_call = build(write_ranges({**base, "UTG vs BB 3bet 10bb call": {"AA": 1}}))
    assert only_call["vs_3bet"]["UTG>BB"]["th"] == {"c": pytest.approx(0.5), "r": 0.0}
    only_4bet = build(write_ranges({**base, "UTG vs BB 3bet 10bb 4bet 23bb": {"KK": 1}}))
    assert only_4bet["vs_3bet"]["UTG>BB"]["th"] == {"c": 0.0, "r": pytest.approx(0.5)}
    assert build(write_ranges({"UTG vs BB 3bet 10bb call": {"AA": 1}}))["vs_3bet"]["UTG>BB"]["th"] is None
    assert build(write_ranges(base))["vs_3bet"]["UTG>BB"]["th"] is None


def test_vs_3bet_4bet_all_in_file_is_added_to_the_4bet_range(write_ranges):
    files = {"UTG Open 2bb": {"AA": 1, "KK": 1}, "UTG vs BB 3bet 10bb call": {"KK": 1},
             "UTG vs BB 3bet 10bb 4bet 23bb": {"AA": 0.25}, "UTG vs BB 3bet 10bb 4bet all in": {"AA": 0.5}}
    assert build(write_ranges(files))["vs_3bet"]["UTG>BB"]["th"] == {"c": pytest.approx(0.5), "r": pytest.approx(0.375)}
    del files["UTG vs BB 3bet 10bb 4bet 23bb"]
    assert build(write_ranges(files))["vs_3bet"]["UTG>BB"]["th"]["r"] == pytest.approx(0.25)


def test_missing_actions_report(write_ranges):
    book = load_ranges(write_ranges({
        "BB vs UTG open 2bb call": {"AA": 1},
        "UTG Open 2bb": {"AA": 1}, "UTG vs HJ 3bet 6.5bb 4bet 18bb": {"AA": 1},
        "BB vs HJ open 2bb 3bet 10bb": {"AA": 1}, "BB vs HJ 4bet 23bb call": {"AA": 1},
        "HJ vs CO 3bet 6.5bb call": {"AA": 1},
        "BB vs CO open 2bb call": {"AA": 1}, "BB vs CO open 2bb 3bet 10bb": {"AA": 1},
    }))
    assert missing_actions(book) == ["vs_open UTG>BB 缺 3bet，已當 0", "vs_open HJ>BB 缺 call，已當 0",
                                     "vs_3bet UTG>HJ 缺 call，已當 0", "vs_4bet HJ>BB 缺 5bet，已當 0"]


def test_vs_4bet_theory_uses_the_3bet_range_as_base_and_adds_the_all_in_range(write_ranges):
    files = {"BB vs UTG open 2bb 3bet 9bb": {"AA": 1, "KK": 1}, "BB vs UTG 4bet 23bb call": {"KK": 1},
             "BB vs UTG 4bet 23bb 5bet 48bb": {"AA": 0.75}, "BB vs UTG 4bet 23bb 5bet all in": {"AA": 0.75}}
    th = build(write_ranges(files))["vs_4bet"]["UTG>BB"]["th"]
    assert th == {"c": pytest.approx(6 / 12), "r": pytest.approx(6 / 12)}


def test_vs_4bet_theory_with_only_one_5bet_file_or_none(write_ranges):
    files = {"BB vs UTG open 2bb 3bet 9bb": {"AA": 1, "KK": 1}, "BB vs UTG 4bet 23bb call": {"KK": 1},
             "BB vs UTG 4bet 23bb 5bet all in": {"AA": 0.5}}
    assert build(write_ranges(files))["vs_4bet"]["UTG>BB"]["th"]["r"] == pytest.approx(3 / 12)
    del files["BB vs UTG 4bet 23bb 5bet all in"]
    assert build(write_ranges(files))["vs_4bet"]["UTG>BB"]["th"] == {"c": pytest.approx(0.5), "r": 0.0}


def test_theory_above_one_is_clamped_with_a_warning(write_ranges):
    everything = {h: 1 for h in HANDS}
    data = build(write_ranges({"BB vs UTG open 2bb call": everything, "BB vs UTG open 2bb 3bet 9bb": everything}))
    th = data["vs_open"]["UTG>BB"]["th"]
    assert th["c"] + th["r"] <= 1 + 1e-9
    assert th["c"] == pytest.approx(th["r"])
    assert len(data["meta"]["warnings"]) == 1 and "vs_open UTG>BB" in data["meta"]["warnings"][0]


def test_theory_within_tolerance_is_left_alone(write_ranges):
    data = build(write_ranges({"UTG Open 2bb": {"AA": 1}, "UTG vs BB 3bet 10bb call": {"AA": 0.5},
                               "UTG vs BB 3bet 10bb 4bet 23bb": {"AA": 0.5}}))
    assert data["vs_3bet"]["UTG>BB"]["th"] == {"c": pytest.approx(0.5), "r": pytest.approx(0.5)}
    assert data["meta"]["warnings"] == []


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
        "hands": 2, "hero": "Hero", "hero_hands": 2, "warnings": [], "date_from": "2026-09-30", "date_to": "2026-10-06"}
    assert build(write_ranges({}), hands, hero="Nobody")["meta"]["hero_hands"] == 0


def chain_hands():
    """Hero is CO: opens, gets 3bet by BTN, 4bets, gets 5bet (called), and folds the other CO open."""
    rest = [folds("UTG"), folds("HJ")]
    full = rest + [raises("CO", 2), raises("BTN", 7), folds("SB"), folds("BB"), raises("CO", 18), raises("BTN", 40), calls("CO")]
    other = rest + [raises("CO", 2), folds("BTN"), folds("SB"), folds("BB")]
    return [make_hand(full, hand_id="A", hero="CO"), make_hand(other, hand_id="B", hero="CO"),
            make_hand(other, hand_id="C", hero="SB"), make_hand(other, hand_id="D", hero="SB")]


def test_absolute_chains_the_conditional_frequencies(write_ranges):
    files = {"CO Open 2bb": {"AA": 1, "KK": 1}, "CO vs BTN 3bet 7bb call": {"AA": 1}, "CO vs BTN 3bet 7bb 4bet 20bb": {"KK": 1}}
    data = build(write_ranges(files), chain_hands())
    ab = data["absolute"]
    # me opened in 2 of 2 hands; 1 of those was 3bet by BTN and I 4bet it
    assert ab["vs_3bet"]["CO>BTN"]["me"] == {"reach": 1.0, "f": 0.0, "c": 0.0, "r": 1.0, "n": 1}
    th = ab["vs_3bet"]["CO>BTN"]["th"]
    assert th["reach"] == pytest.approx(12 / SHARE) and th["c"] == pytest.approx(0.5 * 12 / SHARE)
    # the pool BTN faces the CO open in all 4 hands and 3bets in 1 (hand A), then 5bets the 4bet
    assert ab["vs_4bet"]["CO>BTN"]["pool"]["reach"] == pytest.approx(0.25)
    assert ab["vs_4bet"]["CO>BTN"]["pool"]["r"] == pytest.approx(0.25)
    assert ab["vs_5bet"]["CO>BTN"]["me"] == {"reach": 1.0 * 1.0, "f": 0.0, "c": 1.0, "r": 0.0, "n": 1}


def test_absolute_has_everything_needed_and_parts_add_up(write_ranges):
    files = {"CO Open 2bb": {"AA": 1, "KK": 1}, "CO vs BTN 3bet 7bb call": {"AA": 1}, "CO vs BTN 3bet 7bb 4bet 20bb": {"KK": 1}}
    data = build(write_ranges(files), chain_hands())
    for node in ("vs_3bet", "vs_4bet", "vs_5bet"):
        assert len(data["absolute"][node]) == 15
        for row in data["absolute"][node].values():
            assert set(row) <= {"th", "me", "pool"}
            for entry in row.values():
                assert entry["f"] + entry["c"] + entry["r"] == pytest.approx(entry["reach"])
    assert "th" not in data["absolute"]["vs_5bet"]["CO>BTN"]
    assert data["absolute"]["vs_3bet"]["UTG>BB"] == {}


def test_absolute_needs_the_previous_street_to_have_data(write_ranges):
    actions = [folds("UTG"), folds("HJ"), raises("CO", 2), raises("BTN", 7), folds("SB"), folds("BB"), calls("CO")]
    data = build(write_ranges({}), [make_hand(actions, hero="CO")])
    assert "me" in data["absolute"]["vs_3bet"]["CO>BTN"]
    assert "me" not in data["absolute"]["vs_4bet"]["CO>BTN"]


def test_vs_5bet_never_has_theory_even_with_vs_4bet_files(write_ranges):
    files = {"BB vs UTG open 2bb 3bet 9bb": {"AA": 1, "KK": 1}, "BB vs UTG 4bet 23bb call": {"KK": 1}}
    data = build(write_ranges(files))
    assert data["vs_4bet"]["UTG>BB"]["th"] == {"c": pytest.approx(0.5), "r": 0.0}
    assert data["vs_5bet"]["UTG>BB"]["th"] is None
    assert all(cell["th"] is None for cell in data["vs_5bet"].values())
    assert data["meta"]["warnings"] == []


def test_absolute_vs_5bet_carries_no_theory_even_when_its_reach_chain_exists(write_ranges):
    files = {"UTG Open 2bb": {"AA": 1, "KK": 1}, "UTG vs BB 3bet 9bb call": {"AA": 0.5},
             "UTG vs BB 3bet 9bb 4bet 22bb": {"AA": 0.5},
             "BB vs UTG open 2bb 3bet 9bb": {"AA": 1, "KK": 1}, "BB vs UTG 4bet 23bb call": {"KK": 1}}
    absolute = build(write_ranges(files))["absolute"]
    assert "th" in absolute["vs_3bet"]["UTG>BB"] and "th" in absolute["vs_4bet"]["UTG>BB"]
    assert all("th" not in row for row in absolute["vs_5bet"].values())


def test_vs_5bet_theory_is_not_scaled_or_warned_about(write_ranges):
    everything = {h: 1 for h in HANDS}
    files = {"BB vs UTG open 2bb 3bet 9bb": everything, "BB vs UTG 4bet 23bb call": everything,
             "BB vs UTG 4bet 23bb 5bet 48bb": everything}
    data = build(write_ranges(files))
    assert data["vs_5bet"]["UTG>BB"]["th"] is None
    assert [w for w in data["meta"]["warnings"] if "vs_5bet" in w] == []
