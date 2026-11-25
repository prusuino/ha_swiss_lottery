"""Reading the published draw results from swisslos.ch.

Swisslos publishes the results of every draw on its website; there is no
machine-readable feed. Each game has its own winning-numbers page. Its main
part carries the latest draw of that game: date, numbers, the extra-game
number, the prize tables and the jackpots. The page header carries, for all
three games, the closing time of the next draw. One request per game
therefore covers what the integration shows.

The page is parsed with the standard library only (html.parser): a small
element tree is built and then queried by CSS class. The class names are the
ones Swisslos uses for its own layout; if they change, the parser raises
SwisslosParseError and the entities go unavailable rather than showing
something wrong.
"""
from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

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

# Path segment of a game's own pages, also the game the results form names.
_GAME_PAGE = {
    GAME_SWISSLOTTO: "swisslotto",
    GAME_EUROMILLIONS: "euromillions",
    GAME_EURODREAMS: "eurodreams",
}
# Key of a game in the data the page header carries for all three games.
_HEADER_KEY = {
    GAME_SWISSLOTTO: "swissLotto",
    GAME_EUROMILLIONS: "euroMillions",
    GAME_EURODREAMS: "euroDreams",
}
_HEADER_EXTRA_KEY = {GAME_SWISSLOTTO: "joker", GAME_EUROMILLIONS: "superstar"}
_EXTRA_NAME = {GAME_SWISSLOTTO: "Joker", GAME_EUROMILLIONS: "Super-Star"}
_MAIN_NUMBER_CLASSES = ("actual-numbers__number___normal", "actual-numbers__number___eurodreams")
_BONUS_NUMBER_CLASSES = (
    "actual-numbers__number___lucky",
    "actual-numbers__number___superstar",
    "actual-numbers__number___eurodreams-dream",
)
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_TIME_RE = re.compile(r"\b(\d{1,2}:\d{2})\b")
# The header writes its times in UTC; draws and closing times are Swiss time.
_SWISS_TZ = ZoneInfo("Europe/Zurich")


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


def _header_data(root: _Node) -> dict:
    """What the page header knows about the latest draw of every game.

    `<app-header winning-numbers='{"swissLotto": {...}, ...}'>`: closing time
    of the next draw (`deadline`), time of the last draw, numbers and jackpot.
    An empty dict when the header carries nothing readable.
    """
    for node in root.iter():
        raw = node.attrs.get("winning-numbers")
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except ValueError:
            return {}
        return data if isinstance(data, dict) else {}
    return {}


def _header_time(value) -> datetime | None:
    """'2026-11-25T18:00:00Z' → the same moment in Swiss time."""
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        return None
    return moment.astimezone(_SWISS_TZ)


def _jackpot_in(table: _Node) -> float | None:
    """'Jackpot next draw: CHF 1'500'000' → 1500000.0."""
    cell = table.find(cls="quotes__game-jackpot-value")
    if cell is None:
        return None
    return _parse_amount(re.sub(r"^\s*CHF\s*", "", cell.text()))


class _Block:
    """One game of the results: its numbers and the tables that follow it."""

    def __init__(self, node: _Node) -> None:
        self.node = node
        self.tiers: tuple[PrizeTier, ...] = ()
        self.jackpot: float | None = None

    @property
    def is_extra(self) -> bool:
        return self.node.has_class("quotes__extra-game")

    @property
    def is_second_chance(self) -> bool:
        return (
            self.node.find(cls="second-chance-logo") is not None
            or self.node.find(cls="actual-numbers__2nd-chance") is not None
        )


def _result_blocks(scope: _Node) -> list[_Block]:
    """The games of the results in page order, each with its prize table and
    jackpot. The tables stand next to or inside the block they belong to."""
    blocks: list[_Block] = []
    for node in scope.iter():
        if node.tag == "div" and (node.has_class("quotes__game") or node.has_class("quotes__extra-game")):
            blocks.append(_Block(node))
        elif node.tag == "table" and blocks:
            block = blocks[-1]
            if node.has_class("quotes__game-jackpot"):
                if block.jackpot is None:
                    block.jackpot = _jackpot_in(node)
            elif not block.tiers:
                block.tiers = _parse_table(node)
    return blocks


def _parse_game(root: _Node, game: str) -> DrawResult:
    scope = root.find(cls="filter-results")
    if scope is None:
        raise SwisslosParseError(f"no result block for {game}")
    form = root.find(cls="filter__form")
    shown = form.attrs.get("data-statistics-game") if form is not None else None
    if shown and shown != _GAME_PAGE[game]:
        raise SwisslosParseError(f"page shows {shown} instead of {game}")
    header = _header_data(root).get(_HEADER_KEY[game])
    if not isinstance(header, dict):
        header = {}

    blocks = _result_blocks(scope)
    main = next((b for b in blocks if not b.is_extra and not b.is_second_chance), None)
    main_body = main.node.find(cls="actual-numbers___body") if main is not None else None
    if main is None or main_body is None:
        raise SwisslosParseError(f"no numbers for {game}")
    numbers = _numbers_in(main_body, _MAIN_NUMBER_CLASSES)
    bonus = _numbers_in(main_body, _BONUS_NUMBER_CLASSES)
    replay_node = main_body.find(cls="actual-numbers__number___replay")
    replay = _parse_int(replay_node.text()) if replay_node else None
    if not numbers:
        raise SwisslosParseError(f"empty numbers for {game}")

    # The date field of the results form holds the draw that is shown.
    draw_date = None
    date_input = root.find(cls="js-datepicker-input")
    if date_input is not None:
        draw_date = _parse_date(date_input.attrs.get("value", ""))
    if draw_date is None:
        last_draw = _header_time(header.get("lastDrawingDate"))
        draw_date = last_draw.date() if last_draw else None
    if draw_date is None:
        raise SwisslosParseError(f"no draw date for {game}")

    second_chance: tuple[int, ...] = ()
    sc_tiers: tuple[PrizeTier, ...] = ()
    second = next((b for b in blocks if not b.is_extra and b.is_second_chance), None)
    if second is not None:
        second_chance = _numbers_in(second.node, _MAIN_NUMBER_CLASSES)
        sc_tiers = second.tiers

    # Next draw: the header knows it for every game, the box beside the logo
    # only for Swiss Lotto and EuroMillions.
    next_draw = None
    closing = None
    deadline = _header_time(header.get("deadline"))
    if deadline is not None:
        next_draw = deadline.date()
        closing = deadline.strftime("%H:%M")
    else:
        pick = root.find(cls="cockpit__jackpot___next-pick-time")
        if pick is not None:
            next_draw = _parse_date(pick.text())
            m = _TIME_RE.search(pick.text())
            closing = m.group(1) if m and next_draw else None

    # Jackpot of the next draw: beside the logo as a plain number, below the
    # prize table as text.
    jackpot = None
    for node in root.find_all(cls="jackpot___value"):
        raw = node.attrs.get("data-jackpot")
        if raw and re.fullmatch(r"\d+(\.\d+)?", raw):
            jackpot = float(raw)
            break
    if jackpot is None:
        jackpot = main.jackpot

    extra_game = None
    extra = next((b for b in blocks if b.is_extra), None)
    extra_number = None
    if extra is not None:
        code_node = extra.node.find(cls="actual-numbers__extra-game___number")
        if code_node is not None:
            extra_number = code_node.text() or None
        else:
            # Super-Star: one character per ball.
            extra_number = "".join(li.text() for li in extra.node.find_all(cls="actual-numbers__number")) or None
    if extra_number is None and game in _HEADER_EXTRA_KEY:
        code = header.get(_HEADER_EXTRA_KEY[game])
        extra_number = code if isinstance(code, str) and code else None
    if extra is not None or extra_number:
        extra_game = ExtraGame(
            name=_EXTRA_NAME.get(game, "Super-Star"),
            number=extra_number,
            jackpot_chf=extra.jackpot if extra is not None else None,
            tiers=extra.tiers if extra is not None else (),
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
        tiers=main.tiers,
        second_chance_tiers=sc_tiers,
    )


def parse_result(html: str, game: str) -> DrawResult:
    """The latest draw of one game from that game's winning-numbers page."""
    return _parse_game(parse_tree(html), game)


# --------------------------------------------------------------------------- fetch


async def _async_fetch_page(session: aiohttp.ClientSession, game: str) -> str:
    try:
        async with session.get(
            SWISSLOS_RESULTS_URL.format(game=_GAME_PAGE[game]),
            timeout=aiohttp.ClientTimeout(total=SWISSLOS_REQUEST_TIMEOUT_SECONDS),
            headers={"Accept": "text/html", "Accept-Language": "en"},
        ) as resp:
            if resp.status >= 400:
                raise SwisslosCommunicationError(f"HTTP {resp.status}")
            return await resp.text()
    except TimeoutError as err:
        raise SwisslosCommunicationError("timeout") from err
    except aiohttp.ClientError as err:
        raise SwisslosCommunicationError(type(err).__name__) from err


async def async_fetch_results(
    session: aiohttp.ClientSession, games: tuple[str, ...] | None = None
) -> dict[str, DrawResult]:
    """Download the winning-numbers page of every requested game (all three
    when none is named), one after the other, and parse it.

    Parsing ~50 KB of HTML takes tens of milliseconds, so it runs in the
    default executor rather than on the event loop.
    """
    loop = asyncio.get_running_loop()
    out: dict[str, DrawResult] = {}
    for game in games or tuple(_GAME_PAGE):
        html = await _async_fetch_page(session, game)
        out[game] = await loop.run_in_executor(None, parse_result, html, game)
    return out


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
