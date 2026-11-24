"""Dehumidifier measurements."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NomaIQConfigEntry
from .entity import NomaIQPropertyEntity
from .device import is_dehumidifier


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NomaIQConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities = [
        NomaIQIndoorHumiditySensor(coordinator, device, "indoor_humidity", "Indoor humidity")
        for device in coordinator.data
        if is_dehumidifier(device) and "indoor_humidity" in device.properties_full
    ]
    async_add_entities(entities)


class NomaIQIndoorHumiditySensor(NomaIQPropertyEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> int | None:
        return self._value()
