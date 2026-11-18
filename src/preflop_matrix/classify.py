"""Classify preflop decisions into two-player nodes.

A decision belongs to a node only when nobody besides the two players of that node has acted
voluntarily so far (folds do not count). Limps, cold calls, squeezes and cold 4bets therefore
drop the decision from every node.
"""
from typing import NamedTuple

from preflop_matrix.parser import Hand

OPEN, VS_OPEN, VS_3BET, VS_4BET, VS_5BET = "open", "vs_open", "vs_3bet", "vs_4bet", "vs_5bet"
NODES = (OPEN, VS_OPEN, VS_3BET, VS_4BET, VS_5BET)
CALL, RAISE = "call", "raise"


class Decision(NamedTuple):
    node: str
    player: str
    pos: str            # position of the player deciding
    vs: str | None      # position of the opponent whose raise is faced (None for open)
    action: str         # fold | call | raise (the next raise level: open / 3bet / 4bet / 5bet / 6bet)


def _node(raisers: list[str], active: set[str], player: str, limped: bool) -> tuple[str, str] | None:
    """(node, opponent) the player now decides in, or None. Opponent is a player name ("" for open)."""
    n = len(raisers)
    if n == 0:
        return (OPEN, "") if not active else None
    if limped:
        return None
    opener = raisers[0]
    if n == 1:
        return (VS_OPEN, opener) if player != opener and active == {opener} else None
    three_bettor = raisers[1]
    if active != {opener, three_bettor}:
        return None
    if n == 2 and player == opener:
        return VS_3BET, three_bettor
    if n == 3 and player == three_bettor and raisers[2] == opener:
        return VS_4BET, opener
    if n == 4 and player == opener and raisers[3] == three_bettor:
        return VS_5BET, three_bettor
    return None


def preflop_decisions(hand: Hand) -> list[Decision]:
    """Every decision of the hand that falls into one of the five nodes."""
    out: list[Decision] = []
    raisers: list[str] = []
    active: set[str] = set()
    limped = False
    current_to = last_size = hand.bb
    for a in hand.actions:
        if a.kind == "check":
            continue
        kind = a.kind
        if kind == "raise":
            # An all-in raise smaller than the last raise does not reopen the betting: it counts as a call.
            if a.allin and a.to_amount - current_to < last_size:
                kind = CALL
            else:
                last_size = a.to_amount - current_to
            current_to = a.to_amount
        node = _node(raisers, active, a.player, limped)
        if node:
            opponent = node[1]
            out.append(Decision(node[0], a.player, hand.positions[a.player],
                                hand.positions[opponent] if opponent else None, kind))
        if kind == CALL and not raisers:
            limped = True
        if kind != "fold":
            active.add(a.player)
        if kind == RAISE:
            raisers.append(a.player)
    return out
