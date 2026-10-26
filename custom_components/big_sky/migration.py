"""Move pre-1.1 unique_ids to entry-scoped ids."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .feed import ResortData, slugify_name

_LOGGER = logging.getLogger(__package__)

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


@callback
def async_migrate_unique_ids(
    hass: HomeAssistant, entry: ConfigEntry, data: ResortData
) -> None:
    """Move legacy unique_ids to entry-scoped ids based on feed ids.

    Lift and trail ids used to be the slugged name. The feed's own id is
    steadier, so map each old name slug to the new key. Only items in
    `data` can be mapped, so this runs again when a refresh brings in
    lifts or trails that were missing at setup.
    """
    lift_keys = {slugify_name(lift.name): key for key, lift in data.lifts.items()}
    trail_keys = {slugify_name(trail.name): key for key, trail in data.trails.items()}
    registry = er.async_get(hass)
    prefix = entry.entry_id

    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
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
            continue
        if registry.async_get_entity_id(entity.domain, DOMAIN, new):
            _LOGGER.warning(
                "Not migrating %s: unique_id %s is already in use", entity.entity_id, new
            )
            continue
        _LOGGER.debug("Migrating %s unique_id %s -> %s", entity.entity_id, old, new)
        registry.async_update_entity(entity.entity_id, new_unique_id=new)
