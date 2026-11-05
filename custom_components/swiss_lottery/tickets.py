"""Tickets: parsing the user's picks and checking them against a draw."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .const import GAME_RULES
from .swisslos import DrawResult, PrizeTier


class TicketError(ValueError):
    """A ticket line that cannot be used; `code` is a translation key."""

    def __init__(self, code: str, line: str) -> None:
        super().__init__(f"{code}: {line}")
        self.code = code
        self.line = line


@dataclass(frozen=True)
class Ticket:
    numbers: tuple[int, ...]
    bonus: tuple[int, ...]

    def as_text(self) -> str:
        main = " ".join(str(n) for n in self.numbers)
        if not self.bonus:
            return main
        return f"{main} + {' '.join(str(n) for n in self.bonus)}"


@dataclass(frozen=True)
class TicketResult:
    ticket: Ticket
    matched: tuple[int, ...]
    matched_bonus: tuple[int, ...]
    tier: str | None  # the prize-table label this ticket falls into, if any
    prize: float | None  # CHF when published as a plain amount
    prize_text: str | None
    won: bool

    @property
    def matches(self) -> int:
        return len(self.matched)

    @property
    def bonus_matches(self) -> int:
        return len(self.matched_bonus)


_SPLIT_RE = re.compile(r"\s*[+/|]\s*")
_NUM_RE = re.compile(r"\d+")


def parse_ticket(text: str, game: str) -> Ticket:
    """One ticket from a line like '4 11 19 27 33 41 + 5', '4,11,19,27,33,41,5' or '4-11-19-27-33-41 / 5'.

    With a separator (+ / |) the part after it holds the bonus numbers; without
    one, the first numbers are the main picks and the rest the bonus.
    """
    n_main, max_main, n_bonus, max_bonus = GAME_RULES[game]
    line = text.strip()
    if not line:
        raise TicketError("ticket_count", line)
    parts = _SPLIT_RE.split(line, maxsplit=1)
    main_nums = [int(x) for x in _NUM_RE.findall(parts[0])]
    if len(parts) == 2:
        bonus_nums = [int(x) for x in _NUM_RE.findall(parts[1])]
    else:
        bonus_nums = main_nums[n_main:]
        main_nums = main_nums[:n_main]
    if len(main_nums) != n_main or len(bonus_nums) != n_bonus:
        raise TicketError("ticket_count", line)
    if len(set(main_nums)) != n_main or len(set(bonus_nums)) != n_bonus:
        raise TicketError("ticket_duplicate", line)
    if any(not 1 <= n <= max_main for n in main_nums) or any(not 1 <= n <= max_bonus for n in bonus_nums):
        raise TicketError("ticket_range", line)
    return Ticket(tuple(sorted(main_nums)), tuple(sorted(bonus_nums)))


def parse_tickets(lines: list[str] | str, game: str) -> list[Ticket]:
    if isinstance(lines, str):
        lines = lines.splitlines()
    return [parse_ticket(line, game) for line in lines if line.strip()]


def _tier_for(tiers: tuple[PrizeTier, ...], matches: int, bonus_matches: int) -> PrizeTier | None:
    """The table row for `matches` main and `bonus_matches` bonus hits.

    Labels are '5+1', '5' or, for EuroDreams, combined like '5+1 & 5'.
    """
    wanted = {f"{matches}+{bonus_matches}", str(matches) if bonus_matches == 0 else ""}
    wanted.discard("")
    for tier in tiers:
        tokens = {tok.strip() for tok in tier.label.split("&")}
        if tokens & wanted:
            return tier
    return None


def evaluate(ticket: Ticket, result: DrawResult) -> TicketResult:
    matched = tuple(n for n in ticket.numbers if n in result.numbers)
    matched_bonus = tuple(n for n in ticket.bonus if n in result.bonus)
    tier = _tier_for(result.tiers, len(matched), len(matched_bonus))
    if tier is None:
        return TicketResult(ticket, matched, matched_bonus, None, None, None, False)
    # Swisslos prints 0.00 for a rank nobody hit: the quota of a top rank is
    # only computed when there is a winner. A ticket that lands in such a
    # rank has won it (the jackpot, typically); the amount is not published.
    if tier.prize == 0 and (tier.winners or 0) == 0:
        return TicketResult(ticket, matched, matched_bonus, tier.label, None, "Jackpot", True)
    # An unparsable text (EuroDreams annuity) is a win as well.
    won = tier.prize is None or tier.prize > 0
    return TicketResult(ticket, matched, matched_bonus, tier.label, tier.prize, tier.prize_text, won)
