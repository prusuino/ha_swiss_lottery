"""Win binary sensor: on when at least one of your tickets won in the latest draw."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import DATA_COORDINATOR, SwisslosCoordinator
from .device import device_info, entry_game
from .localization import t
from .sensor import entry_tickets, ticket_dict
from .tickets import Ticket


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: SwisslosCoordinator = hass.data[DOMAIN][DATA_COORDINATOR]
    async_add_entities([WinBinarySensor(hass, coordinator, entry, entry_tickets(entry))])


class WinBinarySensor(CoordinatorEntity[SwisslosCoordinator], BinarySensorEntity):
    """On while the latest draw pays out on at least one configured ticket.

    Off when no ticket is configured; a notification automation can trigger
    on the transition to on and read the winning tickets from the attributes.
    """

    _attr_has_entity_name = False
    _attr_icon = "mdi:trophy"

    def __init__(
        self, hass: HomeAssistant, coordinator: SwisslosCoordinator, entry: ConfigEntry, tickets: list[Ticket]
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._game = entry_game(entry)
        self._tickets = tickets
        self._attr_name = t("win_sensor_name", hass)
        self._attr_unique_id = f"{entry.entry_id}_win"
        self._attr_device_info = device_info(hass, entry)
        self._attr_attribution = ATTRIBUTION
        self.entity_id = f"binary_sensor.{DOMAIN}_{self._game}_win"

    @property
    def _result(self):
        data = self.coordinator.data
        return data.get(self._game) if data else None

    @property
    def available(self) -> bool:
        return super().available and self._result is not None

    @property
    def is_on(self) -> bool | None:
        r = self._result
        if r is None:
            return None
        return any(ticket_dict(ticket, r)["won"] for ticket in self._tickets)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        r = self._result
        if r is None:
            return {}
        results = [ticket_dict(ticket, r) for ticket in self._tickets]
        return {
            "draw_date": r.draw_date.isoformat(),
            "tickets": len(results),
            "winning_tickets": [
                {"ticket": i, "rank": x["rank"], "prize": x["prize"], "prize_text": x["prize_text"]}
                for i, x in enumerate(results, start=1)
                if x["won"]
            ],
        }
