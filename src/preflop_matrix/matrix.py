"""Build the position-vs-position frequency matrices (theory / Hero / pool).

Output layout (same as the HTML template expects):
  open:      {pos: {th, me, pool}}                      th={r}, me/pool={r, n}
  vs_*:      {"<raiser>><other>": {th, me, pool}}       th={c, r}, me/pool={c, r, n}; fold = 1 - c - r
  absolute:  {vs_3bet|vs_4bet|vs_5bet: {key: {th|me|pool: {reach, f, c, r, n}}}}
             the same frequencies as a share of all dealt hands (the conditional frequency times the
             probability of reaching the node)
  meta:      hands, hero, hero_hands, date_from, date_to, warnings
A missing theory or no observations is None. vs_5bet has no theory: only me / pool.
"""
from collections import Counter
from collections.abc import Iterable

from preflop_matrix.classify import CALL, NODES, OPEN, RAISE, VS_3BET, VS_4BET, VS_5BET, VS_OPEN, preflop_decisions
from preflop_matrix.parser import Hand
from preflop_matrix.positions import POSITIONS
from preflop_matrix.ranges import HANDS, Range, RangeBook, combos, total_share

ME, POOL = "me", "pool"
WHO = ("th", ME, POOL)
SUM_TOLERANCE = 1e-6
ZERO: Range = {h: 0.0 for h in HANDS}
# the two actions a theory cell is made of, per node
ACTION_NAMES = {VS_OPEN: ("call", "3bet"), VS_3BET: ("call", "4bet"), VS_4BET: ("call", "5bet")}


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


def _union(*ranges: Range | None) -> Range | None:
    present = [r for r in ranges if r]
    return {h: min(1.0, sum(r[h] for r in present)) for h in HANDS} if present else None


def _inputs(node: str, a: str, b: str, book: RangeBook) -> tuple[Range | None, tuple[Range | None, Range | None]]:
    """(base range, (first action range, second action range)) for the cell where `a` is the earlier position.

    vs_open has no base range (the actions are shares of all hands). vs_5bet has no theory at all.
    """
    if node == VS_5BET:
        return None, (None, None)
    if node == VS_OPEN:
        return None, (book.get(VS_OPEN, b, a, "call"), book.get(VS_OPEN, b, a, "3bet"))
    if node == VS_3BET:
        return (book.get(OPEN, a, None, "raise"),
                (book.get(VS_3BET, a, b, "call"),
                 _union(book.get(VS_3BET, a, b, "4bet"), book.get(VS_3BET, a, b, "4bet_allin"))))
    return (book.get(VS_OPEN, b, a, "3bet"),
            (book.get(VS_4BET, b, a, "call"),
             _union(book.get(VS_4BET, b, a, "5bet"), book.get(VS_4BET, b, a, "5bet_allin"))))


def missing_actions(book: RangeBook) -> list[str]:
    """Theory cells that have only one of their two actions (the other counts as 0)."""
    out = []
    for node, names in ACTION_NAMES.items():
        for i, a in enumerate(POSITIONS[:-1]):
            for b in POSITIONS[i + 1:]:
                base, actions = _inputs(node, a, b, book)
                if (base is None and node != VS_OPEN) or not any(actions):
                    continue
                out += [f"{node} {a}>{b} 缺 {name}，已當 0" for name, rng in zip(names, actions) if rng is None]
    return out


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


def _theory(node: str, a: str, b: str, book: RangeBook) -> dict[str, float] | None:
    """Theory for the cell. A missing action counts as 0 when the other action and the base range exist."""
    base, (first, second) = _inputs(node, a, b, book)
    if not (first or second) or (base is None and node != VS_OPEN):
        return None
    first, second = first or ZERO, second or ZERO
    if node == VS_OPEN:
        return {"c": total_share(first), "r": total_share(second)}
    return _conditional(base, first, second)


def _clamped(theory: dict[str, float] | None, label: str, warnings: list[str]) -> dict[str, float] | None:
    """Scale c and r down proportionally when they add up to more than 1."""
    if theory is None or theory["c"] + theory["r"] <= 1 + SUM_TOLERANCE:
        return theory
    total = theory["c"] + theory["r"]
    warnings.append(f"{label} 理論的跟注 + 加注 = {total:.4f} 超過 1，已按比例縮到 1")
    return {"c": theory["c"] / total, "r": theory["r"] / total}


def _open_cell(pos: str, counts: dict, book: RangeBook) -> dict:
    rng = book.get(OPEN, pos, None, "raise")
    cell: dict = {"th": {"r": total_share(rng)} if rng else None}
    for who in (ME, POOL):
        counter = counts.get((OPEN, pos, who))
        n = sum(counter.values()) if counter else 0
        cell[who] = {"r": counter[RAISE] / n, "n": n} if n else None
    return cell


def _pair_cell(node: str, a: str, b: str, counts: dict, book: RangeBook, warnings: list[str]) -> dict:
    cell: dict = {"th": _clamped(_theory(node, a, b, book), f"{node} {a}>{b}", warnings)}
    for who in (ME, POOL):
        counter = counts.get((node, f"{a}>{b}", who))
        n = sum(counter.values()) if counter else 0
        cell[who] = {"c": counter[CALL] / n, "r": counter[RAISE] / n, "n": n} if n else None
    return cell


def _reach(data: dict, node: str, key: str, who: str) -> float | None:
    """Probability (over all dealt hands) that the responder of the cell gets to decide."""
    opener, _, _ = key.partition(">")
    try:
        if node == VS_3BET:
            return data["open"][opener][who]["r"]
        if node == VS_4BET:
            return data[VS_OPEN][key][who]["r"]
        return data["open"][opener][who]["r"] * data[VS_3BET][key][who]["r"]
    except (KeyError, TypeError):
        return None


def absolute(data: dict) -> dict:
    """Frequencies of vs_3bet / vs_4bet / vs_5bet as a share of all dealt hands (th, me, pool)."""
    out: dict = {}
    for node in (VS_3BET, VS_4BET, VS_5BET):
        out[node] = {}
        for key, cell in data[node].items():
            row = {}
            for who in WHO:
                x, reach = cell[who], _reach(data, node, key, who)
                if x is not None and reach is not None:
                    row[who] = {"reach": reach, "f": reach * (1 - x["c"] - x["r"]), "c": reach * x["c"],
                                "r": reach * x["r"], "n": x.get("n")}
            out[node][key] = row
    return out


def build_matrix(hands: list[Hand], book: RangeBook, hero: str) -> dict:
    counts, hero_hands = tally(hands, hero)
    warnings: list[str] = []
    data: dict = {"open": {p: _open_cell(p, counts, book) for p in POSITIONS[:-1]}}
    for node in NODES[1:]:
        data[node] = {f"{a}>{b}": _pair_cell(node, a, b, counts, book, warnings)
                      for i, a in enumerate(POSITIONS[:-1]) for b in POSITIONS[i + 1:]}
    data["absolute"] = absolute(data)
    dates = sorted(h.date for h in hands)
    data["meta"] = {"hands": len(hands), "hero": hero, "hero_hands": hero_hands, "warnings": warnings,
                    "date_from": dates[0] if dates else "", "date_to": dates[-1] if dates else ""}
    return data
