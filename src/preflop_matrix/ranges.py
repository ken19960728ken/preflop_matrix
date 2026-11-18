"""Theory range files: parsing and the file name → node mapping.

A range maps each of the 169 hand classes (AA, AKs, AKo, ...) to the fraction of its combos played.
Only two-player nodes are mapped; any file naming a third player is ignored.
"""
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

from preflop_matrix.classify import OPEN, VS_3BET, VS_4BET, VS_OPEN
from preflop_matrix.positions import POSITION_INDEX

RANKS = "AKQJT98765432"
SUITS = "shdc"
HANDS = tuple(RANKS[i] * 2 if i == j else RANKS[min(i, j)] + RANKS[max(i, j)] + ("s" if i < j else "o")
              for i in range(13) for j in range(13))
TOTAL_COMBOS = 1326
Range = dict[str, float]


def combos(hand: str) -> int:
    return 6 if len(hand) == 2 else 4 if hand[2] == "s" else 12


def hand_class(card_a: str, card_b: str) -> str:
    """'As', 'Kh' -> 'AKo'."""
    for card in (card_a, card_b):
        if len(card) != 2 or card[0] not in RANKS or card[1] not in SUITS:
            raise ValueError(f"bad card: {card!r}")
    if card_a == card_b:
        raise ValueError(f"the same card twice: {card_a}{card_b}")
    hi, lo = sorted((card_a, card_b), key=lambda c: RANKS.index(c[0]))
    if hi[0] == lo[0]:
        return hi[0] * 2
    return hi[0] + lo[0] + ("s" if hi[1] == lo[1] else "o")


def parse_range_text(text: str) -> Range:
    """'AsAh: 1,KsKh: 0.5,...' -> {hand class: fraction of its combos}, capped at 1."""
    weight: dict[str, float] = defaultdict(float)
    seen: set[frozenset[str]] = set()
    for token in text.replace("\n", ",").split(","):
        if not token.strip():
            continue
        cards, _, value = token.partition(":")
        cards = cards.strip()
        if len(cards) != 4:
            raise ValueError(f"bad combo: {token.strip()!r}")
        cls = hand_class(cards[:2], cards[2:])
        combo = frozenset((cards[:2], cards[2:]))
        if combo in seen:
            raise ValueError(f"duplicate combo: {cards}")
        seen.add(combo)
        w = float(value) if value.strip() else 1.0
        if not math.isfinite(w) or w < 0:
            raise ValueError(f"bad weight: {token.strip()!r}")
        weight[cls] += w
    return {h: min(1.0, weight[h] / combos(h)) for h in HANDS}


def total_share(rng: Range) -> float:
    """Fraction of all 1326 combos in the range."""
    return sum(rng[h] * combos(h) for h in HANDS) / TOTAL_COMBOS


class RangeKey(NamedTuple):
    node: str           # open | vs_open | vs_3bet | vs_4bet
    pos: str            # the acting position
    vs: str | None      # the opponent (None for open)
    action: str         # raise (open) | call | 3bet | 4bet | 4bet_allin | 5bet | 5bet_allin


_POS = "UTG|HJ|CO|BTN|SB|BB"
_SIZE = r"\d+(?:\.\d+)?bb"
RE_OPEN = re.compile(rf"^({_POS}) open {_SIZE}$", re.IGNORECASE)
RE_VS_OPEN = re.compile(rf"^({_POS}) vs ({_POS}) open(?: {_SIZE})? (call|3bet|3b)(?: {_SIZE})?$", re.IGNORECASE)
RE_VS_3BET = re.compile(
    rf"^({_POS}) vs ({_POS}) 3bet(?: {_SIZE})? (call|4bet(?: 4bet)?(?: {_SIZE})?(?: all ?in)?)(?: {_SIZE})?$", re.IGNORECASE)
RE_VS_4BET = re.compile(
    rf"^({_POS}) vs ({_POS}) 4bet(?: {_SIZE})? (call|5bet(?: 5bet)?(?: {_SIZE})?(?: all ?in)?)$", re.IGNORECASE)


def parse_filename(stem: str) -> RangeKey | None:
    """Map a range file name (without .txt) to its node, or None when it is not a two-player node."""
    stem = " ".join(stem.split())
    if m := RE_OPEN.match(stem):
        return RangeKey(OPEN, m[1].upper(), None, "raise")
    if m := RE_VS_OPEN.match(stem):
        defender, opener, action = m[1].upper(), m[2].upper(), m[3].lower()
        if _earlier(opener, defender):
            return RangeKey(VS_OPEN, defender, opener, "3bet" if action == "3b" else action)
        return None
    if m := RE_VS_3BET.match(stem):
        opener, three_bettor, action = m[1].upper(), m[2].upper(), m[3].lower()
        if _earlier(opener, three_bettor):
            return RangeKey(VS_3BET, opener, three_bettor, _raise_action(action, "4bet"))
        return None
    if m := RE_VS_4BET.match(stem):
        three_bettor, opener, action = m[1].upper(), m[2].upper(), m[3].lower()
        if _earlier(opener, three_bettor):
            return RangeKey(VS_4BET, three_bettor, opener, _raise_action(action, "5bet"))
    return None


def _raise_action(action: str, name: str) -> str:
    """'call' stays; '4bet ...' becomes '4bet' or, when the name says all in, '4bet_allin'."""
    if action == "call":
        return action
    return f"{name}_allin" if "all" in action else name


def _earlier(first: str, second: str) -> bool:
    return POSITION_INDEX[first] < POSITION_INDEX[second]


@dataclass
class RangeBook:
    ranges: dict[RangeKey, Range] = field(default_factory=dict)
    files: int = 0
    ignored: list[str] = field(default_factory=list)      # not a two-player node
    duplicates: list[str] = field(default_factory=list)   # a second file for an already mapped node
    unreadable: list[str] = field(default_factory=list)   # mapped but could not be read or parsed

    def get(self, node: str, pos: str, vs: str | None, action: str) -> Range | None:
        return self.ranges.get(RangeKey(node, pos, vs, action))


def load_ranges(root: Path) -> RangeBook:
    """Read every .txt under root and keep the files that map to a two-player node."""
    book = RangeBook()
    for path in sorted(root.rglob("*.txt")):
        book.files += 1
        key = parse_filename(path.stem)
        if key is None:
            book.ignored.append(path.name)
        elif key in book.ranges:
            book.duplicates.append(path.name)
        else:
            try:
                book.ranges[key] = parse_range_text(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError) as err:
                book.unreadable.append(f"{path.name}: {err}")
    return book
