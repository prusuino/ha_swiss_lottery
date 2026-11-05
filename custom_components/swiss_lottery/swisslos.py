"""Reading the published draw results from swisslos.ch.

Swisslos publishes the results of every draw on its website; there is no
machine-readable feed. The footer of the winning-numbers page carries, for
all three games at once, the latest draw (date and numbers), the extra-game
number, the prize table, the current jackpot and the next draw. One request
therefore covers Swiss Lotto, EuroMillions and EuroDreams.

The page is parsed with the standard library only (html.parser): a small
element tree is built and then queried by CSS class. The class names are the
ones Swisslos uses for its own layout; if they change, the parser raises
SwisslosParseError and the entities go unavailable rather than showing
something wrong.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser

import aiohttp

from .const import (
    GAME_EURODREAMS,
    GAME_EUROMILLIONS,
    GAME_SWISSLOTTO,
    SWISSLOS_REQUEST_TIMEOUT_SECONDS,
    SWISSLOS_RESULTS_URL,
)


class SwisslosError(Exception):
    """Base class for all errors raised by this module."""


class SwisslosCommunicationError(SwisslosError):
    """The page could not be fetched."""


class SwisslosParseError(SwisslosError):
    """The page did not have the expected structure."""


# --------------------------------------------------------------------------- tree


class _Node:
    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag: str, attrs: dict[str, str], parent: _Node | None) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children: list[_Node | str] = []
        self.parent = parent

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    def has_class(self, name: str) -> bool:
        return name in self.classes

    def text(self) -> str:
        parts: list[str] = []
        for child in self.children:
            parts.append(child if isinstance(child, str) else child.text())
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def iter(self):
        for child in self.children:
            if isinstance(child, _Node):
                yield child
                yield from child.iter()

    def find_all(self, *, cls: str | None = None, tag: str | None = None) -> list[_Node]:
        return [
            n
            for n in self.iter()
            if (cls is None or n.has_class(cls)) and (tag is None or n.tag == tag)
        ]

    def find(self, *, cls: str | None = None, tag: str | None = None) -> _Node | None:
        found = self.find_all(cls=cls, tag=tag)
        return found[0] if found else None


_VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", {}, None)
        self._cur = self.root

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, {k: (v or "") for k, v in attrs}, self._cur)
        self._cur.children.append(node)
        if tag not in _VOID:
            self._cur = node

    def handle_startendtag(self, tag, attrs):
        self._cur.children.append(_Node(tag, {k: (v or "") for k, v in attrs}, self._cur))

    def handle_endtag(self, tag):
        # Close the nearest open element with this tag; tolerate stray end tags.
        node = self._cur
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self._cur = node.parent

    def handle_data(self, data):
        if data:
            self._cur.children.append(data)


def parse_tree(html: str) -> _Node:
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


# --------------------------------------------------------------------------- model


@dataclass(frozen=True)
class PrizeTier:
    """One row of a prize table: '5 + 1' → 9 winners → CHF 11'721.40."""

    label: str  # normalised: "5+1", "5", "6+1 & 5" style kept as published
    winners: int | None
    prize: float | None  # CHF; None when the published prize is not a plain amount
    prize_text: str  # the published text (EuroDreams: "50'000.00 30 years per month")


@dataclass(frozen=True)
class ExtraGame:
    """Joker (Swiss Lotto), Super-Star (EuroMillions): a drawn code and its table."""

    name: str
    number: str | None
    jackpot_chf: float | None
    tiers: tuple[PrizeTier, ...] = ()


@dataclass(frozen=True)
class DrawResult:
    game: str
    draw_date: date
    numbers: tuple[int, ...]
    bonus: tuple[int, ...]  # lucky number / stars / dream number
    replay: int | None  # Swiss Lotto only
    second_chance: tuple[int, ...]  # EuroMillions only
    extra_game: ExtraGame | None
    jackpot_chf: float | None  # jackpot of the NEXT draw as published
    next_draw: date | None
    next_draw_closing: str | None  # "17:00"
    tiers: tuple[PrizeTier, ...]
    second_chance_tiers: tuple[PrizeTier, ...] = ()


# --------------------------------------------------------------------------- parsing

# The footer has one block per game, marked with data-hash="swisslotto" etc.
# (the class names carry a hyphenated variant, "swiss-lotto", so the data
# attribute is the stable handle).
_CONTAINER_HASH = {
    GAME_SWISSLOTTO: "swisslotto",
    GAME_EUROMILLIONS: "euromillions",
    GAME_EURODREAMS: "eurodreams",
}
_MAIN_NUMBER_CLASSES = ("actual-numbers__number___normal", "actual-numbers__number___eurodreams")
_BONUS_NUMBER_CLASSES = (
    "actual-numbers__number___lucky",
    "actual-numbers__number___superstar",
    "actual-numbers__number___eurodreams-dream",
)
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")


def _parse_date(text: str) -> date | None:
    m = _DATE_RE.search(text)
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _parse_int(text: str) -> int | None:
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else None


def _parse_amount(text: str) -> float | None:
    """'526'735.85' / '1 902.50' / '0.00' → float; None for anything else."""
    cleaned = text.replace("'", "").replace("’", "").replace(" ", "").replace(" ", "")
    if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
        return None
    return float(cleaned)


def _numbers_in(ul: _Node, classes: tuple[str, ...]) -> tuple[int, ...]:
    out: list[int] = []
    for li in ul.find_all(tag="li"):
        if any(li.has_class(c) for c in classes) and li.has_class("actual-numbers__number"):
            value = _parse_int(li.text())
            if value is not None:
                out.append(value)
    return tuple(out)


def _parse_table(table: _Node) -> tuple[PrizeTier, ...]:
    tiers: list[PrizeTier] = []
    for tr in table.find_all(tag="tr"):
        cells = [c for c in tr.children if isinstance(c, _Node) and c.tag in ("td", "th")]
        if len(cells) < 3 or tr.parent is not None and tr.parent.tag == "thead":
            continue
        label_cell, winners_cell, prize_cell = cells[0], cells[1], cells[2]
        label = label_cell.text()
        # EuroMillions prints the star count as images: "5 + ★★" → "5+2".
        stars = len([n for n in label_cell.iter() if n.tag == "img"])
        if stars:
            label = f"{label.rstrip('+ ').strip()}+{stars}" if label.strip().endswith("+") else f"{label}+{stars}"
        label = re.sub(r"\s*\+\s*", "+", label)
        label = re.sub(r"\s*&\s*", " & ", label)
        label = re.sub(r"\s+", " ", label).strip()
        if not label or not re.match(r"\d", label):
            continue
        prize_text = prize_cell.text()
        tiers.append(
            PrizeTier(
                label=label,
                winners=_parse_int(winners_cell.text()),
                prize=_parse_amount(prize_text),
                prize_text=prize_text,
            )
        )
    return tuple(tiers)


def _parse_game(root: _Node, game: str) -> DrawResult:
    container = next(
        (
            n
            for n in root.find_all(cls="flyout__game-container")
            if n.attrs.get("data-hash") == _CONTAINER_HASH[game]
        ),
        None,
    )
    if container is None:
        raise SwisslosParseError(f"no result block for {game}")

    date_node = container.find(cls="actual-numbers__date-time")
    draw_date = _parse_date(date_node.text()) if date_node else None
    if draw_date is None:
        raise SwisslosParseError(f"no draw date for {game}")

    bodies = container.find_all(cls="actual-numbers___body")
    if not bodies:
        raise SwisslosParseError(f"no numbers for {game}")
    main_body = next((b for b in bodies if not b.has_class("actual-numbers__2nd-chance")), bodies[0])
    numbers = _numbers_in(main_body, _MAIN_NUMBER_CLASSES)
    bonus = _numbers_in(main_body, _BONUS_NUMBER_CLASSES)
    replay_node = main_body.find(cls="actual-numbers__number___replay")
    replay = _parse_int(replay_node.text()) if replay_node else None
    if not numbers:
        raise SwisslosParseError(f"empty numbers for {game}")

    second_chance: tuple[int, ...] = ()
    sc_body = next((b for b in bodies if b.has_class("actual-numbers__2nd-chance")), None)
    if sc_body is not None:
        second_chance = _numbers_in(sc_body, _MAIN_NUMBER_CLASSES)

    # Next draw and jackpots
    next_draw = None
    closing = None
    nd_date = container.find(cls="actual-jackpot__next-draw___date")
    nd_time = container.find(cls="actual-jackpot__next-draw___time")
    if nd_date is not None:
        next_draw = _parse_date(nd_date.text())
    if nd_time is not None:
        m = _TIME_RE.search(nd_time.text())
        closing = m.group(1) if m else None
    jackpot = None
    extra_jackpot = None
    # The first jackpot node is the game's own, a second one (marked extraGame
    # for Swiss Lotto, unmarked for EuroMillions) belongs to the extra game.
    for node in container.find_all(cls="jackpot___value"):
        raw = node.attrs.get("data-jackpot")
        value = float(raw) if raw and re.fullmatch(r"\d+(\.\d+)?", raw) else None
        if node.attrs.get("data-jackpot-type") == "extraGame" or jackpot is not None:
            if value is not None:
                extra_jackpot = value
        elif value is not None:
            jackpot = value

    # Prize tables: the main game, then the extra games (Joker / 2. Chance / Super-Star)
    tiers: tuple[PrizeTier, ...] = ()
    sc_tiers: tuple[PrizeTier, ...] = ()
    extra_name = None
    extra_tiers: tuple[PrizeTier, ...] = ()
    for block in container.find_all(cls="quotes__game") + container.find_all(cls="quotes__extra-game"):
        title_node = block.find(cls="quotes__game-title")
        table = block.find(tag="table")
        if table is None:
            continue
        title = title_node.text() if title_node else ""
        parsed = _parse_table(table)
        if block.has_class("quotes__game"):
            tiers = parsed
        elif re.search(r"chance", title, re.I):
            sc_tiers = parsed
        else:
            extra_name = title or extra_name
            extra_tiers = parsed

    extra_number = None
    extra_node = container.find(cls="actual-numbers__extra-game___number")
    if extra_node is not None:
        extra_number = extra_node.text() or None
    extra_game = None
    if extra_name or extra_number or extra_jackpot is not None:
        extra_game = ExtraGame(
            name=extra_name or ("Joker" if game == GAME_SWISSLOTTO else "Super-Star"),
            number=extra_number,
            jackpot_chf=extra_jackpot,
            tiers=extra_tiers,
        )

    return DrawResult(
        game=game,
        draw_date=draw_date,
        numbers=numbers,
        bonus=bonus,
        replay=replay,
        second_chance=second_chance,
        extra_game=extra_game,
        jackpot_chf=jackpot,
        next_draw=next_draw,
        next_draw_closing=closing,
        tiers=tiers,
        second_chance_tiers=sc_tiers,
    )


def parse_results(html: str, games: tuple[str, ...] | None = None) -> dict[str, DrawResult]:
    """All games found on the page (or the requested ones), keyed by game."""
    root = parse_tree(html)
    out: dict[str, DrawResult] = {}
    for game in games or tuple(_CONTAINER_HASH):
        out[game] = _parse_game(root, game)
    return out


# --------------------------------------------------------------------------- fetch


async def async_fetch_results(
    session: aiohttp.ClientSession, games: tuple[str, ...] | None = None
) -> dict[str, DrawResult]:
    """Download the results page once and parse the requested games.

    Parsing ~90 KB of HTML takes tens of milliseconds, so it runs in the
    default executor rather than on the event loop.
    """
    try:
        async with session.get(
            SWISSLOS_RESULTS_URL,
            timeout=aiohttp.ClientTimeout(total=SWISSLOS_REQUEST_TIMEOUT_SECONDS),
            headers={"Accept": "text/html", "Accept-Language": "en"},
        ) as resp:
            if resp.status >= 400:
                raise SwisslosCommunicationError(f"HTTP {resp.status}")
            html = await resp.text()
    except TimeoutError as err:
        raise SwisslosCommunicationError("timeout") from err
    except aiohttp.ClientError as err:
        raise SwisslosCommunicationError(type(err).__name__) from err
    return await asyncio.get_running_loop().run_in_executor(None, parse_results, html, games)


def next_draw_datetime(result: DrawResult, tzinfo) -> datetime | None:
    """Closing time of the next draw as an aware datetime (None if unknown)."""
    if result.next_draw is None:
        return None
    hour, minute = 0, 0
    if result.next_draw_closing:
        hour, minute = (int(x) for x in result.next_draw_closing.split(":"))
    return datetime(
        result.next_draw.year, result.next_draw.month, result.next_draw.day, hour, minute, tzinfo=tzinfo
    )
