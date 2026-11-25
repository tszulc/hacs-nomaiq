"""Shared access to the latest Ayla device object."""

from __future__ import annotations

import re
from typing import Any

import ayla_iot_unofficial.device

from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo, format_mac
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NomaIQDataUpdateCoordinator


class NomaIQEntity(CoordinatorEntity[NomaIQDataUpdateCoordinator]):
    """An entity whose availability follows the device's cloud connection."""

    def __init__(
        self,
        coordinator: NomaIQDataUpdateCoordinator,
        device: ayla_iot_unofficial.device.Device,
    ) -> None:
        super().__init__(coordinator)
        self._serial = device.serial_number
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            serial_number=self._serial,
            name=device.name,
            model=device.device_model_number,
        )
        # Ayla 1.5.0 only exposes the MAC through private Device attributes.
        mac = coordinator.mac_addresses.get(self._serial)
        if isinstance(mac, str):
            mac = format_mac(mac)
            if re.fullmatch(r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}", mac) and mac not in (
                "00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"
            ):
                self._attr_device_info["connections"] = {(CONNECTION_NETWORK_MAC, mac)}
        version = device.properties_full.get("version", {}).get("value")
        if isinstance(version, str) and version:
            self._attr_device_info["sw_version"] = version

    @property
    def available(self) -> bool:
        return super().available and self.coordinator.is_device_available(self._serial)


class NomaIQPropertyEntity(NomaIQEntity):
    """A device property that survives replacement objects during polling."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: NomaIQDataUpdateCoordinator,
        device: ayla_iot_unofficial.device.Device,
        property_name: str,
        label: str | None,
    ) -> None:
        super().__init__(coordinator, device)
        self._property_name = property_name
        self._attr_name = label
        self._attr_unique_id = f"nomaiq_{property_name}_{self._serial}"

    def _value(self) -> Any:
        device = self.coordinator.device(self._serial)
        if device is None or self._property_name not in device.properties_full:
            return None
        return device.get_property_value(self._property_name)

    async def _async_set_value(self, value: int) -> None:
        device = self.coordinator.device(self._serial)
        if device is None or device.properties_full.get(self._property_name, {}).get(
            "read_only", True
        ):
            raise ServiceValidationError(f"Device property {self._property_name} is not writable")
        await device.async_set_property_value(self._property_name, value)
        await self.coordinator.async_request_refresh()
