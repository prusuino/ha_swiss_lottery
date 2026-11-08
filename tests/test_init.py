"""Setup and unload of a game entry against faked draw results."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swiss_lottery.const import CONF_GAME, CONF_TICKETS, DOMAIN, GAME_SWISSLOTTO
from custom_components.swiss_lottery.swisslos import DrawResult, PrizeTier

RESULT = DrawResult(
    game=GAME_SWISSLOTTO, draw_date=date(2026, 11, 7), numbers=(4, 11, 19, 27, 33, 41), bonus=(5,), replay=3,
    second_chance=(), extra_game=None, jackpot_chf=2_500_000.0, next_draw=date(2026, 11, 11),
    next_draw_closing="17:00",
    tiers=(PrizeTier("6+1", 0, 0.0, "0.00"), PrizeTier("3", 20_000, 10.0, "10.00")),
)


async def test_entry_sets_up_entities_and_unloads(hass: HomeAssistant, enable_custom_integrations) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=GAME_SWISSLOTTO, title="Swiss Lotto", data={CONF_GAME: GAME_SWISSLOTTO},
        options={CONF_TICKETS: ["4 11 19 27 33 1 + 5"]},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.swiss_lottery.swisslos.async_fetch_results", return_value={GAME_SWISSLOTTO: RESULT}):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data is not None
    assert entry.runtime_data.data[GAME_SWISSLOTTO] is RESULT

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, entry.entry_id)
    assert entities, "no entities registered"
    # the draw is shown, the ticket (5 numbers + lucky number, no such tier) has not won
    numbers = hass.states.get("sensor.swiss_lottery_swisslotto_numbers")
    assert numbers is not None and numbers.state.startswith("4, 11, 19, 27, 33, 41")
    assert hass.states.get("sensor.swiss_lottery_swisslotto_replay").state == "3"
    assert hass.states.get("binary_sensor.swiss_lottery_swisslotto_win").state == "off"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
