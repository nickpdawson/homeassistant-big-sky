"""Diagnostics for Big Sky Resort."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import BigSkyConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BigSkyConfigEntry
) -> dict[str, Any]:
    """Return entry settings and the last parsed feed.

    The feed is public resort data and the entry holds no secrets, so
    nothing is redacted.
    """
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": {
            "version": entry.version,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": {
            "feed_url": coordinator.feed_url,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception)
            if coordinator.last_exception
            else None,
        },
        "counts": {
            "lifts": len(data.lifts) if data else 0,
            "trails": len(data.trails) if data else 0,
            "parks": len(data.parks) if data else 0,
            "parking_lots": len(data.parking) if data else 0,
            "forecast_days": len(data.forecast) if data else 0,
        },
        "data": asdict(data) if data else None,
    }
