"""Sensors for Big Sky Resort."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength, UnitOfPrecipitationDepth, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import BigSkyConfigEntry, BigSkyCoordinator
from .entity import BigSkyEntity
from .feed import Lift, ResortData, is_open

DIFFICULTIES = (
    "beginner",
    "intermediate",
    "advanced_intermediate",
    "advanced",
    "expert",
    "high_exposure",
)


@dataclass(frozen=True, kw_only=True)
class BigSkySensorDescription(SensorEntityDescription):
    value_fn: Callable[[ResortData], float | int | str | None]
    attrs_fn: Callable[[ResortData], dict[str, Any]] | None = None


def _snow(key: str, value_fn: Callable[[ResortData], float | None]) -> BigSkySensorDescription:
    return BigSkySensorDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPrecipitationDepth.INCHES,
        value_fn=value_fn,
    )


def _find_tram(data: ResortData) -> Lift | None:
    return next(
        (lift for lift in data.lifts.values() if "tram" in (lift.type or "").lower()),
        None,
    )


def _tram_attrs(data: ResortData) -> dict[str, Any]:
    if (tram := _find_tram(data)) is None:
        return {}
    return {
        "name": tram.name,
        "capacity": tram.capacity,
        "type": tram.type,
        "status_detail": tram.status_detail,
        "open_time": tram.open_time,
        "close_time": tram.close_time,
        "skier_wait_time": tram.skier_wait_time,
        "scenic_wait_time": tram.scenic_wait_time,
        "serviced_trails": [
            {
                "name": trail.name,
                "status": trail.status,
                "difficulty": trail.difficulty,
                "groomed": trail.groomed,
            }
            for trail in data.trails.values()
            if tram.area and trail.area == tram.area
        ],
    }


def _trails_by_difficulty(data: ResortData) -> dict[str, Any]:
    counts = {name: {"open": 0, "total": 0} for name in DIFFICULTIES}
    for trail in data.trails.values():
        name = (trail.difficulty or "").strip().lower().replace(" ", "_")
        if name in counts:
            counts[name]["total"] += 1
            if is_open(trail.status):
                counts[name]["open"] += 1
    return counts


def _parks_attrs(data: ResortData) -> dict[str, Any]:
    return {
        park.name: {
            "status": park.status,
            "difficulty": park.difficulty,
            "groomed": park.groomed,
            "area": park.area,
        }
        for park in data.parks
    }


def _parking_attrs(data: ResortData) -> dict[str, Any]:
    return {
        lot.name: {
            "status": lot.status,
            "percent_full": lot.percent_full,
            "open_time": lot.open_time,
            "closed_time": lot.closed_time,
            "alert": lot.alert,
        }
        for lot in data.parking
    }


def _forecast_high_attrs(data: ResortData) -> dict[str, Any]:
    if not data.forecast:
        return {}
    today = data.forecast[0]
    return {
        "period": today.name,
        "condition": today.weather,
        "high": today.high,
        "low": today.low,
        "details": today.text,
    }


SENSORS: tuple[BigSkySensorDescription, ...] = (
    BigSkySensorDescription(
        key="snow_depth",
        translation_key="snow_depth",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.INCHES,
        value_fn=lambda data: data.snow_base,
    ),
    _snow("snowfall_24h", lambda data: data.snow_24h),
    _snow("snowfall_48h", lambda data: data.snow_48h),
    _snow("snowfall_72h", lambda data: data.snow_72h),
    _snow("snowfall_7d", lambda data: data.snow_7d),
    BigSkySensorDescription(
        key="forecast_high",
        translation_key="forecast_high",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        value_fn=lambda data: data.forecast[0].high if data.forecast else None,
        attrs_fn=_forecast_high_attrs,
    ),
    BigSkySensorDescription(
        key="terrain_parks",
        translation_key="terrain_parks",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.parks_open,
        attrs_fn=_parks_attrs,
    ),
    BigSkySensorDescription(
        key="trails_open",
        translation_key="trails_open",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.trails_open,
        attrs_fn=_trails_by_difficulty,
    ),
    BigSkySensorDescription(
        key="lifts_open",
        translation_key="lifts_open",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.lifts_open,
    ),
    BigSkySensorDescription(
        key="tram",
        translation_key="tram",
        value_fn=lambda data: tram.status if (tram := _find_tram(data)) else None,
        attrs_fn=_tram_attrs,
    ),
    BigSkySensorDescription(
        key="parking",
        translation_key="parking",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sum(1 for lot in data.parking if is_open(lot.status)),
        attrs_fn=_parking_attrs,
    ),
    BigSkySensorDescription(
        key="shuttle",
        translation_key="shuttle",
        value_fn=lambda data: data.shuttle.get("status") if data.shuttle else None,
        attrs_fn=lambda data: dict(data.shuttle or {}),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BigSkyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Big Sky Resort sensors."""
    coordinator = entry.runtime_data
    async_add_entities(BigSkySensor(coordinator, description) for description in SENSORS)


class BigSkySensor(BigSkyEntity, SensorEntity):
    """A value read from the mountain report."""

    entity_description: BigSkySensorDescription

    def __init__(
        self, coordinator: BigSkyCoordinator, description: BigSkySensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
