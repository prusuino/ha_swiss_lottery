"""Unit tests of the ticket parser and the draw evaluation."""
from __future__ import annotations

from datetime import date

import pytest

from custom_components.swiss_lottery.const import GAME_EURODREAMS, GAME_EUROMILLIONS, GAME_SWISSLOTTO
from custom_components.swiss_lottery.swisslos import DrawResult, PrizeTier
from custom_components.swiss_lottery.tickets import Ticket, TicketError, evaluate, parse_ticket, parse_tickets


def test_parse_ticket_accepts_the_documented_formats() -> None:
    expected = Ticket((4, 11, 19, 27, 33, 41), (5,))
    assert parse_ticket("4 11 19 27 33 41 + 5", GAME_SWISSLOTTO) == expected
    assert parse_ticket("4,11,19,27,33,41,5", GAME_SWISSLOTTO) == expected
    assert parse_ticket("41-33-27-19-11-4 / 5", GAME_SWISSLOTTO) == expected
    assert expected.as_text() == "4 11 19 27 33 41 + 5"


def test_parse_ticket_euromillions_has_two_stars() -> None:
    ticket = parse_ticket("1 2 3 4 5 + 6 7", GAME_EUROMILLIONS)
    assert ticket.numbers == (1, 2, 3, 4, 5)
    assert ticket.bonus == (6, 7)


@pytest.mark.parametrize(
    ("line", "game", "code"),
    [
        ("1 2 3 4 5 + 6", GAME_SWISSLOTTO, "ticket_count"),  # one main number short
        ("1 2 3 4 5 5 + 6", GAME_SWISSLOTTO, "ticket_duplicate"),
        ("1 2 3 4 5 43 + 6", GAME_SWISSLOTTO, "ticket_range"),  # 43 > 42
        ("1 2 3 4 5 6 + 7", GAME_SWISSLOTTO, "ticket_range"),  # lucky number 7 > 6
        ("1 2 3 4 5 6 + 6", GAME_EURODREAMS, "ticket_range"),  # dream number 6 > 5
        ("", GAME_SWISSLOTTO, "ticket_count"),
    ],
)
def test_parse_ticket_rejects_bad_lines(line: str, game: str, code: str) -> None:
    with pytest.raises(TicketError) as err:
        parse_ticket(line, game)
    assert err.value.code == code


def test_parse_tickets_skips_blank_lines() -> None:
    tickets = parse_tickets("1 2 3 4 5 6 + 1\n\n7 8 9 10 11 12 + 2\n", GAME_SWISSLOTTO)
    assert len(tickets) == 2


def _draw(tiers: tuple[PrizeTier, ...]) -> DrawResult:
    return DrawResult(
        game=GAME_SWISSLOTTO,
        draw_date=date(2026, 11, 7),
        numbers=(4, 11, 19, 27, 33, 41),
        bonus=(5,),
        replay=3,
        second_chance=(),
        extra_game=None,
        jackpot_chf=2_500_000.0,
        next_draw=date(2026, 11, 11),
        next_draw_closing="17:00",
        tiers=tiers,
    )


TIERS = (
    PrizeTier("6+1", 0, 0.0, "0.00"),
    PrizeTier("6", 1, 1_000_000.0, "1'000'000.00"),
    PrizeTier("5+1", 9, 11_721.40, "11'721.40"),
    PrizeTier("5", 150, 1_000.0, "1'000.00"),
    PrizeTier("3", 20_000, 10.0, "10.00"),
)


def test_evaluate_finds_the_tier_and_the_prize() -> None:
    result = evaluate(Ticket((4, 11, 19, 27, 33, 1), (5,)), _draw(TIERS))
    assert result.matches == 5
    assert result.bonus_matches == 1
    assert result.tier == "5+1"
    assert result.prize == 11_721.40
    assert result.won is True


def test_evaluate_without_tier_is_no_win() -> None:
    result = evaluate(Ticket((1, 2, 3, 4, 5, 6), (6,)), _draw(TIERS))
    assert result.matches == 1
    assert result.tier is None
    assert result.won is False


def test_evaluate_jackpot_rank_without_winners_counts_as_won() -> None:
    result = evaluate(Ticket((4, 11, 19, 27, 33, 41), (5,)), _draw(TIERS))
    assert result.tier == "6+1"
    assert result.won is True
    assert result.prize is None
    assert result.prize_text == "Jackpot"


def test_evaluate_matches_combined_eurodreams_labels() -> None:
    tiers = (PrizeTier("6+1 & 5", 2, None, "20'000.00 30 years per month"),)
    ticket = Ticket((4, 11, 19, 27, 33, 2), (1,))
    result = evaluate(ticket, _draw(tiers))
    assert result.tier == "6+1 & 5"
    assert result.won is True  # an annuity text is a win even without a plain amount
