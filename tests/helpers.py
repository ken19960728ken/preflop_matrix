"""Synthetic GG hands and range files; nothing here comes from real data."""
BB = 0.1
# Button is seat 1 (as in real files); seats 2.. follow clockwise.
SEAT_POSITIONS = ("BTN", "SB", "BB", "UTG", "HJ", "CO")
SUITS = "shdc"


def make_hand(actions, hand_id="RC1", hero="BB", day="2026/10/06", seats=SEAT_POSITIONS, button=1, extra_lines=()):
    """actions: tuples from raises() / calls() / folds(), in order.

    The player sitting at `hero` is called Hero, everybody else p_<position>.
    """
    def name(pos):
        return "Hero" if pos == hero else f"p_{pos}"

    lines = [f"Poker Hand #{hand_id}: Hold'em No Limit ($0.05/$0.1) - {day} 06:55:22",
             f"Table 'RushAndCash1' 6-max Seat #{button} is the button"]
    lines += [f"Seat {i}: {name(pos)} ($10 in chips)" for i, pos in enumerate(seats, start=1)]
    lines += [f"{name('SB')}: posts small blind $0.05", f"{name('BB')}: posts big blind $0.1", "*** HOLE CARDS ***"]
    lines += [f"Dealt to {name(pos)} " for pos in seats]
    for act in actions:
        pos, verb = act[0], act[1]
        if verb == "raises":
            to = act[2] * BB
            lines.append(f"{name(pos)}: raises ${to:.2f} to ${to:.2f}" + (" and is all-in" if act[3] else ""))
        elif verb == "calls":
            lines.append(f"{name(pos)}: calls $0.20")
        else:
            lines.append(f"{name(pos)}: {verb}")
    lines += list(extra_lines)
    lines += ["*** SUMMARY ***", "Total pot $0.5 | Rake $0.02 | Jackpot $0 | Bingo $0 | Fortune $0 | Tax $0"]
    return "\n".join(lines) + "\n\n"


def raises(pos, to, allin=False):
    """A raise to `to` big blinds."""
    return (pos, "raises", to, allin)


def calls(pos):
    return (pos, "calls")


def folds(pos):
    return (pos, "folds")


def _combos(hand: str) -> list[str]:
    r1, r2 = hand[0], hand[1]
    if len(hand) == 2:
        return [f"{r1}{a}{r2}{b}" for i, a in enumerate(SUITS) for b in SUITS[i + 1:]]
    if hand[2] == "s":
        return [f"{r1}{s}{r2}{s}" for s in SUITS]
    return [f"{r1}{a}{r2}{b}" for a in SUITS for b in SUITS if a != b]


def range_text(weights: dict[str, float]) -> str:
    """{'AA': 1, 'AKs': 0.5} -> a range file body ('AsAh: 1,...')."""
    return ",".join(f"{combo}: {w}" for hand, w in weights.items() for combo in _combos(hand))
