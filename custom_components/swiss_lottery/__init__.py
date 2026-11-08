"""Swiss Lottery integration: published Swisslos draw results and your tickets."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import DATA_ENTRIES, SwisslosCoordinator, get_coordinator, release_coordinator

# Every game entry shares the one coordinator; runtime_data points at it.
type SwissLotteryConfigEntry = ConfigEntry[SwisslosCoordinator]
from .frontend import async_serve_card

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["binary_sensor", "sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: SwissLotteryConfigEntry) -> bool:
    coordinator = get_coordinator(hass)
    if coordinator.data is None:
        await coordinator.async_refresh()
        if not coordinator.last_update_success:
            raise ConfigEntryNotReady(str(coordinator.last_exception))
    hass.data[DOMAIN][DATA_ENTRIES].add(entry.entry_id)
    entry.runtime_data = coordinator

    await async_serve_card(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        release_coordinator(hass, entry.entry_id)
    return unloaded
