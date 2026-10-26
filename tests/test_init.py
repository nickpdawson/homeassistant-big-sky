"""Setup, unload, reload, entity and migration tests."""
from __future__ import annotations

import re

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.big_sky.const import (
    CONF_CREATE_LIFT_ENTITIES,
    DEFAULT_FEED_URL,
    DOMAIN,
)
from custom_components.big_sky.diagnostics import async_get_config_entry_diagnostics


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_unload_reload(hass: HomeAssistant, mock_feed, config_entry) -> None:
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("binary_sensor.big_sky_resort_resort_status").state == STATE_OFF

    assert await hass.config_entries.async_reload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_feed_down(
    hass: HomeAssistant, aioclient_mock, config_entry
) -> None:
    aioclient_mock.get(DEFAULT_FEED_URL, status=500)
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_entities(hass: HomeAssistant, mock_feed, config_entry) -> None:
    await _setup(hass, config_entry)

    snow = hass.states.get("sensor.big_sky_resort_snowfall_72h")
    assert snow.state == "3.0"
    assert snow.attributes["device_class"] == "precipitation"
    assert hass.states.get("sensor.big_sky_resort_snowfall_7_days").state == "3.0"
    assert hass.states.get("sensor.big_sky_resort_snow_depth").state == "2.0"
    assert hass.states.get("sensor.big_sky_resort_forecast_high_today").state == "66.0"

    trails = hass.states.get("sensor.big_sky_resort_trails_open")
    assert trails.state == "0"
    assert trails.attributes["state_class"] == "measurement"
    assert trails.attributes["advanced_intermediate"] == {"open": 0, "total": 46}

    tram = hass.states.get("sensor.big_sky_resort_tram")
    assert tram.state == "Closed"
    assert tram.attributes["name"] == "Lone Peak Tram"

    # A lift that is the only one in its area (single dict in the XML).
    lift = hass.states.get("binary_sensor.big_sky_resort_lift_lone_peak_tram")
    assert lift.state == STATE_OFF
    assert lift.attributes["device_class"] == "running"

    trail = hass.states.get("binary_sensor.big_sky_resort_trail_little_thunder")
    assert trail.state == STATE_OFF
    assert trail.attributes["device_class"] == "opening"

    registry = er.async_get(hass)
    entry = registry.async_get("binary_sensor.big_sky_resort_lift_lone_peak_tram")
    assert entry.unique_id == f"{config_entry.entry_id}_lift_1722"


async def test_parking_count_is_case_insensitive(
    hass: HomeAssistant, aioclient_mock, feed_xml, config_entry
) -> None:
    feed = feed_xml.replace(
        'name="Exchange Lot" status="Closed"', 'name="Exchange Lot" status="Open"'
    ).replace(
        'name="Carpool Lot" status="Closed"', 'name="Carpool Lot" status="OPEN"'
    )
    assert feed != feed_xml
    aioclient_mock.get(DEFAULT_FEED_URL, text=feed)
    await _setup(hass, config_entry)

    parking = hass.states.get("sensor.big_sky_resort_parking_lots_open")
    assert parking.state == "2"
    assert parking.attributes["Exchange Lot"]["status"] == "Open"


async def test_sparse_feed(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    """An off-season feed with most elements missing still sets up."""
    aioclient_mock.get(
        DEFAULT_FEED_URL,
        text='<report name="Big Sky"><operations resortStatus="Open"/>'
        '<facilities><areas><area name="Only"><lifts><lift name="Solo" status="open"/>'
        "</lifts></area></areas></facilities></report>",
    )
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("binary_sensor.big_sky_resort_resort_status").state == STATE_ON
    assert hass.states.get("binary_sensor.big_sky_resort_lift_solo").state == STATE_ON
    assert hass.states.get("sensor.big_sky_resort_snow_depth").state == "unknown"
    assert hass.states.get("sensor.big_sky_resort_parking_lots_open").state == "0"


async def test_unique_id_migration(hass: HomeAssistant, mock_feed, config_entry) -> None:
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old_lift = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "big_sky_lift_lone_peak_tram",
        config_entry=config_entry,
        suggested_object_id="lift_lone_peak_tram",
    )
    old_sensor = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "big_sky_current_weather",
        config_entry=config_entry,
        suggested_object_id="big_sky_current_weather",
    )
    unknown = registry.async_get_or_create(
        "binary_sensor", DOMAIN, "big_sky_trail_gone_trail", config_entry=config_entry
    )

    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert (
        registry.async_get(old_lift.entity_id).unique_id
        == f"{config_entry.entry_id}_lift_1722"
    )
    assert (
        registry.async_get(old_sensor.entity_id).unique_id
        == f"{config_entry.entry_id}_forecast_high"
    )
    # Old entity_ids are kept, so no duplicates appear.
    assert hass.states.get(old_lift.entity_id) is not None
    assert hass.states.get("binary_sensor.big_sky_resort_lift_lone_peak_tram") is None
    assert registry.async_get(unknown.entity_id).unique_id == "big_sky_trail_gone_trail"


def _without(feed_xml: str, tag: str, name: str) -> str:
    feed, count = re.subn(rf'<{tag} name="{name}"[^>]*/>', "", feed_xml)
    assert count == 1
    return feed


async def _refresh(hass: HomeAssistant, aioclient_mock, entry, feed: str) -> None:
    aioclient_mock.clear_requests()
    aioclient_mock.get(DEFAULT_FEED_URL, text=feed)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_new_items_added_on_refresh(
    hass: HomeAssistant, aioclient_mock, feed_xml, config_entry
) -> None:
    """Winter lifts and trails that show up later get entities without a reload."""
    summer = _without(_without(feed_xml, "lift", "Bear Back"), "trail", "Little Thunder")
    aioclient_mock.get(DEFAULT_FEED_URL, text=summer)
    await _setup(hass, config_entry)
    lift_id = "binary_sensor.big_sky_resort_lift_bear_back"
    trail_id = "binary_sensor.big_sky_resort_trail_little_thunder"
    assert hass.states.get(lift_id) is None
    assert hass.states.get(trail_id) is None

    await _refresh(hass, aioclient_mock, config_entry, feed_xml)
    assert hass.states.get(lift_id).state == STATE_OFF
    assert hass.states.get(trail_id).state == STATE_OFF
    registry = er.async_get(hass)
    assert registry.async_get(lift_id).unique_id == f"{config_entry.entry_id}_lift_1222"

    # Gone again: the entity stays and goes unavailable.
    await _refresh(hass, aioclient_mock, config_entry, summer)
    assert hass.states.get(lift_id).state == STATE_UNAVAILABLE
    assert registry.async_get(lift_id) is not None


async def test_new_items_respect_options(
    hass: HomeAssistant, aioclient_mock, feed_xml, config_entry
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={**config_entry.data, CONF_CREATE_LIFT_ENTITIES: False},
    )
    aioclient_mock.get(DEFAULT_FEED_URL, text=_without(feed_xml, "lift", "Bear Back"))
    await _setup(hass, entry)
    await _refresh(hass, aioclient_mock, entry, feed_xml)
    assert hass.states.get("binary_sensor.big_sky_resort_lift_bear_back") is None
    assert hass.states.get("binary_sensor.big_sky_resort_trail_little_thunder") is not None


async def test_legacy_entry_migrated_when_item_returns(
    hass: HomeAssistant, aioclient_mock, feed_xml, config_entry
) -> None:
    """A pre-1.1 entry for a lift missing at setup keeps its entity_id when the lift returns."""
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "binary_sensor",
        DOMAIN,
        "big_sky_lift_bear_back",
        config_entry=config_entry,
        suggested_object_id="lift_bear_back_poma",
    )
    assert old.entity_id == "binary_sensor.lift_bear_back_poma"

    aioclient_mock.get(DEFAULT_FEED_URL, text=_without(feed_xml, "lift", "Bear Back"))
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(old.entity_id).unique_id == "big_sky_lift_bear_back"

    await _refresh(hass, aioclient_mock, config_entry, feed_xml)

    new_unique_id = f"{config_entry.entry_id}_lift_1222"
    assert registry.async_get(old.entity_id).unique_id == new_unique_id
    assert hass.states.get(old.entity_id).state == STATE_OFF
    assert hass.states.get("binary_sensor.big_sky_resort_lift_bear_back") is None
    matches = [
        e
        for e in er.async_entries_for_config_entry(registry, config_entry.entry_id)
        if e.unique_id == new_unique_id
    ]
    assert len(matches) == 1


async def test_migrate_v1_entry(hass: HomeAssistant, mock_feed) -> None:
    entry = MockConfigEntry(domain=DOMAIN, version=1, data={})
    await _setup(hass, entry)
    assert entry.version == 2
    assert entry.data["feed_url"] == DEFAULT_FEED_URL


async def test_diagnostics(hass: HomeAssistant, mock_feed, config_entry) -> None:
    await _setup(hass, config_entry)
    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diag["counts"]["lifts"] == 40
    assert diag["counts"]["trails"] == 319
    # Two trails share feed id 11711; both must survive with distinct keys.
    assert "11711_headwaters_bowl" in diag["data"]["trails"]
    assert "11711_white_magic" in diag["data"]["trails"]
    assert diag["coordinator"]["last_update_success"] is True
