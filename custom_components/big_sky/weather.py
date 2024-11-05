"""Weather platform for Big Sky Resort."""
from __future__ import annotations

from homeassistant.components.weather import (
   WeatherEntity,
   WeatherEntityFeature,
   Forecast,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfTemperature

from .const import DOMAIN

WEATHER_ICONS = {
   "Sunny": "sunny",
   "Mostly Sunny": "partlycloudy",
   "Partly Sunny": "partlycloudy", 
   "Mostly Cloudy": "cloudy",
   "Cloudy": "cloudy",
   "Rain": "rainy",
   "Snow": "snowy",
   "Rain Showers": "rainy",
   "Snow Showers": "snowy",
   "Partly Cloudy": "partlycloudy",
   "Clear": "clear-night",
   "Chance Rain Showers": "rainy",
   "Chance Snow Showers": "snowy",
   "Slight Chance Rain Showers": "rainy",
}

async def async_setup_entry(
   hass: HomeAssistant,
   config_entry: ConfigEntry,
   async_add_entities: AddEntitiesCallback,
) -> None:
   """Set up Big Sky weather platform."""
   coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
   async_add_entities([BigSkyWeather(coordinator)], True)

class BigSkyWeather(CoordinatorEntity, WeatherEntity):
   """Big Sky weather implementation."""

   def __init__(self, coordinator):
       """Initialize weather entity."""
       super().__init__(coordinator)
       self._attr_name = "Big Sky Weather"
       self._attr_unique_id = "big_sky_weather"
       self._attr_native_temperature_unit = UnitOfTemperature.FAHRENHEIT
       self._attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

   @property
   def condition(self):
       """Return current condition."""
       try:
           condition = self.coordinator.data["report"]["forecast"]["day"][0]["@weather"]
           return WEATHER_ICONS.get(condition, "exceptional")
       except (KeyError, IndexError):
           return None

   @property
   def native_temperature(self):
       """Return current temperature."""
       try:
           return float(self.coordinator.data["report"]["forecast"]["day"][0]["@high"])
       except (KeyError, IndexError, ValueError):
           return None

   @property
   def native_precipitation_unit(self) -> str:
       """Return precipitation unit."""
       return "in"

   @property
   def forecast(self) -> list[Forecast] | None:
       """Return forecast array."""
       try:
           forecasts = []
           for day in self.coordinator.data["report"]["forecast"]["day"]:
               forecast = {
                   "datetime": day["@name"],
                   "native_temperature": float(day["@high"]),
                   "native_templow": float(day["@low"]),
                   "condition": WEATHER_ICONS.get(day["@weather"], "exceptional"),
                   "precipitation_probability": None,
               }
               forecasts.append(forecast)
           return forecasts
       except (KeyError, IndexError, ValueError):
           return None