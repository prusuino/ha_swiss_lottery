"""Triggers for Swiss Lottery.

"A ticket has won", "A draw was published" and "Jackpot crossed a threshold"
for the automation editor's trigger list. Each trigger targets the
integration's own entities: a target that expands to other entities (a
device, an area) is narrowed to the ones this integration created.

The trigger platform API arrived in Home Assistant 2026.10. On an older
version the module still imports, but offers no triggers.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

try:
    from homeassistant.helpers.automation import DomainSpec
    from homeassistant.helpers.trigger import (
        EntityTriggerBase,
        Trigger,
        make_entity_numerical_state_crossed_threshold_trigger,
        make_entity_target_state_trigger,
    )
except ImportError:  # Home Assistant before 2026.10: no trigger platform API
    TRIGGERS: dict = {}
else:
    WIN_DOMAIN_SPECS = {BINARY_SENSOR_DOMAIN: DomainSpec()}
    DRAW_DATE_DOMAIN_SPECS = {SENSOR_DOMAIN: DomainSpec(device_class=SensorDeviceClass.DATE)}
    JACKPOT_DOMAIN_SPECS = {SENSOR_DOMAIN: DomainSpec(device_class=SensorDeviceClass.MONETARY)}

    def _own_entities(hass: HomeAssistant, entities: set[str]) -> set[str]:
        """Keep only entities created by this integration."""
        registry = er.async_get(hass)
        return {
            entity_id
            for entity_id in entities
            if (entry := registry.async_get(entity_id)) is not None
            and entry.platform == DOMAIN
        }

    class _TicketWon(make_entity_target_state_trigger(WIN_DOMAIN_SPECS, STATE_ON)):
        """The win entity switches to on: at least one ticket won the latest draw."""

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    class _DrawPublished(EntityTriggerBase):
        """The draw-date entity changes: Swisslos published a new draw."""

        _domain_specs = DRAW_DATE_DOMAIN_SPECS

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    class _JackpotCrossedThreshold(
        make_entity_numerical_state_crossed_threshold_trigger(JACKPOT_DOMAIN_SPECS, "CHF")
    ):
        """The jackpot entity crosses into the configured range."""

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    TRIGGERS: dict[str, type[Trigger]] = {
        "ticket_won": _TicketWon,
        "draw_published": _DrawPublished,
        "jackpot_crossed_threshold": _JackpotCrossedThreshold,
    }


async def async_get_triggers(hass: HomeAssistant) -> dict:
    """Return the triggers of this integration."""
    return TRIGGERS
