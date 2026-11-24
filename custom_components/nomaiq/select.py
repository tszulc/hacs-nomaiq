"""Select controls for supported Noma IQ devices."""

from __future__ import annotations

import ayla_iot_unofficial
import ayla_iot_unofficial.device

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import NomaIQConfigEntry
from .const import DOMAIN
from .coordinator import NomaIQDataUpdateCoordinator
from .device import is_dehumidifier, is_humidifier
from .entity import NomaIQPropertyEntity

# App label -> raw value stored in the device's "fan_speed" property
FAN_TO_RAW: dict[str, str] = {
    "auto": "Smart",
    "slow": "Low",
    "fast": "High",
}
RAW_TO_FAN: dict[str, str] = {raw: label for label, raw in FAN_TO_RAW.items()}

HUMIDIFIER_SELECTS = (
    ("night_mode", "boolean", "Unit lights", {"Dim": 1, "Bright": 0}),
    ("vapour_setting", "integer", "Mist output", {"Low": 1, "Medium": 3, "High": 7}),
    ("mist_setting", "integer", "Mist temperature", {"Cool": 1, "Warm": 2}),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NomaIQConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up select controls based on device model."""
    coordinator: NomaIQDataUpdateCoordinator = entry.runtime_data

    for device in coordinator.data:
        if is_humidifier(device):
            for name, base_type, label, values in HUMIDIFIER_SELECTS:
                prop = device.properties_full.get(name, {})
                if prop.get("base_type") == base_type and not prop.get("read_only", True):
                    async_add_entities([
                        NomaIQHumidifierSelectEntity(coordinator, device, name, label, values)
                    ])
        elif is_dehumidifier(device):
            async_add_entities(
                [NomaIQDehumidifierFanSpeedEntity(coordinator, device)],
                update_before_add=False,
            )


class NomaIQHumidifierSelectEntity(NomaIQPropertyEntity, SelectEntity):
    """Select an app option backed by an Ayla property value."""

    def __init__(
        self,
        coordinator: NomaIQDataUpdateCoordinator,
        device: ayla_iot_unofficial.device.Device,
        property_name: str,
        label: str,
        values: dict[str, int],
    ) -> None:
        super().__init__(coordinator, device, property_name, label)
        self._values = values
        self._attr_options = list(values)

    @property
    def current_option(self) -> str | None:
        value = self._value()
        return next((option for option, raw in self._values.items() if raw == value), None)

    async def async_select_option(self, option: str) -> None:
        if option not in self._values:
            raise ServiceValidationError(f"Unsupported {self.name} option: {option}")
        await self._async_set_value(self._values[option])


class NomaIQDehumidifierFanSpeedEntity(
    CoordinatorEntity[NomaIQDataUpdateCoordinator], SelectEntity
):
    """Fan speed control for a NomaIQ dehumidifier."""

    _attr_has_entity_name = True
    _attr_name = "Fan speed"
    _attr_options = list(FAN_TO_RAW)

    def __init__(
        self,
        coordinator: NomaIQDataUpdateCoordinator,
        device: ayla_iot_unofficial.device.Device,
    ) -> None:
        """Initialize the fan speed select."""
        super().__init__(coordinator)
        self._device = device
        self._attr_unique_id = f"nomaiq_dehumidifier_fan_{device.serial_number}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.serial_number)},
            name=device.name,
            model=device.device_model_number,
        )

    def _get_current_device(self) -> ayla_iot_unofficial.device.Device | None:
        """Get the current device from coordinator data."""
        return self.coordinator.device(self._device.serial_number)

    @property
    def current_option(self) -> str | None:
        """Return the current fan speed as an app label."""
        device = self._get_current_device()
        raw = device.get_property_value("fan_speed") if device else None
        return RAW_TO_FAN.get(raw)

    async def async_select_option(self, option: str) -> None:
        """Set the fan speed."""
        raw = FAN_TO_RAW.get(option)
        if raw is None:
            raise ValueError(f"Unsupported fan speed: {option}")
        await self._get_current_device().async_set_property_value("fan_speed", raw)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
