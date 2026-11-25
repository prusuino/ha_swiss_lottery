"""One shared coordinator: once an hour it reads the results of the games
that have a config entry, one swisslos.ch page per game.

The integration keeps one DataUpdateCoordinator per Home Assistant instance,
created by the first config entry and released by the last.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import swisslos
from .const import CONF_GAME, DOMAIN, GAMES, UPDATE_INTERVAL_SECONDS
from .issues import IssueReporter, async_clear_entry_issues

# The coordinator is shared by every entry, so its issues carry this id
# instead of an entry id; they are withdrawn when the last entry goes.
SHARED_ISSUE_OWNER = "shared"

_LOGGER = logging.getLogger(__name__)

DATA_COORDINATOR = "coordinator"
DATA_ENTRIES = "entries"


class SwisslosCoordinator(DataUpdateCoordinator[dict[str, swisslos.DrawResult]]):
    """Fetches the published results of the configured games once per interval."""

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=None,  # shared by every entry on purpose
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.issues = IssueReporter(hass, SHARED_ISSUE_OWNER)
        self._load_lock = asyncio.Lock()

    def _games(self) -> tuple[str, ...] | None:
        """The games that have a config entry, in a fixed order; None (every
        game) while no entry is known yet."""
        configured = {
            entry.data.get(CONF_GAME)
            for entry in self.hass.config_entries.async_entries(DOMAIN, include_disabled=False)
        }
        return tuple(game for game in GAMES if game in configured) or None

    async def async_ensure_game(self, game: str) -> bool:
        """Load the results unless this game is already there. Entries set up
        at the same time wait for the one refresh that covers them all."""
        async with self._load_lock:
            if self.data is None or game not in self.data:
                await self.async_refresh()
                return self.last_update_success
        return True

    async def _async_update_data(self) -> dict[str, swisslos.DrawResult]:
        try:
            results = await swisslos.async_fetch_results(async_get_clientsession(self.hass), self._games())
        except swisslos.SwisslosCommunicationError as err:
            self.issues.failure("unreachable", {"host": "swisslos.ch"})
            raise UpdateFailed(f"swisslos.ch unreachable: {err}") from err
        except swisslos.SwisslosParseError as err:
            # The page changed: that does not fix itself, an update of the
            # integration is needed. Three times in a row rules out a glitch.
            self.issues.failure("page_changed", {"error": str(err)})
            raise UpdateFailed(f"swisslos.ch page not understood: {err}") from err
        self.issues.clear("unreachable")
        self.issues.clear("page_changed")
        return results


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
        async_clear_entry_issues(hass, SHARED_ISSUE_OWNER)
