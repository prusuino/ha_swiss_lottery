"""Shared device info and entity-id helpers for all platforms."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import CONF_GAME, CONFIGURATION_URL, DOMAIN, GAME_NAMES, GAME_SWISSLOTTO
from .localization import t


def entry_game(entry: ConfigEntry) -> str:
    return entry.data.get(CONF_GAME, GAME_SWISSLOTTO)


def device_info(hass: HomeAssistant, entry: ConfigEntry) -> DeviceInfo:
    game = entry_game(entry)
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=GAME_NAMES[game],
        manufacturer=t("manufacturer", hass),
        model=t("model", hass),
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=CONFIGURATION_URL,
    )
