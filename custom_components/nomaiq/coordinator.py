"""Coordinator for nomaiq."""

from datetime import timedelta
from typing import Any, Set

import ayla_iot_unofficial

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, NORMAL_UPDATE_INTERVAL, TRANSITION_UPDATE_INTERVAL


def properties_snapshot(device: ayla_iot_unofficial.device.Device) -> dict[str, Any]:
    """Return a JSON-safe copy of a device's property values and metadata."""
    return {
        name: {
            "value": prop.get("value"),
            "base_type": prop.get("base_type"),
            "read_only": prop.get("read_only"),
        }
        for name, prop in device.properties_full.items()
    }


class NomaIQDataUpdateCoordinator(
    DataUpdateCoordinator[list[ayla_iot_unofficial.device.Device]]
):
    """Devices state update handler."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger,
        update_interval: timedelta,
        api: ayla_iot_unofficial.AylaApi,
    ) -> None:
        """Initialize global data updater."""
        self._api = api
        self._devices_in_transition: Set[str] = set()  # Track devices opening/closing
        self._last_full_update = 0  # Track when we last did a full update
        self.snapshots: list[dict[str, Any]] = []  # Captured states, kept until restart
        self.connection_info: dict[str, dict[str, Any]] = {}
        self.mac_addresses: dict[str, str | None] = {}

        super().__init__(
            hass,
            logger,
            name=DOMAIN,
            update_interval=update_interval,
            update_method=self._async_update_data,
        )

    @property
    def api(self) -> ayla_iot_unofficial.AylaApi:
        """Return the API instance."""
        return self._api

    def set_device_transition_state(
        self, device_serial: str, in_transition: bool
    ) -> None:
        """Set whether a device is in transition state (opening/closing)."""
        if in_transition:
            self._devices_in_transition.add(device_serial)
            # Switch to faster update interval if not already set
            if self.update_interval.total_seconds() != TRANSITION_UPDATE_INTERVAL:
                self.update_interval = timedelta(seconds=TRANSITION_UPDATE_INTERVAL)
                self.logger.debug(
                    "Switched to fast update interval for device %s", device_serial
                )
        else:
            self._devices_in_transition.discard(device_serial)
            # Switch back to normal interval if no devices are in transition
            if (
                not self._devices_in_transition
                and self.update_interval.total_seconds() != NORMAL_UPDATE_INTERVAL
            ):
                self.update_interval = timedelta(seconds=NORMAL_UPDATE_INTERVAL)
                self.logger.debug("Switched back to normal update interval")

    def is_device_in_transition(self, device_serial: str) -> bool:
        """Check if a device is currently in transition state."""
        return device_serial in self._devices_in_transition

    def device(self, serial: str) -> ayla_iot_unofficial.device.Device | None:
        """Return the latest object for a device, including after a poll replaces it."""
        return next(
            (device for device in self.data or [] if device.serial_number == serial),
            None,
        )

    def is_device_available(self, serial: str) -> bool:
        """Treat an explicit offline status as unavailable, even with cached values."""
        status = self.connection_info.get(serial, {}).get("connection_status")
        return self.device(serial) is not None and (
            not isinstance(status, str) or status.casefold() != "offline"
        )

    async def _async_update_data(self) -> list[ayla_iot_unofficial.device.Device]:
        """Fetch data."""
        try:
            try:
                self._api.check_auth()
            except ayla_iot_unofficial.AylaAuthExpiringError:
                await self._api.async_refresh_auth()
            except Exception as ex:
                self.logger.error("Failed to refresh auth: %s", ex)
                raise UpdateFailed("Failed to refresh auth") from ex

            # The library's async_get_devices() discards connection metadata.
            # Noma IQ platforms use generic property-based devices.
            raw_devices = await self._api.async_list_devices()
            devices = [
                ayla_iot_unofficial.device.Device(self._api, raw, europe=self._api.europe)
                for raw in raw_devices
            ]
            current_time = self.hass.loop.time()

            # Determine if this should be a full update or transition-only update
            is_full_update = (
                self.update_interval.total_seconds() == NORMAL_UPDATE_INTERVAL
                or current_time - self._last_full_update >= NORMAL_UPDATE_INTERVAL
            )

            if is_full_update:
                # Full update: update all devices
                self.logger.debug("Performing full update of all devices")
                for device in devices:
                    await device.async_update()
                self._last_full_update = current_time
            else:
                # Transition update: only update devices in transition
                self.logger.debug(
                    "Performing transition update for %d devices",
                    len(self._devices_in_transition),
                )
                previous = {device.serial_number: device for device in self.data or []}
                for device in devices:
                    if device.serial_number in self._devices_in_transition:
                        await device.async_update()
                        # Check if device status has changed from transition to stable
                        door_status = device.get_property_value("door_status")
                        if door_status in ["opened", "closed"]:
                            self.set_device_transition_state(
                                device.serial_number, False
                            )
                            self.logger.debug(
                                "Device %s transition completed, status: %s",
                                device.serial_number,
                                door_status,
                            )
                    elif old := previous.get(device.serial_number):
                        device.properties_full = old.properties_full

        except Exception as ex:
            raise UpdateFailed(f"Exception on getting states: {ex}") from ex
        else:
            self.mac_addresses = {raw["dsn"]: raw.get("mac") for raw in raw_devices}
            self.connection_info = {
                raw["dsn"]: {
                    "connection_status": raw.get("connection_status"),
                    "connected_at": raw.get("connected_at"),
                }
                for raw in raw_devices
            }
            return devices
