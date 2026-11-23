"""The triggers "Draw published" and "Ticket won" with real automations, on
registered entities whose state is set by hand - also across an outage."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.swiss_lottery import trigger
from custom_components.swiss_lottery.const import DOMAIN


def _entity(hass: HomeAssistant, domain: str, name: str, device_class: str | None = None, platform: str = DOMAIN) -> str:
    return er.async_get(hass).async_get_or_create(domain, platform, f"entry_{name}", suggested_object_id=name, original_device_class=device_class).entity_id


async def _play(hass: HomeAssistant, entity_id: str, *states: str) -> None:
    for state in states:
        hass.states.async_set(entity_id, state, {"device_class": "date"} if entity_id.startswith("sensor.") else {})
        await hass.async_block_till_done()


async def _automation(hass: HomeAssistant, name: str, entity_ids) -> list:
    calls = async_mock_service(hass, "test", name)
    assert await async_setup_component(hass, "automation", {"automation": {
        "alias": name, "trigger": {"trigger": f"swiss_lottery.{name}", "target": {"entity_id": entity_ids}},
        "action": {"action": f"test.{name}"},
    }})
    await hass.async_block_till_done()
    assert hass.states.get(f"automation.{name}") is not None, "the automation was rejected"
    return calls


async def test_draw_published(hass: HomeAssistant, enable_custom_integrations) -> None:
    assert set(await trigger.async_get_triggers(hass)) == {"ticket_won", "draw_published", "jackpot_crossed_threshold"}
    draw = _entity(hass, "sensor", "draw", "date")
    foreign = _entity(hass, "sensor", "bin_day", "date", "another_integration")
    await _play(hass, draw, "2026-11-18")
    await _play(hass, foreign, "2026-11-18")
    calls = await _automation(hass, "draw_published", [draw, foreign])
    await _play(hass, foreign, "2026-11-21")  # not ours
    assert len(calls) == 0
    await _play(hass, draw, "2026-11-21")
    assert len(calls) == 1
    await _play(hass, draw, "unavailable", "2026-11-21")  # the same draw after an outage
    assert len(calls) == 1
    await _play(hass, draw, "unavailable", "2026-11-25")  # a draw published during the outage
    assert len(calls) == 2


async def test_draw_with_nothing_known_from_before(hass: HomeAssistant, enable_custom_integrations) -> None:
    draw = _entity(hass, "sensor", "draw", "date")
    await _play(hass, draw, "unavailable")
    calls = await _automation(hass, "draw_published", draw)
    await _play(hass, draw, "2026-11-21")  # a draw of unknown age
    assert len(calls) == 0
    await _play(hass, draw, "unknown", "2026-11-25")
    assert len(calls) == 1


async def test_ticket_won(hass: HomeAssistant, enable_custom_integrations) -> None:
    win = _entity(hass, "binary_sensor", "win")
    await _play(hass, win, "off")
    calls = await _automation(hass, "ticket_won", win)
    await _play(hass, win, "unavailable", "on")  # the winning draw came in during an outage
    assert len(calls) == 1
    await _play(hass, win, "unavailable", "on")  # still the same win
    assert len(calls) == 1
    await _play(hass, win, "off", "on")
    assert len(calls) == 2
