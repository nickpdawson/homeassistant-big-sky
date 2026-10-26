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
)
from .coordinator import BigSkyConfigEntry, BigSkyCoordinator, entry_config
from .migration import async_migrate_unique_ids

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.WEATHER]


async def async_setup_entry(hass: HomeAssistant, entry: BigSkyConfigEntry) -> bool:
    """Set up Big Sky Resort from a config entry."""
    coordinator = BigSkyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async_migrate_unique_ids(hass, entry, coordinator.data)
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
