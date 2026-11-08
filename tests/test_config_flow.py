"""Config flow tests: one entry per game, ticket validation, duplicate
detection and the options flow. swisslos.ch is never contacted."""
from __future__ import annotations

from datetime import date
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.swiss_lottery.const import CONF_GAME, CONF_TICKETS, DOMAIN, GAME_EUROMILLIONS, GAME_SWISSLOTTO
from custom_components.swiss_lottery.swisslos import DrawResult, SwisslosCommunicationError

RESULT = DrawResult(
    game=GAME_SWISSLOTTO, draw_date=date(2026, 11, 7), numbers=(4, 11, 19, 27, 33, 41), bonus=(5,), replay=3,
    second_chance=(), extra_game=None, jackpot_chf=2_500_000.0, next_draw=date(2026, 11, 11),
    next_draw_closing="17:00", tiers=(),
)


@pytest.fixture
def fake_results():
    with patch("custom_components.swiss_lottery.swisslos.async_fetch_results", return_value={GAME_SWISSLOTTO: RESULT}):
        yield


async def test_setup_normalises_tickets(hass: HomeAssistant, enable_custom_integrations, fake_results) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_GAME: GAME_SWISSLOTTO, CONF_TICKETS: "41,33,27,19,11,4,5\n\n1 2 3 4 5 6 + 1"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Swiss Lotto"
    assert result["data"] == {CONF_GAME: GAME_SWISSLOTTO}
    assert result["options"][CONF_TICKETS] == ["4 11 19 27 33 41 + 5", "1 2 3 4 5 6 + 1"]
    assert result["result"].unique_id == GAME_SWISSLOTTO


async def test_bad_ticket_shows_the_offending_line(hass: HomeAssistant, enable_custom_integrations, fake_results) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_GAME: GAME_SWISSLOTTO, CONF_TICKETS: "1 2 3 4 5 99 + 1"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TICKETS: "ticket_range"}
    assert result["description_placeholders"]["line"] == "1 2 3 4 5 99 + 1"


async def test_same_game_twice_is_refused(hass: HomeAssistant, enable_custom_integrations, fake_results) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=GAME_SWISSLOTTO, title="Swiss Lotto", data={CONF_GAME: GAME_SWISSLOTTO}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_GAME: GAME_SWISSLOTTO, CONF_TICKETS: ""})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_unreachable_site_is_a_form_error(hass: HomeAssistant, enable_custom_integrations) -> None:
    with patch(
        "custom_components.swiss_lottery.swisslos.async_fetch_results",
        side_effect=SwisslosCommunicationError("offline"),
    ):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_GAME: GAME_EUROMILLIONS, CONF_TICKETS: ""})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_replaces_the_tickets(hass: HomeAssistant, enable_custom_integrations) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=GAME_SWISSLOTTO, title="Swiss Lotto", data={CONF_GAME: GAME_SWISSLOTTO},
        options={CONF_TICKETS: ["1 2 3 4 5 6 + 1"]},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_TICKETS: "7 8 9 10 11 12 + 2"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_TICKETS: ["7 8 9 10 11 12 + 2"]}
