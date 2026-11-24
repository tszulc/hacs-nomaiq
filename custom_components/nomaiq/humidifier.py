"""Platform for dehumidifier integration."""

from __future__ import annotations

from typing import Any

import ayla_iot_unofficial
import ayla_iot_unofficial.device

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NomaIQConfigEntry
from .const import DOMAIN
from .coordinator import NomaIQDataUpdateCoordinator
from .device import MAX_HUMIDITY, MIN_HUMIDITY, is_dehumidifier, stepped_humidity

# App label -> raw value stored in the device's "mode" property
MODE_TO_RAW: dict[str, str] = {
    "manual": "Normal",
    "auto dry": "Auto",
    "continuous": "Persistent",
}
RAW_TO_MODE: dict[str, str] = {raw: label for label, raw in MODE_TO_RAW.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NomaIQConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Noma IQ dehumidifier platform."""
    coordinator: NomaIQDataUpdateCoordinator = entry.runtime_data

    for device in coordinator.data:
        if is_dehumidifier(device):
            async_add_entities(
                [NomaIQDehumidifierEntity(coordinator, device)],
                update_before_add=False,
            )


class NomaIQDehumidifierEntity(
    CoordinatorEntity[NomaIQDataUpdateCoordinator], HumidifierEntity
):
    """Representation of a NomaIQ dehumidifier."""

    _attr_device_class = HumidifierDeviceClass.DEHUMIDIFIER
    _attr_supported_features = HumidifierEntityFeature.MODES
    _attr_available_modes = list(MODE_TO_RAW)
    _attr_min_humidity = MIN_HUMIDITY
    _attr_max_humidity = MAX_HUMIDITY
    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self,
        coordinator: NomaIQDataUpdateCoordinator,
        device: ayla_iot_unofficial.device.Device,
    ) -> None:
        """Initialize a NomaIQ dehumidifier."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"nomaiq_dehumidifier_{device.serial_number}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.serial_number)},
            name=device.name,
            model=device.device_model_number,
        )

    def _get_current_device(self) -> ayla_iot_unofficial.device.Device | None:
        """Get the current device from coordinator data."""
        return self.coordinator.device(self._device.serial_number)

    def _get_value(self, property_name: str) -> Any:
        """Read a property from the latest coordinator data."""
        device = self._get_current_device()
        return device.get_property_value(property_name) if device else None

    @property
    def is_on(self) -> bool | None:
        """Return true if the dehumidifier is on."""
        power = self._get_value("power")
        return None if power is None else bool(power)

    @property
    def current_humidity(self) -> int | None:
        """Return the measured indoor humidity."""
        return self._get_value("indoor_humidity")

    @property
    def target_humidity(self) -> int | None:
        """Return the target humidity."""
        return self._get_value("humidity")

    @property
    def mode(self) -> str | None:
        """Return the current mode as an app label."""
        raw = self._get_value("mode")
        return RAW_TO_MODE.get(raw)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the dehumidifier on."""
        await self._get_current_device().async_set_property_value("power", 1)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the dehumidifier off."""
        await self._get_current_device().async_set_property_value("power", 0)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_set_humidity(self, humidity: int) -> None:
        """Set the target humidity, moving one 5% step in the requested direction.

        The device only accepts multiples of 5, while the Home Assistant +/-
        buttons change the target by 1%. Rounding up when increasing and down
        when decreasing means each press moves the target to the next step.
        """
        value = stepped_humidity(humidity, self.target_humidity)
        await self._get_current_device().async_set_property_value("humidity", value)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()

    async def async_set_mode(self, mode: str) -> None:
        """Set the operating mode."""
        raw = MODE_TO_RAW.get(mode)
        if raw is None:
            raise ValueError(f"Unsupported mode: {mode}")
        await self._get_current_device().async_set_property_value("mode", raw)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
