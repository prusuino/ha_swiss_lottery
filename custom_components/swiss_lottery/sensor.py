"""Sensors: the published draw, the jackpot, the next draw and your tickets."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTRIBUTION,
    CONF_TICKETS,
    DOMAIN,
    GAME_EURODREAMS,
    GAME_EUROMILLIONS,
    GAME_NAMES,
    GAME_SWISSLOTTO,
)
from .coordinator import DATA_COORDINATOR, SwisslosCoordinator
from .device import device_info, entry_game
from .localization import t
from .swisslos import DrawResult, PrizeTier, next_draw_datetime
from .tickets import Ticket, TicketError, evaluate, parse_ticket

_LOGGER = logging.getLogger(__name__)

BONUS_KIND = {GAME_SWISSLOTTO: "lucky", GAME_EUROMILLIONS: "stars", GAME_EURODREAMS: "dream"}


def entry_tickets(entry: ConfigEntry) -> list[Ticket]:
    game = entry_game(entry)
    tickets: list[Ticket] = []
    for index, line in enumerate(entry.options.get(CONF_TICKETS, []), start=1):
        try:
            tickets.append(parse_ticket(line, game))
        except TicketError as err:
            # The line itself stays out of the log: it is the user's picks.
            _LOGGER.warning("Ignoring ticket line %d of %s: %s", index, GAME_NAMES[game], err.code)
    return tickets


def tier_dict(tier: PrizeTier) -> dict[str, Any]:
    return {"rank": tier.label, "winners": tier.winners, "prize": tier.prize, "prize_text": tier.prize_text}


def ticket_dict(ticket: Ticket, result: DrawResult) -> dict[str, Any]:
    outcome = evaluate(ticket, result)
    return {
        "numbers": list(ticket.numbers),
        "bonus": list(ticket.bonus),
        "matched": list(outcome.matched),
        "matched_bonus": list(outcome.matched_bonus),
        "matches": outcome.matches,
        "bonus_matches": outcome.bonus_matches,
        "rank": outcome.tier,
        "prize": outcome.prize,
        "prize_text": outcome.prize_text,
        "won": outcome.won,
    }


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SwisslosCoordinator = hass.data[DOMAIN][DATA_COORDINATOR]
    game = entry_game(entry)
    tickets = entry_tickets(entry)

    entities: list[SensorEntity] = [
        NumbersSensor(hass, coordinator, entry, tickets),
        BonusSensor(hass, coordinator, entry),
        DrawDateSensor(hass, coordinator, entry),
        NextDrawSensor(hass, coordinator, entry),
    ]
    if game == GAME_SWISSLOTTO:
        entities.append(ReplaySensor(hass, coordinator, entry))
    if game == GAME_EUROMILLIONS:
        entities.append(SecondChanceSensor(hass, coordinator, entry))
    if game in (GAME_SWISSLOTTO, GAME_EUROMILLIONS):
        entities.append(JackpotSensor(hass, coordinator, entry))
        entities.append(ExtraGameSensor(hass, coordinator, entry))
    for index, ticket in enumerate(tickets, start=1):
        entities.append(TicketSensor(hass, coordinator, entry, index, ticket))
    async_add_entities(entities)

    # Tickets that were removed from the options leave registry rows behind;
    # drop them so the entity list matches the configuration.
    registry = er.async_get(hass)
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        uid = reg_entry.unique_id or ""
        prefix = f"{entry.entry_id}_ticket_"
        if reg_entry.domain == "sensor" and uid.startswith(prefix):
            try:
                index = int(uid[len(prefix):])
            except ValueError:
                continue
            if index > len(tickets):
                registry.async_remove(reg_entry.entity_id)


class _LotterySensor(CoordinatorEntity[SwisslosCoordinator], SensorEntity):
    """Common wiring: name, unique id, device, attribution, suggested entity id."""

    _attr_has_entity_name = False
    name_key: str
    id_part: str

    def __init__(self, hass: HomeAssistant, coordinator: SwisslosCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._game = entry_game(entry)
        self._attr_name = self._name(hass)
        self._attr_unique_id = f"{entry.entry_id}_{self.id_part}"
        self._attr_device_info = device_info(hass, entry)
        self._attr_attribution = ATTRIBUTION
        # Suggested id only: existing entities keep theirs. The game is the
        # entry's unique id, so one entry per game exists and no suffix is
        # needed to keep two entries apart.
        self.entity_id = f"sensor.{DOMAIN}_{self._game}_{self.id_part}"

    def _name(self, hass: HomeAssistant) -> str:
        return t(self.name_key, hass)

    @property
    def result(self) -> DrawResult | None:
        data = self.coordinator.data
        return data.get(self._game) if data else None

    @property
    def available(self) -> bool:
        return super().available and self.result is not None


class NumbersSensor(_LotterySensor):
    """The drawn main numbers; its attributes carry the whole draw for the card."""

    name_key = "numbers_sensor_name"
    id_part = "numbers"
    _attr_icon = "mdi:dice-multiple"

    def __init__(self, hass, coordinator, entry, tickets: list[Ticket]) -> None:
        super().__init__(hass, coordinator, entry)
        self._tickets = tickets

    @property
    def native_value(self) -> str | None:
        r = self.result
        return ", ".join(str(n) for n in r.numbers) if r else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self.result
        if r is None:
            return {}
        extra = None
        if r.extra_game:
            extra = {
                "name": r.extra_game.name,
                "number": r.extra_game.number,
                "jackpot": r.extra_game.jackpot_chf,
                "ranks": [tier_dict(x) for x in r.extra_game.tiers],
            }
        next_dt = next_draw_datetime(r, dt_util.get_default_time_zone())
        return {
            "game": r.game,
            "game_name": GAME_NAMES[r.game],
            "draw_date": r.draw_date.isoformat(),
            "numbers": list(r.numbers),
            "bonus": list(r.bonus),
            "bonus_kind": BONUS_KIND[r.game],
            "replay": r.replay,
            "second_chance": list(r.second_chance),
            "extra_game": extra,
            "jackpot": r.jackpot_chf,
            "next_draw": next_dt.isoformat() if next_dt else None,
            "next_draw_closing": r.next_draw_closing,
            "ranks": [tier_dict(x) for x in r.tiers],
            "second_chance_ranks": [tier_dict(x) for x in r.second_chance_tiers],
            "tickets": [ticket_dict(ticket, r) for ticket in self._tickets],
        }


class BonusSensor(_LotterySensor):
    """Lucky number (Swiss Lotto), stars (EuroMillions) or dream number (EuroDreams)."""

    id_part = "bonus"
    _attr_icon = "mdi:star-circle"

    def _name(self, hass: HomeAssistant) -> str:
        return t(f"bonus_{self._game}", hass)

    @property
    def native_value(self) -> str | None:
        r = self.result
        return ", ".join(str(n) for n in r.bonus) if r else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self.result
        return {"bonus": list(r.bonus), "bonus_kind": BONUS_KIND[self._game]} if r else {}


class ReplaySensor(_LotterySensor):
    name_key = "replay_sensor_name"
    id_part = "replay"
    _attr_icon = "mdi:replay"

    @property
    def native_value(self) -> int | None:
        r = self.result
        return r.replay if r else None


class SecondChanceSensor(_LotterySensor):
    name_key = "second_chance_sensor_name"
    id_part = "second_chance"
    _attr_icon = "mdi:numeric"

    @property
    def native_value(self) -> str | None:
        r = self.result
        return ", ".join(str(n) for n in r.second_chance) if r and r.second_chance else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self.result
        if not r:
            return {}
        return {
            "numbers": list(r.second_chance),
            "ranks": [tier_dict(x) for x in r.second_chance_tiers],
        }


class ExtraGameSensor(_LotterySensor):
    """Joker (Swiss Lotto) or Super-Star (EuroMillions): the drawn code."""

    id_part = "extra_game"
    _attr_icon = "mdi:cards-playing"

    def _name(self, hass: HomeAssistant) -> str:
        return "Joker" if self._game == GAME_SWISSLOTTO else "Super-Star"

    @property
    def native_value(self) -> str | None:
        r = self.result
        return r.extra_game.number if r and r.extra_game else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self.result
        if not r or not r.extra_game:
            return {}
        return {
            "name": r.extra_game.name,
            "jackpot": r.extra_game.jackpot_chf,
            "ranks": [tier_dict(x) for x in r.extra_game.tiers],
        }


class DrawDateSensor(_LotterySensor):
    name_key = "draw_date_sensor_name"
    id_part = "draw_date"
    _attr_device_class = SensorDeviceClass.DATE

    @property
    def native_value(self) -> date | None:
        r = self.result
        return r.draw_date if r else None


class JackpotSensor(_LotterySensor):
    """Jackpot of the next draw as published by Swisslos, in CHF."""

    name_key = "jackpot_sensor_name"
    id_part = "jackpot"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "CHF"
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:cash-multiple"

    @property
    def native_value(self) -> float | None:
        r = self.result
        return r.jackpot_chf if r else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self.result
        if not r:
            return {}
        return {
            "extra_game": r.extra_game.name if r.extra_game else None,
            "extra_game_jackpot": r.extra_game.jackpot_chf if r.extra_game else None,
        }


class NextDrawSensor(_LotterySensor):
    """Closing time of the next draw (tickets must be in before it)."""

    name_key = "next_draw_sensor_name"
    id_part = "next_draw"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:calendar-clock"

    @property
    def native_value(self) -> datetime | None:
        r = self.result
        return next_draw_datetime(r, dt_util.get_default_time_zone()) if r else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self.result
        if not r:
            return {}
        return {
            "draw_date": r.next_draw.isoformat() if r.next_draw else None,
            "closing_time": r.next_draw_closing,
        }


class TicketSensor(_LotterySensor):
    """One of your tickets: state = number of main numbers matched in the latest draw."""

    name_key = "ticket_sensor_name"
    _attr_icon = "mdi:ticket-confirmation"
    _attr_entity_category = None

    def __init__(self, hass, coordinator, entry, index: int, ticket: Ticket) -> None:
        self.id_part = f"ticket_{index}"
        self._index = index
        self._ticket = ticket
        super().__init__(hass, coordinator, entry)

    def _name(self, hass: HomeAssistant) -> str:
        return t(self.name_key, hass, n=self._index)

    @property
    def native_value(self) -> int | None:
        r = self.result
        return evaluate(self._ticket, r).matches if r else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self.result
        if not r:
            return {}
        return {"draw_date": r.draw_date.isoformat(), **ticket_dict(self._ticket, r)}
