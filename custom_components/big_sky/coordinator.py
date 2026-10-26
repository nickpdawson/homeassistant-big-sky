"""Data update coordinator for Big Sky Resort."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_FEED_URL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_FEED_URL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)
from .feed import FeedError, ResortData, fetch_feed

_LOGGER = logging.getLogger(__package__)

type BigSkyConfigEntry = ConfigEntry[BigSkyCoordinator]


def entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Return the entry settings; options saved later override setup data."""
    return {**entry.data, **entry.options}


class BigSkyCoordinator(DataUpdateCoordinator[ResortData]):
    """Polls the mountain report feed."""

    config_entry: BigSkyConfigEntry

    def __init__(self, hass: HomeAssistant, entry: BigSkyConfigEntry) -> None:
        config = entry_config(entry)
        minutes = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        # Entries made before 1.1 could be set to 1 minute.
        minutes = max(MIN_UPDATE_INTERVAL, min(MAX_UPDATE_INTERVAL, int(minutes)))
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
        )
        self.feed_url: str = config.get(CONF_FEED_URL, DEFAULT_FEED_URL)
        self._session = async_get_clientsession(hass)

    async def _async_update_data(self) -> ResortData:
        try:
            return await fetch_feed(self._session, self.feed_url)
        except FeedError as err:
            raise UpdateFailed(str(err)) from err
