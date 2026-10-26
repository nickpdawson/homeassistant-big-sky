"""Weather forecast tests."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.weather import DOMAIN as WEATHER_DOMAIN, SERVICE_GET_FORECASTS
from homeassistant.core import HomeAssistant

from custom_components.big_sky.weather import map_condition

ENTITY = "weather.big_sky_resort"


async def test_daily_forecast_is_dated(hass: HomeAssistant, mock_feed, config_entry) -> None:
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY)
    assert state.state == "partlycloudy"

    response = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {"entity_id": ENTITY, "type": "daily"},
        blocking=True,
        return_response=True,
    )
    forecast = response[ENTITY]["forecast"]
    assert len(forecast) == 6
    # Fixture report time is 2026-10-26 10:49 MDT.
    dates = [datetime.fromisoformat(day["datetime"]) for day in forecast]
    assert [d.date().isoformat() for d in dates] == [
        "2026-10-26",
        "2026-10-27",
        "2026-10-28",
        "2026-10-29",
        "2026-10-30",
        "2026-10-31",
    ]
    assert all(d.tzinfo is not None for d in dates)
    assert forecast[0]["temperature"] == 66
    assert forecast[0]["templow"] == 32
    assert forecast[1]["condition"] == "sunny"


def test_map_condition() -> None:
    assert map_condition("Chance Snow Showers") == "snowy"
    assert map_condition("Slight Chance Rain Showers") == "rainy"
    assert map_condition("Rain And Snow Likely") == "snowy-rainy"
    assert map_condition("Mostly Cloudy") == "cloudy"
    assert map_condition("Blowing Dust") == "exceptional"
    assert map_condition(None) is None
