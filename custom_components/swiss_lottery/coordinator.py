"""One shared coordinator: a single hourly request serves every game entry.

The results of all three games sit in the footer of one swisslos.ch page, so
the integration keeps one DataUpdateCoordinator per Home Assistant instance,
created by the first config entry and released by the last.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import swisslos
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

DATA_COORDINATOR = "coordinator"
DATA_ENTRIES = "entries"


class SwisslosCoordinator(DataUpdateCoordinator[dict[str, swisslos.DrawResult]]):
    """Fetches the published results of all games once per interval."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=None,  # shared by every entry on purpose
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict[str, swisslos.DrawResult]:
        try:
            return await swisslos.async_fetch_results(async_get_clientsession(self.hass))
        except swisslos.SwisslosCommunicationError as err:
            raise UpdateFailed(f"swisslos.ch unreachable: {err}") from err
        except swisslos.SwisslosParseError as err:
            raise UpdateFailed(f"swisslos.ch page not understood: {err}") from err


def get_coordinator(hass: HomeAssistant) -> SwisslosCoordinator:
    """The instance-wide coordinator, created on first use."""
    store = hass.data.setdefault(DOMAIN, {})
    coordinator = store.get(DATA_COORDINATOR)
    if coordinator is None:
        coordinator = SwisslosCoordinator(hass)
        store[DATA_COORDINATOR] = coordinator
        store[DATA_ENTRIES] = set()
    return coordinator


def release_coordinator(hass: HomeAssistant, entry_id: str) -> None:
    """Forget the coordinator once no entry uses it any more."""
    store = hass.data.get(DOMAIN)
    if not store:
        return
    store.get(DATA_ENTRIES, set()).discard(entry_id)
    if not store.get(DATA_ENTRIES):
        hass.data.pop(DOMAIN, None)
