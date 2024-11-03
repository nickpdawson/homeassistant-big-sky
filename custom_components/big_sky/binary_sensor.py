"""Binary sensors for Big Sky Resort."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_CREATE_LIFT_ENTITIES,
    CONF_CREATE_RUN_ENTITIES,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Big Sky binary sensors based on config entry options."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    entities = []

    # Resort status and snow making sensors
    entities.extend([
        BigSkyResortStatusBinarySensor(coordinator),
        BigSkySnowMakingBinarySensor(coordinator)
    ])

    # Conditionally add lift and trail sensors based on config
    if config_entry.data.get(CONF_CREATE_LIFT_ENTITIES, True):
        areas = coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if "lifts" in area:
                    area_lifts = area["lifts"]["lift"]
                    if isinstance(area_lifts, list):
                        for lift in area_lifts:
                            entities.append(
                                BigSkyLiftBinarySensor(
                                    coordinator,
                                    lift["@name"],
                                    area["@name"],
                                    lift["@type"]
                                )
                            )
                    else:
                        entities.append(
                            BigSkyLiftBinarySensor(
                                coordinator,
                                area_lifts["@name"],
                                area["@name"],
                                area_lifts["@type"]
                            )
                        )

    if config_entry.data.get(CONF_CREATE_RUN_ENTITIES, True):
        areas = coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if "trails" in area:
                    trails = area["trails"]["trail"]
                    if isinstance(trails, list):
                        for trail in trails:
                            entities.append(
                                BigSkyTrailBinarySensor(
                                    coordinator,
                                    trail["@name"],
                                    area["@name"],
                                    trail["@difficulty"]
                                )
                            )
                    else:
                        entities.append(
                            BigSkyTrailBinarySensor(
                                coordinator,
                                trails["@name"],
                                area["@name"],
                                trails["@difficulty"]
                            )
                        )

    async_add_entities(entities)


class BigSkyResortStatusBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for resort open/closed status."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Big Sky Resort Status"
        self._attr_unique_id = "big_sky_resort_open"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        """Return true if the resort is open."""
        return self.coordinator.data["report"]["operations"]["@resortStatus"].lower() == "open"

    @property
    def extra_state_attributes(self):
        """Return additional resort status information."""
        operations = self.coordinator.data["report"]["operations"]
        return {
            "open_time": operations["@openTime"],
            "close_time": operations["@closeTime"]
        }


class BigSkyLiftBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for lift status."""

    def __init__(self, coordinator, lift_name, area_name, lift_type):
        """Initialize lift binary sensor."""
        super().__init__(coordinator)
        self._lift_name = lift_name
        self._area_name = area_name
        self._lift_type = lift_type
        self._attr_name = f"Lift {lift_name}"
        self._attr_unique_id = f"big_sky_lift_{lift_name.lower().replace(' ', '_')}"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
       # Set different icons based on lift type
        if "Tram" in lift_type:
            self._attr_icon = "mdi:ski-lift"
        elif "Carpet" in lift_type:
            self._attr_icon = "mdi:conveyor-belt"
        elif "Poma" in lift_type or "Rope" in lift_type:
            self._attr_icon = "mdi:ski"
        else:
            self._attr_icon = "mdi:chair-rolling"

    @property
    def is_on(self) -> bool:
        """Return true if the lift is open."""
        areas = self.coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if area["@name"] == self._area_name and "lifts" in area:
                    lifts = area["lifts"]["lift"]
                    if isinstance(lifts, list):
                        for lift in lifts:
                            if lift["@name"] == self._lift_name:
                                return lift["@status"].lower() == "open"
                    elif lifts["@name"] == self._lift_name:
                        return lifts["@status"].lower() == "open"
        return False

    @property
    def extra_state_attributes(self):
        """Return additional lift status information."""
        areas = self.coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if area["@name"] == self._area_name and "lifts" in area:
                    lifts = area["lifts"]["lift"]
                    if isinstance(lifts, list):
                        for lift in lifts:
                            if lift["@name"] == self._lift_name:
                                return {
                                    "type": lift["@type"],
                                    "capacity": lift.get("@capacity", ""),
                                    "area": self._area_name,
                                    "open_time": lift.get("@openTime", ""),
                                    "close_time": lift.get("@closeTime", ""),
                                    "status_detail": lift.get("@statusDetail", "")
                                }
                    elif lifts["@name"] == self._lift_name:
                        return {
                            "type": lifts["@type"],
                            "capacity": lifts.get("@capacity", ""),
                            "area": self._area_name,
                            "open_time": lifts.get("@openTime", ""),
                            "close_time": lifts.get("@closeTime", ""),
                            "status_detail": lifts.get("@statusDetail", "")
                        }
        return {}

class BigSkyTrailBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for trail status."""

    def __init__(self, coordinator, trail_name, area_name, difficulty):
        """Initialize trail binary sensor."""
        super().__init__(coordinator)
        self._trail_name = trail_name
        self._area_name = area_name
        self._difficulty = difficulty
        self._attr_name = f"Trail {trail_name}"
        self._attr_unique_id = f"big_sky_trail_{trail_name.lower().replace(' ', '_')}"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        
        # Set different icons based on difficulty
        if "expert" in difficulty.lower():
            self._attr_icon = "mdi:terrain"
        elif "advanced" in difficulty.lower():
            self._attr_icon = "mdi:slope-downhill"
        elif "intermediate" in difficulty.lower():
            self._attr_icon = "mdi:ski"
        else:
            self._attr_icon = "mdi:ski-water"

    @property
    def is_on(self) -> bool:
        """Return true if the trail is open."""
        areas = self.coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if area["@name"] == self._area_name and "trails" in area:
                    trails = area["trails"]["trail"]
                    if isinstance(trails, list):
                        for trail in trails:
                            if trail["@name"] == self._trail_name:
                                return trail["@status"].lower() == "open"
                    elif trails["@name"] == self._trail_name:
                        return trails["@status"].lower() == "open"
        return False

    @property
    def extra_state_attributes(self):
        """Return additional trail status information."""
        areas = self.coordinator.data["report"]["facilities"]["areas"]["area"]
        if isinstance(areas, list):
            for area in areas:
                if area["@name"] == self._area_name and "trails" in area:
                    trails = area["trails"]["trail"]
                    if isinstance(trails, list):
                        for trail in trails:
                            if trail["@name"] == self._trail_name:
                                return {
                                    "difficulty": trail["@difficulty"],
                                    "area": self._area_name,
                                    "groomed": trail.get("@groomed", "no"),
                                    "uphill": trail.get("@uphill", "no")
                                }
                    elif trails["@name"] == self._trail_name:
                        return {
                            "difficulty": trails["@difficulty"],
                            "area": self._area_name,
                            "groomed": trails.get("@groomed", "no"),
                            "uphill": trails.get("@uphill", "no")
                        }
        return {}

class BigSkySnowMakingBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for snow making status."""

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "Big Sky Snow Making"
        self._attr_unique_id = "big_sky_snow_making"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:snowflake"

    @property
    def is_on(self) -> bool:
        """Return true if snow making is active."""
        return int(self.coordinator.data["report"]["currentConditions"]["resortwide"]["@numTrailsSnowMaking"]) > 0

    @property
    def extra_state_attributes(self):
        """Return number of trails with snowmaking."""
        return {
            "trails_with_snowmaking": self.coordinator.data["report"]["currentConditions"]["resortwide"]["@numTrailsSnowMaking"]
        }