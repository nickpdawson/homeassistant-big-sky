"""Base entity for Big Sky Resort."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME
from .coordinator import BigSkyCoordinator


class BigSkyEntity(CoordinatorEntity[BigSkyCoordinator]):
    """Common device and naming for every entity in the entry."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: BigSkyCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=NAME,
            manufacturer=NAME,
            model="Mountain report feed",
            entry_type=DeviceEntryType.SERVICE,
        )
