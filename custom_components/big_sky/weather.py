"""Weather entity for Big Sky Resort."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import UnitOfPrecipitationDepth, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import RESORT_TIME_ZONE
from .coordinator import BigSkyConfigEntry, BigSkyCoordinator
from .entity import BigSkyEntity
from .feed import ResortData

# Feed condition text -> HA condition. Matching is on lower case text.
CONDITIONS = {
    "sunny": "sunny",
    "clear": "sunny",
    "mostly sunny": "partlycloudy",
    "partly sunny": "partlycloudy",
    "partly cloudy": "partlycloudy",
    "mostly clear": "partlycloudy",
    "mostly cloudy": "cloudy",
    "cloudy": "cloudy",
    "fog": "fog",
    "windy": "windy",
    "rain": "rainy",
    "rain showers": "rainy",
    "snow": "snowy",
    "snow showers": "snowy",
    "rain and snow": "snowy-rainy",
    "thunderstorms": "lightning-rainy",
}


def map_condition(text: str | None) -> str | None:
    """Map feed text like 'Chance Snow Showers' to an HA condition."""
    if not text:
        return None
    text = text.strip().lower()
    if text in CONDITIONS:
        return CONDITIONS[text]
    for prefix in ("slight chance ", "chance ", "likely ", "isolated ", "scattered "):
        if text.startswith(prefix) and text.removeprefix(prefix) in CONDITIONS:
            return CONDITIONS[text.removeprefix(prefix)]
    if "snow" in text and "rain" in text:
        return "snowy-rainy"
    if "snow" in text:
        return "snowy"
    if "thunder" in text:
        return "lightning-rainy"
    if "rain" in text or "shower" in text:
        return "rainy"
    return "exceptional"


def build_forecast(data: ResortData) -> list[Forecast]:
    """Date each forecast row from the report day plus its position.

    Row 0 is the report day ('Today', 'This Afternoon'), row 1 the next
    day, and so on. Dates are midnight resort time, sent as ISO strings.
    """
    tz = dt_util.get_time_zone(RESORT_TIME_ZONE)
    report_time = data.updated or dt_util.utcnow()
    start = report_time.astimezone(tz).date()
    forecast: list[Forecast] = []
    for index, day in enumerate(data.forecast):
        when = datetime.combine(start + timedelta(days=index), time.min, tzinfo=tz)
        forecast.append(
            Forecast(
                datetime=when.isoformat(),
                condition=map_condition(day.weather),
                native_temperature=day.high,
                native_templow=day.low,
            )
        )
    return forecast


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BigSkyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Big Sky weather entity."""
    async_add_entities([BigSkyWeather(entry.runtime_data)])


class BigSkyWeather(BigSkyEntity, WeatherEntity):
    """Daily forecast from the mountain report."""

    # The entity takes the device name, like a typical weather entity.
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.INCHES
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(self, coordinator: BigSkyCoordinator) -> None:
        super().__init__(coordinator, "weather")

    @property
    def condition(self) -> str | None:
        forecast = self.coordinator.data.forecast
        return map_condition(forecast[0].weather) if forecast else None

    @property
    def native_temperature(self) -> float | None:
        # The feed has no current reading; today's high is the closest value.
        forecast = self.coordinator.data.forecast
        return forecast[0].high if forecast else None

    async def async_forecast_daily(self) -> list[Forecast] | None:
        return build_forecast(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        super()._handle_coordinator_update()
        self.coordinator.config_entry.async_create_task(
            self.hass, self.async_update_listeners(("daily",))
        )
