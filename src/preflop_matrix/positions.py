"""Seat → table position for a 6-max hand."""

POSITIONS = ("UTG", "HJ", "CO", "BTN", "SB", "BB")
POSITION_INDEX = {p: i for i, p in enumerate(POSITIONS)}
TABLE_SIZE = 6
# Positions in dealing order, starting with the seat left of the button.
_FROM_BUTTON = ("SB", "BB", "UTG", "HJ", "CO", "BTN")


def assign_positions(seats: list[tuple[int, str]], button_seat: int) -> dict[str, str] | None:
    """Return {player: position}, or None unless exactly six players sit and the button seat is taken."""
    if len(seats) != TABLE_SIZE or all(num != button_seat for num, _ in seats):
        return None
    ordered = sorted(seats)
    after = [s for s in ordered if s[0] > button_seat]
    upto = [s for s in ordered if s[0] <= button_seat]
    return {name: pos for (_, name), pos in zip(after + upto, _FROM_BUTTON)}
