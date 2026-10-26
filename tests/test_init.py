"""Setup, unload, reload, entity and migration tests."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.big_sky.const import DEFAULT_FEED_URL, DOMAIN
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
