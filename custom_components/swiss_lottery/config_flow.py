"""Config flow: one entry per game, with the user's tickets as options."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from . import swisslos
from .const import CONF_GAME, CONF_TICKETS, DOMAIN, GAME_NAMES, GAMES, MAX_TICKETS
from .tickets import TicketError, parse_tickets

_LOGGER = logging.getLogger(__name__)


def _tickets_schema(default: str = "") -> vol.Schema:
    return vol.Schema(
        {
            vol.Optional(CONF_TICKETS, default=default): TextSelector(
                TextSelectorConfig(multiline=True)
            ),
        }
    )


def _validate_tickets(text: str, game: str) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Normalised ticket lines, or an error key with the offending line."""
    try:
        tickets = parse_tickets(text or "", game)
    except TicketError as err:
        return [], {CONF_TICKETS: err.code}, {"line": err.line}
    if len(tickets) > MAX_TICKETS:
        return [], {CONF_TICKETS: "ticket_too_many"}, {"line": str(MAX_TICKETS)}
    return [t.as_text() for t in tickets], {}, {}


class SwissLotteryConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SwissLotteryOptionsFlow:
        return SwissLotteryOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            game = user_input[CONF_GAME]
            await self.async_set_unique_id(game)
            self._abort_if_unique_id_configured()
            tickets, errors, placeholders = _validate_tickets(user_input.get(CONF_TICKETS, ""), game)
            if not errors:
                try:
                    await swisslos.async_fetch_results(async_get_clientsession(self.hass), (game,))
                except swisslos.SwisslosCommunicationError:
                    errors["base"] = "cannot_connect"
                except swisslos.SwisslosParseError as err:
                    _LOGGER.warning("swisslos.ch page not understood: %s", err)
                    errors["base"] = "invalid_page"
            if not errors:
                return self.async_create_entry(
                    title=GAME_NAMES[game],
                    data={CONF_GAME: game},
                    options={CONF_TICKETS: tickets},
                )

        configured = {entry.unique_id for entry in self._async_current_entries()}
        remaining = [g for g in GAMES if g not in configured] or list(GAMES)
        schema = vol.Schema(
            {
                vol.Required(CONF_GAME, default=remaining[0]): SelectSelector(
                    SelectSelectorConfig(
                        options=list(GAMES), translation_key="game", mode=SelectSelectorMode.LIST
                    )
                ),
                vol.Optional(CONF_TICKETS, default=(user_input or {}).get(CONF_TICKETS, "")): TextSelector(
                    TextSelectorConfig(multiline=True)
                ),
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors, description_placeholders=placeholders
        )


class SwissLotteryOptionsFlow(OptionsFlow):
    """Change the tickets of an entry."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        game = self.config_entry.data[CONF_GAME]
        if user_input is not None:
            tickets, errors, placeholders = _validate_tickets(user_input.get(CONF_TICKETS, ""), game)
            if not errors:
                return self.async_create_entry(data={CONF_TICKETS: tickets})
        current = "\n".join(self.config_entry.options.get(CONF_TICKETS, []))
        default = (user_input or {}).get(CONF_TICKETS, current)
        return self.async_show_form(
            step_id="init",
            data_schema=_tickets_schema(default),
            errors=errors,
            description_placeholders={**placeholders, "game": GAME_NAMES[game]},
        )
