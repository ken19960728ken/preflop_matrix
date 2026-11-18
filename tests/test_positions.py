from preflop_matrix.positions import assign_positions

SIX = [(1, "a"), (2, "b"), (3, "c"), (4, "d"), (5, "e"), (6, "f")]


def test_button_seat_one():
    assert assign_positions(SIX, 1) == {"b": "SB", "c": "BB", "d": "UTG", "e": "HJ", "f": "CO", "a": "BTN"}


def test_button_seat_in_the_middle_wraps_around():
    assert assign_positions(SIX, 4) == {"e": "SB", "f": "BB", "a": "UTG", "b": "HJ", "c": "CO", "d": "BTN"}


def test_button_on_last_seat():
    assert assign_positions(SIX, 6) == {"a": "SB", "b": "BB", "c": "UTG", "d": "HJ", "e": "CO", "f": "BTN"}


def test_seat_numbers_need_not_be_contiguous_or_sorted():
    seats = [(9, "f"), (2, "a"), (5, "c"), (3, "b"), (7, "e"), (6, "d")]
    assert assign_positions(seats, 5) == {"d": "SB", "e": "BB", "f": "UTG", "a": "HJ", "b": "CO", "c": "BTN"}


def test_not_six_players_is_none():
    assert assign_positions(SIX[:5], 1) is None
    assert assign_positions(SIX[:2], 1) is None


def test_button_seat_must_be_taken():
    assert assign_positions(SIX, 7) is None
