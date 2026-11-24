"""Dehumidifier alerts."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import NomaIQConfigEntry
from .entity import NomaIQPropertyEntity
from .device import is_dehumidifier


ALERTS = {
    "water_bucket_full": ("Tank full", BinarySensorDeviceClass.MOISTURE),
    "filter_clean_alarm": ("Filter alert", BinarySensorDeviceClass.PROBLEM),
    "humidity_sensor_fault": ("Sensor fault", BinarySensorDeviceClass.PROBLEM),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NomaIQConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities = [
        NomaIQAlertSensor(coordinator, device, property_name, label, device_class)
        for device in coordinator.data
        if is_dehumidifier(device)
        for property_name, (label, device_class) in ALERTS.items()
        if property_name in device.properties_full
    ]
    async_add_entities(entities)


class NomaIQAlertSensor(NomaIQPropertyEntity, BinarySensorEntity):
    def __init__(self, coordinator, device, property_name, label, device_class) -> None:
        super().__init__(coordinator, device, property_name, label)
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        value = self._value()
        return None if value is None else bool(value)
