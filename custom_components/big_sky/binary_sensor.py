"""Binary sensors for Big Sky Resort."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_CREATE_LIFT_ENTITIES, CONF_CREATE_RUN_ENTITIES
from .coordinator import BigSkyConfigEntry, BigSkyCoordinator, entry_config
from .entity import BigSkyEntity
from .feed import Lift, Trail, is_open
from .migration import async_migrate_unique_ids


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BigSkyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Big Sky binary sensors."""
    coordinator = entry.runtime_data
    config = entry_config(entry)
    create_lifts = config.get(CONF_CREATE_LIFT_ENTITIES, True)
    create_trails = config.get(CONF_CREATE_RUN_ENTITIES, True)

    async_add_entities(
        [BigSkyResortStatusBinarySensor(coordinator), BigSkySnowmakingBinarySensor(coordinator)]
    )

    added_lifts: set[str] = set()
    added_trails: set[str] = set()

    # The feed switches between summer and winter content, so lifts and
    # trails can appear long after setup.
    @callback
    def _add_new_items() -> None:
        data = coordinator.data
        new_lifts = (
            [lift for key, lift in data.lifts.items() if key not in added_lifts]
            if create_lifts
            else []
        )
        new_trails = (
            [trail for key, trail in data.trails.items() if key not in added_trails]
            if create_trails
            else []
        )
        if not new_lifts and not new_trails:
            return
        # A legacy registry entry for a returning item must get its new
        # unique_id before the entity is added, or it gets a duplicate.
        async_migrate_unique_ids(hass, entry, data)
        added_lifts.update(lift.key for lift in new_lifts)
        added_trails.update(trail.key for trail in new_trails)
        entities: list[BinarySensorEntity] = [
            BigSkyLiftBinarySensor(coordinator, lift) for lift in new_lifts
        ]
        entities.extend(BigSkyTrailBinarySensor(coordinator, trail) for trail in new_trails)
        async_add_entities(entities)

    _add_new_items()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_items))


class BigSkyResortStatusBinarySensor(BigSkyEntity, BinarySensorEntity):
    """On when the resort reports Open."""

    _attr_translation_key = "resort_status"
    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, coordinator: BigSkyCoordinator) -> None:
        super().__init__(coordinator, "resort_status")

    @property
    def is_on(self) -> bool:
        return is_open(self.coordinator.data.resort_status)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {"open_time": data.open_time, "close_time": data.close_time}


class BigSkySnowmakingBinarySensor(BigSkyEntity, BinarySensorEntity):
    """On when any trail has snowmaking."""

    _attr_translation_key = "snowmaking"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: BigSkyCoordinator) -> None:
        super().__init__(coordinator, "snowmaking")

    @property
    def is_on(self) -> bool | None:
        count = self.coordinator.data.trails_snowmaking
        return None if count is None else count > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"trails_with_snowmaking": self.coordinator.data.trails_snowmaking}


def _lift_icon(lift_type: str | None) -> str:
    lift_type = (lift_type or "").lower()
    if "tram" in lift_type or "gondola" in lift_type:
        return "mdi:gondola"
    if "carpet" in lift_type:
        return "mdi:conveyor-belt"
    if "poma" in lift_type or "rope" in lift_type:
        return "mdi:ski"
    return "mdi:ski-lift"


def _trail_icon(difficulty: str | None) -> str:
    difficulty = (difficulty or "").lower()
    if "expert" in difficulty or "exposure" in difficulty:
        return "mdi:terrain"
    if difficulty == "advanced":
        return "mdi:slope-downhill"
    if "intermediate" in difficulty:
        return "mdi:ski"
    return "mdi:ski-water"


class BigSkyLiftBinarySensor(BigSkyEntity, BinarySensorEntity):
    """On when the lift is running."""

    _attr_translation_key = "lift"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator: BigSkyCoordinator, lift: Lift) -> None:
        super().__init__(coordinator, f"lift_{lift.key}")
        self._key = lift.key
        self._attr_translation_placeholders = {"name": lift.name}
        self._attr_icon = _lift_icon(lift.type)

    @property
    def _lift(self) -> Lift | None:
        return self.coordinator.data.lifts.get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self._lift is not None

    @property
    def is_on(self) -> bool | None:
        return is_open(lift.status) if (lift := self._lift) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if (lift := self._lift) is None:
            return {}
        return {
            "type": lift.type,
            "capacity": lift.capacity,
            "area": lift.area,
            "status": lift.status,
            "open_time": lift.open_time,
            "close_time": lift.close_time,
            "status_detail": lift.status_detail,
        }


class BigSkyTrailBinarySensor(BigSkyEntity, BinarySensorEntity):
    """On when the trail is open."""

    _attr_translation_key = "trail"
    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(self, coordinator: BigSkyCoordinator, trail: Trail) -> None:
        super().__init__(coordinator, f"trail_{trail.key}")
        self._key = trail.key
        self._attr_translation_placeholders = {"name": trail.name}
        self._attr_icon = _trail_icon(trail.difficulty)

    @property
    def _trail(self) -> Trail | None:
        return self.coordinator.data.trails.get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self._trail is not None

    @property
    def is_on(self) -> bool | None:
        return is_open(trail.status) if (trail := self._trail) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if (trail := self._trail) is None:
            return {}
        return {
            "difficulty": trail.difficulty,
            "area": trail.area,
            "status": trail.status,
            "groomed": trail.groomed,
        }
