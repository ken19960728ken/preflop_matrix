"""Preflop-only parser for GGPoker / Natural8 Rush & Cash hand histories."""
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from preflop_matrix.positions import TABLE_SIZE, assign_positions

_AMOUNT = r"\$([\d,]+(?:\.\d+)?)"
RE_HEADER = re.compile(
    rf"^Poker Hand #(\S+): Hold'em No Limit \({_AMOUNT}/{_AMOUNT}\) - (\d{{4}})/(\d{{2}})/(\d{{2}}) \d{{2}}:\d{{2}}:\d{{2}}$"
)
RE_TABLE = re.compile(r"^Table '[^']+' \d+-max Seat #(\d+) is the button$")
RE_SEAT = re.compile(rf"^Seat (\d+): (.+?) \({_AMOUNT} in chips\)$")
RE_POST = re.compile(rf"^(.+?): posts (small|big) blind {_AMOUNT}(?: and is all-in)?$")
RE_HAND_ID = re.compile(r"^Poker Hand #(\S+):")
RE_FOLD_CHECK = re.compile(r"^(.+?): (folds|checks)$")
RE_CALL = re.compile(rf"^(.+?): calls {_AMOUNT}( and is all-in)?$")
RE_RAISE = re.compile(rf"^(.+?): raises {_AMOUNT} to {_AMOUNT}( and is all-in)?$")
RE_IGNORED = re.compile(
    r"^(Dealt to .*|Uncalled bet \(.*|Cash Drop to Pot .*|.+: shows \[.*|.+: Bet & Muck folds|.*All-in Insurance.*)$"
)
HOLE_CARDS = "*** HOLE CARDS ***"
SUMMARY = "*** SUMMARY ***"


class ParseError(ValueError):
    """The text is not a hand this parser understands."""


class TableSizeError(ParseError):
    """A well-formed hand that does not have exactly six players."""


@dataclass(frozen=True)
class Action:
    player: str
    kind: str                     # fold | check | call | raise
    to_amount: Decimal | None     # raise-to size, raises only
    allin: bool


@dataclass(frozen=True)
class Hand:
    hand_id: str
    date: str                     # YYYY-MM-DD
    bb: Decimal
    positions: Mapping[str, str]  # player name -> position
    actions: tuple[Action, ...]   # preflop voluntary actions, in order (blinds excluded)


def _dec(text: str) -> Decimal:
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation:
        raise ParseError(f"bad amount: {text!r}") from None


def split_hands(text: str) -> list[str]:
    """Split a file's text into hand blocks."""
    text = text.replace("\r\n", "\n").lstrip("﻿")
    return [b.strip() for b in re.split(r"(?m)^(?=Poker Hand #)", text) if b.strip()]


def _parse_action(line: str) -> Action:
    if m := RE_FOLD_CHECK.match(line):
        return Action(m[1], "fold" if m[2] == "folds" else "check", None, False)
    if m := RE_CALL.match(line):
        return Action(m[1], "call", None, bool(m[3]))
    if m := RE_RAISE.match(line):
        return Action(m[1], "raise", _dec(m[3]), bool(m[4]))
    raise ParseError(f"unrecognised preflop line: {line!r}")


def parse_hand(block: str) -> Hand:
    """Parse the preflop part of one hand block."""
    lines = [line.rstrip() for line in block.replace("\r\n", "\n").strip().split("\n")]
    header = RE_HEADER.match(lines[0])
    table = RE_TABLE.match(lines[1]) if len(lines) > 1 else None
    if not header or not table:
        raise ParseError(f"unsupported game or bad header: {lines[0]!r}")
    if HOLE_CARDS not in lines or SUMMARY not in lines:
        raise ParseError("missing HOLE CARDS or SUMMARY section")
    seats: list[tuple[int, str]] = []
    actions: list[Action] = []
    posted: dict[str, str] = {}
    for line in lines[2:lines.index(HOLE_CARDS)]:
        if m := RE_SEAT.match(line):
            seats.append((int(m[1]), m[2]))
        elif m := RE_POST.match(line):
            posted[m[2]] = m[1]
        elif not RE_IGNORED.match(line):
            raise ParseError(f"unrecognised line before the deal: {line!r}")
    for line in lines[lines.index(HOLE_CARDS) + 1:]:
        if line.startswith("*** "):
            break
        if line.strip() and not RE_IGNORED.match(line):
            actions.append(_parse_action(line))
    if len({name for _, name in seats}) != len(seats):
        raise ParseError("duplicate player name")
    if len(seats) != TABLE_SIZE:
        raise TableSizeError(f"{len(seats)} players (only {TABLE_SIZE}-handed hands are used)")
    if all(num != int(table[1]) for num, _ in seats):
        raise ParseError(f"button seat {table[1]} is empty")
    names = {name for _, name in seats}
    if unseated := {a.player for a in actions} - names:
        raise ParseError(f"player not seated: {min(unseated)!r}")
    positions = assign_positions(seats, int(table[1]))
    if positions.get(posted.get("small")) != "SB" or positions.get(posted.get("big")) != "BB":
        raise ParseError("positions from the button disagree with the players who posted the blinds")
    return Hand(header[1], f"{header[4]}-{header[5]}-{header[6]}", _dec(header[3]), positions, tuple(actions))


@dataclass
class LoadResult:
    hands: list[Hand] = field(default_factory=list)
    files: int = 0
    duplicates: int = 0
    unparseable: int = 0
    not_six_max: int = 0
    unreadable_files: int = 0
    error_samples: list[str] = field(default_factory=list)

    MAX_SAMPLES = 5

    def note_error(self, where: str, err: Exception) -> None:
        if len(self.error_samples) < self.MAX_SAMPLES:
            self.error_samples.append(f"{where}: {err}")


def load_hands(root: Path) -> LoadResult:
    """Recursively read every .txt under root; skip duplicates by hand id and count what cannot be used."""
    result = LoadResult()
    seen: set[str] = set()
    for path in sorted(root.rglob("*.txt")):
        result.files += 1
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as err:
            result.unreadable_files += 1
            result.note_error(path.name, err)
            continue
        for block in split_hands(text):
            hand_id = RE_HAND_ID.match(block)
            if hand_id and hand_id[1] in seen:
                result.duplicates += 1
                continue
            if hand_id:
                seen.add(hand_id[1])
            try:
                hand = parse_hand(block)
            except TableSizeError:
                result.not_six_max += 1
                continue
            except ParseError as err:
                result.unparseable += 1
                result.note_error(path.name, err)
                continue
            result.hands.append(hand)
    return result
