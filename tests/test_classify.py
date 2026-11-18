import pytest

from helpers import calls, folds, make_hand, raises
from preflop_matrix.classify import preflop_decisions
from preflop_matrix.parser import parse_hand

OPEN_UTG_HJ = [("open", "UTG", None, "fold"), ("open", "HJ", None, "fold")]
FOLD_TO_CO = [folds("UTG"), folds("HJ")]


def decide(actions):
    hand = parse_hand(make_hand(actions))
    return [(d.node, d.pos, d.vs, d.action) for d in preflop_decisions(hand)]


def test_open_then_vs_open_for_each_later_player():
    assert decide(FOLD_TO_CO + [raises("CO", 2), folds("BTN"), folds("SB"), calls("BB")]) == OPEN_UTG_HJ + [
        ("open", "CO", None, "raise"), ("vs_open", "BTN", "CO", "fold"),
        ("vs_open", "SB", "CO", "fold"), ("vs_open", "BB", "CO", "call")]


def test_a_cold_caller_removes_the_decisions_behind_it():
    assert decide(FOLD_TO_CO + [raises("CO", 2), calls("BTN"), calls("SB"), calls("BB")]) == OPEN_UTG_HJ + [
        ("open", "CO", None, "raise"), ("vs_open", "BTN", "CO", "call")]


def test_vs_open_3bet_and_opener_facing_it():
    actions = [folds("UTG"), raises("HJ", 2), folds("CO"), folds("BTN"), folds("SB"), raises("BB", 9), folds("HJ")]
    assert decide(actions) == [
        ("open", "UTG", None, "fold"), ("open", "HJ", None, "raise"), ("vs_open", "CO", "HJ", "fold"),
        ("vs_open", "BTN", "HJ", "fold"), ("vs_open", "SB", "HJ", "fold"), ("vs_open", "BB", "HJ", "raise"),
        ("vs_3bet", "HJ", "BB", "fold")]


def test_walk_has_only_open_folds():
    assert decide([folds(p) for p in ("UTG", "HJ", "CO", "BTN", "SB")]) == [
        ("open", p, None, "fold") for p in ("UTG", "HJ", "CO", "BTN", "SB")]


def test_sb_limp_is_an_open_decision_and_the_bb_check_is_not_a_decision():
    assert decide([folds(p) for p in ("UTG", "HJ", "CO", "BTN")] + [calls("SB"), ("BB", "checks")]) == [
        ("open", p, None, "fold") for p in ("UTG", "HJ", "CO", "BTN")] + [("open", "SB", None, "call")]


def test_blind_vs_blind_chain():
    actions = [folds(p) for p in ("UTG", "HJ", "CO", "BTN")] + [raises("SB", 3), raises("BB", 10), calls("SB")]
    assert decide(actions)[-3:] == [("open", "SB", None, "raise"), ("vs_open", "BB", "SB", "raise"),
                                    ("vs_3bet", "SB", "BB", "call")]


def test_vs_3bet_heads_up_ignores_players_who_fold_in_between():
    assert decide(FOLD_TO_CO + [raises("CO", 2), raises("BTN", 7), folds("SB"), folds("BB"), calls("CO")]) == OPEN_UTG_HJ + [
        ("open", "CO", None, "raise"), ("vs_open", "BTN", "CO", "raise"), ("vs_3bet", "CO", "BTN", "call")]


@pytest.mark.parametrize("last, action", [(calls("CO"), "call"), (folds("CO"), "fold"), (raises("CO", 100, True), "raise")])
def test_vs_3bet_actions(last, action):
    got = decide(FOLD_TO_CO + [raises("CO", 2), raises("BTN", 7), folds("SB"), folds("BB"), last])
    assert got[-1] == ("vs_3bet", "CO", "BTN", action)


def test_vs_4bet_and_vs_5bet_chain():
    actions = FOLD_TO_CO + [raises("CO", 2), raises("BTN", 7), folds("SB"), folds("BB"),
                            raises("CO", 18), raises("BTN", 40), raises("CO", 100, True)]
    assert decide(actions)[3:] == [
        ("vs_open", "BTN", "CO", "raise"), ("vs_3bet", "CO", "BTN", "raise"),
        ("vs_4bet", "BTN", "CO", "raise"), ("vs_5bet", "CO", "BTN", "raise")]


def test_vs_4bet_fold_and_vs_5bet_call():
    base = FOLD_TO_CO + [raises("CO", 2), raises("BTN", 7), folds("SB"), folds("BB"), raises("CO", 18)]
    assert decide(base + [folds("BTN")])[-1] == ("vs_4bet", "BTN", "CO", "fold")
    assert decide(base + [raises("BTN", 40), calls("CO")])[-1] == ("vs_5bet", "CO", "BTN", "call")


def test_squeeze_removes_the_squeezer_and_the_opener_but_keeps_the_caller():
    actions = FOLD_TO_CO + [raises("CO", 2), calls("BTN"), raises("SB", 11), folds("BB"), folds("CO"), folds("BTN")]
    assert decide(actions) == OPEN_UTG_HJ + [("open", "CO", None, "raise"), ("vs_open", "BTN", "CO", "call")]


def test_cold_call_of_the_3bet_removes_the_opener_decision():
    actions = FOLD_TO_CO + [raises("CO", 2), raises("BTN", 7), calls("SB"), folds("BB"), calls("CO")]
    assert decide(actions) == OPEN_UTG_HJ + [("open", "CO", None, "raise"), ("vs_open", "BTN", "CO", "raise")]


def test_cold_4bet_removes_both_original_players():
    actions = FOLD_TO_CO + [raises("CO", 2), raises("BTN", 7), raises("SB", 25), folds("BB"), folds("CO"), folds("BTN")]
    assert decide(actions) == OPEN_UTG_HJ + [("open", "CO", None, "raise"), ("vs_open", "BTN", "CO", "raise")]


def test_third_player_in_the_pot_removes_vs_4bet():
    actions = FOLD_TO_CO + [raises("CO", 2), raises("BTN", 7), calls("SB"), folds("BB"), raises("CO", 20),
                            folds("SB"), folds("BTN")]
    assert [d for d in decide(actions) if d[0] in ("vs_3bet", "vs_4bet", "vs_5bet")] == []


def test_limp_removes_every_later_node_even_if_the_limper_reraises():
    actions = [calls("UTG"), raises("HJ", 4), folds("CO"), folds("BTN"), folds("SB"), folds("BB"), raises("UTG", 12), calls("HJ")]
    assert decide(actions) == [("open", "UTG", None, "call")]


def test_incomplete_all_in_raise_counts_as_a_call():
    actions = FOLD_TO_CO + [raises("CO", 2), raises("BTN", 2.5, True), folds("SB"), folds("BB"), calls("CO")]
    assert decide(actions) == OPEN_UTG_HJ + [("open", "CO", None, "raise"), ("vs_open", "BTN", "CO", "call")]


def test_decision_carries_the_player_name():
    hand = parse_hand(make_hand([folds(p) for p in ("UTG", "HJ", "CO", "BTN")] + [raises("SB", 3), folds("BB")], hero="SB"))
    assert [(d.player, d.pos) for d in preflop_decisions(hand)][4:] == [("Hero", "SB"), ("p_BB", "BB")]
