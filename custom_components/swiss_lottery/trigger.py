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
from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
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

    _GAP = (STATE_UNAVAILABLE, STATE_UNKNOWN)

    class _AcrossGaps:
        """Lets a target-state trigger see a change that follows a gap.

        The core skips every change out of "unavailable" or "unknown". While
        the source cannot be reached the entities are unavailable, so
        whatever began during the outage would switch an entity from
        unavailable straight to its new state, and the core would not fire.
        Such a change is let through here and judged against the last state
        seen before the gap (the tracked value, which can be an attribute): it
        fires when that value was not already the
        target. With nothing known from before the gap, a trigger that
        announces something (`_fire_without_history`) fires, the others
        stay quiet. The core asks is_valid_state for every state with a
        value and only then is_valid_transition, so the states are
        remembered there.
        """

        _excluded_from_states = frozenset()
        _fire_without_history = False

        def __init__(self, hass: HomeAssistant, config) -> None:
            super().__init__(hass, config)
            self._last_state: dict[str, str] = {}
            self._previous_state: dict[str, str | None] = {}

        def entity_filter(self, entities: set[str]) -> set[str]:
            # Start from what the entities show now, so that a gap right
            # after the automation starts is judged against a known state.
            kept = super().entity_filter(entities)
            for entity_id in kept:
                state = self._hass.states.get(entity_id)
                if entity_id not in self._last_state and state is not None and state.state not in _GAP:
                    self._last_state[entity_id] = self._get_tracked_value(state)
            return kept

        def is_valid_state(self, state, report_not_triggered) -> bool:
            self._previous_state[state.entity_id] = self._last_state.get(state.entity_id)
            self._last_state[state.entity_id] = self._get_tracked_value(state)
            return super().is_valid_state(state, report_not_triggered)

        def is_valid_transition(self, from_state, to_state) -> bool:
            if from_state.state not in _GAP:
                return super().is_valid_transition(from_state, to_state)
            before = self._previous_state.get(to_state.entity_id)
            if before is None:
                return self._fire_without_history
            return before not in self._to_states

    class _TicketWon(_AcrossGaps, make_entity_target_state_trigger(WIN_DOMAIN_SPECS, STATE_ON)):
        """The win entity switches to on: at least one ticket won the latest draw.

        After a gap it fires unless the entity was already on before it."""

        _fire_without_history = True

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

    class _DrawPublished(EntityTriggerBase):
        """The draw-date entity changes: Swisslos published a new draw.

        After a gap it fires when the date differs from the one seen before
        it; a draw that only reappears does not fire again."""

        _domain_specs = DRAW_DATE_DOMAIN_SPECS
        _excluded_from_states = frozenset()

        def __init__(self, hass: HomeAssistant, config) -> None:
            super().__init__(hass, config)
            self._last_draw: dict[str, str] = {}
            self._previous_draw: dict[str, str | None] = {}

        def entity_filter(self, entities: set[str]) -> set[str]:
            return _own_entities(self._hass, super().entity_filter(entities))

        def is_valid_state(self, state: State, report_not_triggered) -> bool:
            self._previous_draw[state.entity_id] = self._last_draw.get(state.entity_id)
            self._last_draw[state.entity_id] = state.state
            return True

        def is_valid_transition(self, from_state: State, to_state: State) -> bool:
            if from_state.state in _GAP:
                before = self._previous_draw.get(to_state.entity_id)
                return before is not None and before != to_state.state
            return from_state.state != to_state.state

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
