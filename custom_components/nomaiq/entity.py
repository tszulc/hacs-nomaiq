"""Shared access to the latest Ayla device object."""

from __future__ import annotations

from typing import Any

import ayla_iot_unofficial.device

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NomaIQDataUpdateCoordinator


class NomaIQPropertyEntity(CoordinatorEntity[NomaIQDataUpdateCoordinator]):
    """A device property that survives replacement objects during polling."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NomaIQDataUpdateCoordinator,
        device: ayla_iot_unofficial.device.Device,
        property_name: str,
        label: str,
    ) -> None:
        super().__init__(coordinator)
        self._serial = device.serial_number
        self._property_name = property_name
        self._attr_name = label
        self._attr_unique_id = f"nomaiq_{property_name}_{self._serial}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            name=device.name,
            model=device.device_model_number,
        )

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.device(self._serial) is not None

    def _value(self) -> Any:
        device = self.coordinator.device(self._serial)
        return device.get_property_value(self._property_name) if device else None
