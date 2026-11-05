"""Serving of the bundled Lovelace card (swiss-lottery-card.js).

Registers a static path so the card file bundled in this integration's
frontend/ directory is reachable under /swiss_lottery_files/. Adding it as a
Lovelace resource is left to the user: writing into another component's
storage is not an integration's job, and the resource list belongs to the
dashboard configuration the user controls. The README documents the one-time
registration.
"""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "swiss-lottery-card.js"
CARD_URL_BASE = f"/{DOMAIN}_files/{CARD_FILENAME}"
_REGISTERED_FLAG = f"{DOMAIN}_card_served"


async def async_serve_card(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Make the bundled card file reachable over HTTP.

    Idempotent per HA run; safe to call from every config entry setup. The
    flag is claimed before the await so concurrent entry setups do not
    register twice, and released again if the registration raises, so the
    next entry setup retries instead of remembering a failure as done.
    """
    if hass.data.get(_REGISTERED_FLAG):
        return
    hass.data[_REGISTERED_FLAG] = True
    card_path = Path(__file__).parent / "frontend" / CARD_FILENAME
    registered = False
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL_BASE, str(card_path), cache_headers=False)]
        )
        registered = True
    finally:
        if not registered:
            hass.data.pop(_REGISTERED_FLAG, None)
    _LOGGER.debug("Serving the bundled card at %s", CARD_URL_BASE)
