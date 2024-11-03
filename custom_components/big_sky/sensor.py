"""Sensor platform for Big Sky Resort."""
from __future__ import annotations
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    UnitOfLength,
    UnitOfTemperature,
    PERCENTAGE,
)

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Big Sky Resort sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    sensors = [
        BigSkySnowDepthSensor(coordinator),
        BigSkySnowfall24hSensor(coordinator),
        BigSkyCurrentWeatherSensor(coordinator),
        BigSkyTerrainParksSensor(coordinator),
        BigSkyTrailsByDifficultySensor(coordinator),
        BigSkyTramSensor(coordinator),
        BigSkyParkingSensor(coordinator),
        BigSkyShuttleSensor(coordinator),
    ]

    async_add_entities(sensors)

class BigSkySnowDepthSensor(CoordinatorEntity, SensorEntity):
    """Snow depth sensor."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Big Sky Snow Depth"
        self._attr_unique_id = "big_sky_snow_depth"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfLength.INCHES
        self._attr_icon = "mdi:ruler"

    @property
    def native_value(self):
        """Return snow depth."""
        return float(self.coordinator.data["report"]["currentConditions"]["resortLocations"]["location"]["@base"])

class BigSkySnowfall24hSensor(CoordinatorEntity, SensorEntity):
    """24h snowfall sensor."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Big Sky 24h Snowfall"
        self._attr_unique_id = "big_sky_snowfall_24h"
        self._attr_device_class = SensorDeviceClass.DISTANCE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfLength.INCHES
        self._attr_icon = "mdi:weather-snowy-heavy"

    @property
    def native_value(self):
        """Return 24h snowfall."""
        return float(self.coordinator.data["report"]["currentConditions"]["resortLocations"]["location"]["@snow24Hours"])

class BigSkyTerrainParksSensor(CoordinatorEntity, SensorEntity):
    """Terrain parks sensor."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Big Sky Terrain Parks"
        self._attr_unique_id = "big_sky_terrain_parks"
        self._attr_icon = "mdi:snowboard"

    @property
    def native_value(self):
        """Return number of open parks."""
        return self.coordinator.data["report"]["currentConditions"]["resortwide"]["@numParksOpen"]

    @property
    def extra_state_attributes(self):
        """Return park details."""
        parks_data = {}
        areas = self.coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if "freestyleTerrain" in area and "parks" in area["freestyleTerrain"]:
                    parks = area["freestyleTerrain"]["parks"]["park"]
                    if isinstance(parks, list):
                        for park in parks:
                            parks_data[park["@name"]] = {
                                "status": park["@status"],
                                "difficulty": park["@difficulty"],
                                "groomed": park.get("@groomedOrCut", "")
                            }
                    else:
                        parks_data[parks["@name"]] = {
                            "status": parks["@status"],
                            "difficulty": parks["@difficulty"],
                            "groomed": parks.get("@groomedOrCut", "")
                        }
        return parks_data

class BigSkyTrailsByDifficultySensor(CoordinatorEntity, SensorEntity):
    """Trails by difficulty sensor."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Big Sky Trails by Difficulty"
        self._attr_unique_id = "big_sky_trails_by_difficulty"
        self._attr_icon = "mdi:ski"

    @property
    def native_value(self):
        """Return total open trails."""
        return self.coordinator.data["report"]["currentConditions"]["resortwide"]["@numTrailsOpen"]

    @property
    def extra_state_attributes(self):
        """Return trail counts by difficulty."""
        difficulties = {
            "beginner": {"open": 0, "total": 0},
            "intermediate": {"open": 0, "total": 0},
            "advanced": {"open": 0, "total": 0},
            "expert": {"open": 0, "total": 0},
            "high_exposure": {"open": 0, "total": 0}
        }
        
        areas = self.coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if "trails" in area:
                    trails = area["trails"]["trail"]
                    if isinstance(trails, list):
                        for trail in trails:
                            diff = trail["@difficulty"].lower().replace(" ", "_")
                            if diff in difficulties:
                                difficulties[diff]["total"] += 1
                                if trail["@status"].lower() == "open":
                                    difficulties[diff]["open"] += 1
        return difficulties

class BigSkyTramSensor(CoordinatorEntity, SensorEntity):
    """Lone Peak Tram sensor."""
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Big Sky Tram"
        self._attr_unique_id = "big_sky_tram"
        self._attr_icon = "mdi:ski-lift"

    @property
    def native_value(self):
        """Return tram status."""
        areas = self.coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if area["@name"] == "Lone Peak Area":
                    if "lifts" in area:
                        tram = area["lifts"]["lift"]
                        return tram["@status"]
        return "Unknown"

    @property
    def extra_state_attributes(self):
        """Return tram details."""
        tram_data = {}
        areas = self.coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if area["@name"] == "Lone Peak Area":
                    if "lifts" in area:
                        tram = area["lifts"]["lift"]
                        tram_data.update({
                            "capacity": tram["@capacity"],
                            "type": tram["@type"],
                            "status_detail": tram["@statusDetail"],
                            "open_time": tram["@openTime"],
                            "close_time": tram["@closeTime"],
                            "skier_wait_time": tram.get("@skierWaitTime", ""),
                            "scenic_wait_time": tram.get("@scenicWaitTime", ""),
                            "serviced_trails": self._get_serviced_trails(area)
                        })
        return tram_data

    def _get_serviced_trails(self, area):
        """Get trails serviced by tram."""
        serviced_trails = []
        if "trails" in area:
            trails = area["trails"]["trail"]
            if isinstance(trails, list):
                for trail in trails:
                    serviced_trails.append({
                        "name": trail["@name"],
                        "status": trail["@status"],
                        "difficulty": trail["@difficulty"],
                        "groomed": trail.get("@groomed", "")
                    })
        return serviced_trails

class BigSkyParkingSensor(CoordinatorEntity, SensorEntity):
   """Parking status sensor."""
   def __init__(self, coordinator):
       super().__init__(coordinator)
       self._attr_name = "Big Sky Parking"
       self._attr_unique_id = "big_sky_parking"
       self._attr_icon = "mdi:parking"

   @property
   def native_value(self):
       """Return number of open lots."""
       lots = self.coordinator.data["report"]["facilities"]["parking"]["lot"]
       return len([lot for lot in lots if lot["@status"] == "open"]) if isinstance(lots, list) else 0

   @property
   def extra_state_attributes(self):
       """Return lot details."""
       lots = self.coordinator.data["report"]["facilities"]["parking"]["lot"]
       return {lot["@name"]: {
           "status": lot["@status"],
           "percent_full": lot["@percentFull"],
           "open_time": lot["@openTime"],
           "closed_time": lot["@closedTime"],
           "alert": lot["@alert"]
       } for lot in lots} if isinstance(lots, list) else {}

class BigSkyShuttleSensor(CoordinatorEntity, SensorEntity):
   """Shuttle status sensor."""
   def __init__(self, coordinator):
       super().__init__(coordinator)
       self._attr_name = "Big Sky Shuttle"
       self._attr_unique_id = "big_sky_shuttle"
       self._attr_icon = "mdi:bus"

   @property
   def native_value(self):
       """Return shuttle status."""
       return self.coordinator.data["report"]["facilities"]["shuttles"]["line"]["@status"]

   @property
   def extra_state_attributes(self):
       """Return shuttle details."""
       shuttle = self.coordinator.data["report"]["facilities"]["shuttles"]["line"]
       return {
           "number_running": shuttle["@numberRunning"],
           "open_time": shuttle["@openTime"],
           "closed_time": shuttle["@closedTime"],
           "comment": shuttle["@comment"],
           "alert": shuttle["@alert"]
       }

class BigSkyCurrentWeatherSensor(CoordinatorEntity, SensorEntity):
   """Current weather sensor."""
   def __init__(self, coordinator):
       super().__init__(coordinator)
       self._attr_name = "Big Sky Current Weather"
       self._attr_unique_id = "big_sky_current_weather"
       self._attr_icon = "mdi:weather-partly-cloudy"
       self._attr_device_class = SensorDeviceClass.TEMPERATURE
       self._attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT

   @property
   def native_value(self):
       """Return current temperature."""
       try:
           return float(self.coordinator.data["report"]["forecast"]["day"][0]["@high"])
       except (KeyError, IndexError, ValueError):
           return None

   @property
   def extra_state_attributes(self):
       """Return weather details."""
       try:
           current = self.coordinator.data["report"]["forecast"]["day"][0]
           return {
               "condition": current["@weather"],
               "high": current["@high"],
               "low": current["@low"],
               "details": current.get("#text", "")
           }
       except (KeyError, IndexError):
           return {}