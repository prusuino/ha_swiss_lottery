"""Unit tests of the swisslos.ch result parser helpers."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from custom_components.swiss_lottery.const import GAME_SWISSLOTTO
from custom_components.swiss_lottery.swisslos import (
    DrawResult,
    _parse_amount,
    _parse_date,
    _parse_int,
    next_draw_datetime,
    parse_tree,
)


def test_parse_date_reads_swiss_format() -> None:
    assert _parse_date("Ziehung vom 07.11.2026, 17:00") == date(2026, 11, 7)
    assert _parse_date("no date here") is None
    assert _parse_date("31.02.2026") is None


def test_parse_int_strips_separators() -> None:
    assert _parse_int("12'345 winners") == 12345
    assert _parse_int("none") is None


def test_parse_amount_handles_swiss_separators() -> None:
    assert _parse_amount("526'735.85") == 526735.85
    assert _parse_amount("1 902.50") == 1902.5
    assert _parse_amount("0.00") == 0.0
    assert _parse_amount("50'000.00 30 years per month") is None


def test_parse_tree_builds_a_navigable_node_tree() -> None:
    root = parse_tree("<div class='a'><ul><li class='n'>4</li><li class='n'>11</li></ul></div>")
    assert root is not None


def test_next_draw_datetime_combines_date_and_closing_time() -> None:
    result = DrawResult(
        game=GAME_SWISSLOTTO, draw_date=date(2026, 11, 7), numbers=(), bonus=(), replay=None, second_chance=(),
        extra_game=None, jackpot_chf=None, next_draw=date(2026, 11, 11), next_draw_closing="17:00", tiers=(),
    )
    tz = ZoneInfo("Europe/Zurich")
    assert next_draw_datetime(result, tz) == datetime(2026, 11, 11, 17, 0, tzinfo=tz)
    no_date = DrawResult(
        game=GAME_SWISSLOTTO, draw_date=date(2026, 11, 7), numbers=(), bonus=(), replay=None, second_chance=(),
        extra_game=None, jackpot_chf=None, next_draw=None, next_draw_closing=None, tiers=(),
    )
    assert next_draw_datetime(no_date, tz) is None
