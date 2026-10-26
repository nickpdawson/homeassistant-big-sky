"""The Big Sky Resort integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_CREATE_LIFT_ENTITIES,
    CONF_CREATE_RUN_ENTITIES,
    CONF_FEED_URL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_FEED_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .coordinator import BigSkyConfigEntry, BigSkyCoordinator, entry_config
from .feed import ResortData, slugify_name

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.WEATHER]

# unique_ids before 1.1 were global strings, not tied to the entry.
LEGACY_FIXED_IDS = {
    "big_sky_resort_open": "resort_status",
    "big_sky_snow_making": "snowmaking",
    "big_sky_snow_depth": "snow_depth",
    "big_sky_snowfall_24h": "snowfall_24h",
    "big_sky_current_weather": "forecast_high",
    "big_sky_terrain_parks": "terrain_parks",
    "big_sky_trails_by_difficulty": "trails_open",
    "big_sky_tram": "tram",
    "big_sky_parking": "parking",
    "big_sky_shuttle": "shuttle",
    "big_sky_weather": "weather",
}


async def async_setup_entry(hass: HomeAssistant, entry: BigSkyConfigEntry) -> bool:
    """Set up Big Sky Resort from a config entry."""
    coordinator = BigSkyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await _async_migrate_unique_ids(hass, entry, coordinator.data)
    _async_remove_disabled_entities(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: BigSkyConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: BigSkyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: BigSkyConfigEntry) -> bool:
    """Fill in defaults for version 1 entries."""
    if entry.version == 1:
        new_data = {**entry.data}
        new_data.setdefault(CONF_FEED_URL, DEFAULT_FEED_URL)
        new_data.setdefault(CONF_CREATE_RUN_ENTITIES, True)
        new_data.setdefault(CONF_CREATE_LIFT_ENTITIES, True)
        new_data.setdefault(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        hass.config_entries.async_update_entry(entry, data=new_data, version=2)
        _LOGGER.debug("Migrated config entry to version 2")
    return True


async def _async_migrate_unique_ids(
    hass: HomeAssistant, entry: BigSkyConfigEntry, data: ResortData
) -> None:
    """Move pre-1.1 unique_ids to entry-scoped ids based on feed ids.

    Lift and trail ids used to be the slugged name. The feed's own id is
    steadier, so map each old name slug to the new key.
    """
    lift_keys = {slugify_name(lift.name): key for key, lift in data.lifts.items()}
    trail_keys = {slugify_name(trail.name): key for key, trail in data.trails.items()}
    registry = er.async_get(hass)
    prefix = entry.entry_id

    @callback
    def _migrate(entity: er.RegistryEntry) -> dict[str, str] | None:
        old = entity.unique_id
        new: str | None = None
        if old in LEGACY_FIXED_IDS:
            new = f"{prefix}_{LEGACY_FIXED_IDS[old]}"
        elif old.startswith("big_sky_lift_") and (
            key := lift_keys.get(old.removeprefix("big_sky_lift_"))
        ):
            new = f"{prefix}_lift_{key}"
        elif old.startswith("big_sky_trail_") and (
            key := trail_keys.get(old.removeprefix("big_sky_trail_"))
        ):
            new = f"{prefix}_trail_{key}"
        if new is None:
            return None
        if registry.async_get_entity_id(entity.domain, DOMAIN, new):
            _LOGGER.warning(
                "Not migrating %s: unique_id %s is already in use", entity.entity_id, new
            )
            return None
        _LOGGER.debug("Migrating %s unique_id %s -> %s", entity.entity_id, old, new)
        return {"new_unique_id": new}

    await er.async_migrate_entries(hass, entry.entry_id, _migrate)


@callback
def _async_remove_disabled_entities(hass: HomeAssistant, entry: BigSkyConfigEntry) -> None:
    """Drop lift or trail entities the user turned off in options."""
    config = entry_config(entry)
    dropped = []
    if not config.get(CONF_CREATE_LIFT_ENTITIES, True):
        dropped.append(f"{entry.entry_id}_lift_")
    if not config.get(CONF_CREATE_RUN_ENTITIES, True):
        dropped.append(f"{entry.entry_id}_trail_")
    if not dropped:
        return
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.unique_id.startswith(tuple(dropped)):
            registry.async_remove(entity.entity_id)
