from __future__ import annotations
from datetime import timedelta
import logging
import xmltodict
import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_FEED_URL,
    CONF_FEED_URL,
    CONF_CREATE_RUN_ENTITIES,
    CONF_CREATE_LIFT_ENTITIES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
)
LOGGER = logging.getLogger(__name__)
LOGGER.debug("Initializing Big Sky Resort component.")
DEFAULT_PLATFORMS = [Platform.SENSOR, Platform.WEATHER]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Big Sky Resort component."""
    hass.data[DOMAIN] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Big Sky Resort from a config entry."""
    LOGGER.debug("Setting up Big Sky Resort entry with data: %s", entry.data)
    platforms = DEFAULT_PLATFORMS.copy()
    if entry.data.get(CONF_CREATE_RUN_ENTITIES, True) or entry.data.get(CONF_CREATE_LIFT_ENTITIES, True):
        platforms.append(Platform.BINARY_SENSOR)


    async def async_update_data():
        """Fetch data from API."""
        try:
            feed_url = entry.data.get(CONF_FEED_URL, DEFAULT_FEED_URL)
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(feed_url) as response:
                        if response.status != 200:
                            raise UpdateFailed(f"Error fetching data: {response.status}")
                        xml_data = await response.text()
                        return xmltodict.parse(xml_data)
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        LOGGER,
        name="big_sky_resort",
        update_method=async_update_data,
        update_interval=timedelta(minutes=entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "config": entry.data,
    }

    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    LOGGER.debug("Migrating from version %s", config_entry.version)
    if config_entry.version == 1:
        new_data = {**config_entry.data}
        new_data.setdefault(CONF_FEED_URL, DEFAULT_FEED_URL)
        new_data.setdefault(CONF_CREATE_RUN_ENTITIES, True)
        new_data.setdefault(CONF_CREATE_LIFT_ENTITIES, True)
        new_data.setdefault(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new_data)
    LOGGER.info("Migration to version %s successful", config_entry.version)
    return True