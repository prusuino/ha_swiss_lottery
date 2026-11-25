"""The parser against the winning-numbers pages of swisslos.ch.

`tests/fixtures/<game>.html` hold the parts of the three pages the parser
reads, cut out of the pages as published on 25 November 2026."""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.swiss_lottery.const import (
    GAME_EURODREAMS,
    GAME_EUROMILLIONS,
    GAME_SWISSLOTTO,
    SWISSLOS_RESULTS_URL,
)
from custom_components.swiss_lottery.swisslos import (
    SwisslosCommunicationError,
    SwisslosParseError,
    async_fetch_results,
    next_draw_datetime,
    parse_result,
)

FIXTURES = Path(__file__).parent / "fixtures"
SWISS = ZoneInfo("Europe/Zurich")


def page(game: str) -> str:
    return (FIXTURES / f"{game}.html").read_text(encoding="utf-8")


def url(game: str) -> str:
    return SWISSLOS_RESULTS_URL.format(game=game)


def without_header(html: str) -> str:
    return re.sub(r"<app-header.*?</app-header>", "", html, flags=re.S)


def test_swiss_lotto_page() -> None:
    result = parse_result(page(GAME_SWISSLOTTO), GAME_SWISSLOTTO)
    assert result.draw_date == date(2026, 11, 21)
    assert result.numbers == (14, 21, 22, 29, 31, 32)
    assert result.bonus == (3,)
    assert result.replay == 3
    assert result.second_chance == ()
    assert result.jackpot_chf == 1_500_000.0
    assert next_draw_datetime(result, SWISS) == datetime(2026, 11, 25, 19, 0, tzinfo=SWISS)
    assert [(tier.label, tier.winners, tier.prize) for tier in result.tiers] == [
        ("6+1", 1, 47_139_443.95),
        ("6", 2, 500_000.0),
        ("5+1", 12, 11_115.45),
        ("5", 74, 1_000.0),
        ("4+1", 844, 117.3),
        ("4", 3_577, 71.85),
        ("3+1", 13_140, 18.95),
        ("3", 56_394, 9.4),
    ]
    joker = result.extra_game
    assert joker is not None
    # The number keeps its leading zero.
    assert (joker.name, joker.number, joker.jackpot_chf) == ("Joker", "078319", 870_000.0)
    assert [(tier.label, tier.winners, tier.prize) for tier in joker.tiers] == [
        ("6", 0, 0.0),
        ("5", 1, 10_000.0),
        ("4", 19, 1_000.0),
        ("3", 198, 100.0),
        ("2", 2_034, 10.0),
    ]


def test_euromillions_page() -> None:
    result = parse_result(page(GAME_EUROMILLIONS), GAME_EUROMILLIONS)
    assert result.draw_date == date(2026, 11, 24)
    assert result.numbers == (3, 5, 37, 44, 49)
    assert result.bonus == (5, 6)
    assert result.replay is None
    assert result.jackpot_chf == 54_000_000.0
    assert next_draw_datetime(result, SWISS) == datetime(2026, 11, 27, 19, 30, tzinfo=SWISS)
    # The stars of a rank are printed as images.
    assert [tier.label for tier in result.tiers] == [
        "5+2", "5+1", "5", "4+2", "4+1", "3+2", "4", "2+2", "3+1", "3", "1+2", "2+1", "2",
    ]
    assert (result.tiers[1].winners, result.tiers[1].prize) == (1, 446_627.6)
    assert result.second_chance == (1, 13, 14, 18, 48)
    assert [(tier.label, tier.winners, tier.prize) for tier in result.second_chance_tiers] == [
        ("5", 0, 0.0),
        ("4", 74, 950.0),
        ("3", 4_250, 44.2),
    ]
    star = result.extra_game
    assert star is not None
    assert (star.name, star.number, star.jackpot_chf) == ("Super-Star", "E929L", 250_000.0)


def test_eurodreams_page() -> None:
    result = parse_result(page(GAME_EURODREAMS), GAME_EURODREAMS)
    assert result.draw_date == date(2026, 11, 23)
    assert result.numbers == (2, 7, 8, 9, 16, 24)
    assert result.bonus == (1,)
    assert result.extra_game is None
    assert result.jackpot_chf is None
    # This page shows the next draw only as a countdown; the header knows it.
    assert next_draw_datetime(result, SWISS) == datetime(2026, 11, 26, 19, 30, tzinfo=SWISS)
    top = result.tiers[0]
    assert (top.label, top.winners, top.prize, top.prize_text) == ("6+1", 0, None, "50'000.00 30 years per month")
    assert [tier.label for tier in result.tiers[2:]] == ["5+1 & 5", "4+1 & 4", "3+1 & 3", "2+1 & 2"]


def test_page_without_header_data_reads_the_box_beside_the_logo() -> None:
    result = parse_result(without_header(page(GAME_SWISSLOTTO)), GAME_SWISSLOTTO)
    assert result.draw_date == date(2026, 11, 21)
    assert (result.next_draw, result.next_draw_closing) == (date(2026, 11, 25), "19:00")
    assert result.extra_game is not None and result.extra_game.number == "078319"

    dreams = parse_result(without_header(page(GAME_EURODREAMS)), GAME_EURODREAMS)
    assert (dreams.next_draw, dreams.next_draw_closing) == (None, None)
    assert next_draw_datetime(dreams, SWISS) is None


def test_header_fills_what_the_page_lacks() -> None:
    html = page(GAME_SWISSLOTTO)
    # No date field: the header's draw time counts, in Swiss time.
    html = re.sub(r'<input class="js-datepicker-input[^>]*>', "", html)
    # No Joker number in the results: the header's code counts.
    html = re.sub(r'<div class="actual-numbers__extra-game___number">.*?</div>\s*</div>', "", html, count=1, flags=re.S)
    # No jackpot beside the logo: the line below the prize table counts.
    html = re.sub(r'<div class="jackpot___value[^>]*>\s*</div>', "", html)
    result = parse_result(html, GAME_SWISSLOTTO)
    assert result.draw_date == date(2026, 11, 21)
    assert result.extra_game is not None and result.extra_game.number == "78319"
    assert result.jackpot_chf == 1_500_000.0


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda html: html.replace("filter-results", "something-else"), "no result block for swisslotto"),
        (lambda html: html.replace("actual-numbers___body", "something-else"), "no numbers for swisslotto"),
        (lambda html: html.replace("actual-numbers__number___normal", "something-else"), "empty numbers for swisslotto"),
        (
            lambda html: without_header(re.sub(r'<input class="js-datepicker-input[^>]*>', "", html)),
            "no draw date for swisslotto",
        ),
    ],
)
def test_changed_page_is_refused(change, message) -> None:
    with pytest.raises(SwisslosParseError, match=message):
        parse_result(change(page(GAME_SWISSLOTTO)), GAME_SWISSLOTTO)


def test_page_of_another_game_is_refused() -> None:
    with pytest.raises(SwisslosParseError, match="page shows swisslotto instead of euromillions"):
        parse_result(page(GAME_SWISSLOTTO), GAME_EUROMILLIONS)


@pytest.mark.parametrize("broken", ["{not json", "[1, 2]", '{"swissLotto": 5}', '{"swissLotto": {"deadline": "soon"}}'])
def test_unreadable_header_data_is_ignored(broken) -> None:
    html = re.sub(r'winning-numbers="[^"]*"', "winning-numbers='" + broken + "'", page(GAME_SWISSLOTTO))
    result = parse_result(html, GAME_SWISSLOTTO)
    assert result.numbers == (14, 21, 22, 29, 31, 32)
    assert (result.next_draw, result.next_draw_closing) == (date(2026, 11, 25), "19:00")


async def test_fetch_reads_one_page_per_requested_game(hass: HomeAssistant, aioclient_mock) -> None:
    for game in (GAME_SWISSLOTTO, GAME_EUROMILLIONS, GAME_EURODREAMS):
        aioclient_mock.get(url(game), text=page(game))
    session = async_get_clientsession(hass)

    one = await async_fetch_results(session, (GAME_EUROMILLIONS,))
    assert list(one) == [GAME_EUROMILLIONS]
    assert [str(call[1]) for call in aioclient_mock.mock_calls] == [url(GAME_EUROMILLIONS)]

    aioclient_mock.mock_calls.clear()
    everything = await async_fetch_results(session)
    assert list(everything) == [GAME_SWISSLOTTO, GAME_EUROMILLIONS, GAME_EURODREAMS]
    assert everything[GAME_EURODREAMS].numbers == (2, 7, 8, 9, 16, 24)
    assert len(aioclient_mock.mock_calls) == 3


async def test_fetch_reports_a_page_that_cannot_be_loaded(hass: HomeAssistant, aioclient_mock) -> None:
    session = async_get_clientsession(hass)
    aioclient_mock.get(url(GAME_SWISSLOTTO), status=503)
    with pytest.raises(SwisslosCommunicationError, match="HTTP 503"):
        await async_fetch_results(session, (GAME_SWISSLOTTO,))

    aioclient_mock.clear_requests()
    aioclient_mock.get(url(GAME_SWISSLOTTO), exc=TimeoutError())
    with pytest.raises(SwisslosCommunicationError, match="timeout"):
        await async_fetch_results(session, (GAME_SWISSLOTTO,))
