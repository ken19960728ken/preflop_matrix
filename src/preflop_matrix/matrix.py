"""Build the position-vs-position frequency matrices (theory / Hero / pool).

Output layout (same as the HTML template expects):
  open:    {pos: {th, me, pool}}                        th={r}, me/pool={r, n}
  vs_*:    {"<raiser>><other>": {th, me, pool}}         th={c, r}, me/pool={c, r, n}; fold = 1 - c - r
A missing theory or no observations is None.
"""
from collections import Counter
from collections.abc import Iterable

from preflop_matrix.classify import CALL, NODES, OPEN, RAISE, VS_3BET, VS_4BET, VS_OPEN, preflop_decisions
from preflop_matrix.parser import Hand
from preflop_matrix.positions import POSITIONS
from preflop_matrix.ranges import HANDS, Range, RangeBook, combos, total_share

ME, POOL = "me", "pool"


def _cell_key(node: str, pos: str, vs: str | None) -> str:
    """'<raiser>><other>' with the earlier position first."""
    if node == OPEN:
        return pos
    return f"{vs}>{pos}" if node in (VS_OPEN, VS_4BET) else f"{pos}>{vs}"


def tally(hands: Iterable[Hand], hero: str) -> tuple[dict[tuple[str, str, str], Counter], int]:
    """Count decisions per (node, cell, me|pool); also return the number of hands the hero played in."""
    counts: dict[tuple[str, str, str], Counter] = {}
    hero_hands = 0
    for hand in hands:
        hero_hands += hero in hand.positions
        for d in preflop_decisions(hand):
            who = ME if d.player == hero else POOL
            counts.setdefault((d.node, _cell_key(d.node, d.pos, d.vs), who), Counter())[d.action] += 1
    return counts, hero_hands


def _conditional(base: Range, call: Range, raise_: Range) -> dict[str, float] | None:
    """Call / raise shares of the hands in `base`.

    The call / raise range files of a later street give a hand's weight over all deals (the base
    range already filtered the hands), so each is capped at the base weight before it is divided by it.
    """
    size = sum(base[h] * combos(h) for h in HANDS)
    if size == 0:
        return None
    return {"c": sum(min(call[h], base[h]) * combos(h) for h in HANDS) / size,
            "r": sum(min(raise_[h], base[h]) * combos(h) for h in HANDS) / size}


def _union(*ranges: Range | None) -> Range | None:
    present = [r for r in ranges if r]
    return {h: min(1.0, sum(r[h] for r in present)) for h in HANDS} if present else None


def _theory(node: str, a: str, b: str, book: RangeBook) -> dict[str, float] | None:
    """Theory for the cell where `a` is the earlier position and `b` the later one."""
    if node == VS_OPEN:
        call, three_bet = book.get(VS_OPEN, b, a, "call"), book.get(VS_OPEN, b, a, "3bet")
        return {"c": total_share(call), "r": total_share(three_bet)} if call and three_bet else None
    if node == VS_3BET:
        base, call, four_bet = book.get(OPEN, a, None, "raise"), book.get(VS_3BET, a, b, "call"), book.get(VS_3BET, a, b, "4bet")
        return _conditional(base, call, four_bet) if base and call and four_bet else None
    if node == VS_4BET:
        base, call = book.get(VS_OPEN, b, a, "3bet"), book.get(VS_4BET, b, a, "call")
        five_bet = _union(book.get(VS_4BET, b, a, "5bet"), book.get(VS_4BET, b, a, "5bet_allin"))
        return _conditional(base, call, five_bet) if base and call and five_bet else None
    return None


def _open_cell(pos: str, counts: dict, book: RangeBook) -> dict:
    rng = book.get(OPEN, pos, None, "raise")
    cell: dict = {"th": {"r": total_share(rng)} if rng else None}
    for who in (ME, POOL):
        counter = counts.get((OPEN, pos, who))
        n = sum(counter.values()) if counter else 0
        cell[who] = {"r": counter[RAISE] / n, "n": n} if n else None
    return cell


def _pair_cell(node: str, a: str, b: str, counts: dict, book: RangeBook) -> dict:
    cell: dict = {"th": _theory(node, a, b, book)}
    for who in (ME, POOL):
        counter = counts.get((node, f"{a}>{b}", who))
        n = sum(counter.values()) if counter else 0
        cell[who] = {"c": counter[CALL] / n, "r": counter[RAISE] / n, "n": n} if n else None
    return cell


def build_matrix(hands: list[Hand], book: RangeBook, hero: str) -> dict:
    counts, hero_hands = tally(hands, hero)
    data: dict = {"open": {p: _open_cell(p, counts, book) for p in POSITIONS[:-1]}}
    for node in NODES[1:]:
        data[node] = {f"{a}>{b}": _pair_cell(node, a, b, counts, book)
                      for i, a in enumerate(POSITIONS[:-1]) for b in POSITIONS[i + 1:]}
    dates = sorted(h.date for h in hands)
    data["meta"] = {"hands": len(hands), "hero": hero, "hero_hands": hero_hands,
                    "date_from": dates[0] if dates else "", "date_to": dates[-1] if dates else ""}
    return data
