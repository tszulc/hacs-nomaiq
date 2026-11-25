"""Availability regressions using small HA/Ayla doubles, without installing HA."""

import asyncio
from datetime import timedelta
import importlib.util
import logging
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch


ROOT = Path(__file__).resolve().parents[1] / "custom_components/nomaiq"


class Coordinator:
    """Only the coordinator framework behavior used by this integration."""

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, logger, *, update_interval, **kwargs):
        self.hass = hass
        self.logger = logger
        self.update_interval = update_interval
        self.data = None
        self.last_update_success = True


class CoordinatorEntity:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def available(self):
        return self.coordinator.last_update_success


class Device:
    def __init__(self, api, raw, europe=False):
        self.serial_number = raw["dsn"]
        self.name = raw["product_name"]
        self.oem_model_number = "humid"
        self.device_model_number = "AY028MHU1"
        self.properties_full = {}
        self.async_update = AsyncMock()

    def get_property_value(self, name):
        return self.properties_full.get(name, {}).get("value")


def load_modules():
    """Load integration modules without running config-entry setup."""
    package = ModuleType("nomaiq_availability_test")
    package.__path__ = [str(ROOT)]
    package.NomaIQConfigEntry = object
    ayla = ModuleType("ayla_iot_unofficial")
    ayla.device = SimpleNamespace(Device=Device)
    ayla.AylaApi = object
    ayla.AylaAuthExpiringError = type("AylaAuthExpiringError", (Exception,), {})
    dependencies = {
        package.__name__: package,
        "ayla_iot_unofficial": ayla,
        "ayla_iot_unofficial.device": ayla.device,
        "homeassistant.core": SimpleNamespace(HomeAssistant=object),
        "homeassistant.exceptions": SimpleNamespace(ServiceValidationError=ValueError),
        "homeassistant.helpers.device_registry": SimpleNamespace(DeviceInfo=dict),
        "homeassistant.helpers.update_coordinator": SimpleNamespace(
            DataUpdateCoordinator=Coordinator,
            CoordinatorEntity=CoordinatorEntity,
            UpdateFailed=RuntimeError,
        ),
    }
    loaded = []
    with patch.dict(sys.modules, dependencies):
        for name in ("const", "coordinator", "entity", "diagnostics"):
            fullname = f"{package.__name__}.{name}"
            spec = importlib.util.spec_from_file_location(fullname, ROOT / f"{name}.py")
            module = importlib.util.module_from_spec(spec)
            sys.modules[fullname] = module
            spec.loader.exec_module(module)
            loaded.append(module)
    return loaded[1:]


coordinator_module, entity_module, diagnostics = load_modules()


class AvailabilityTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.raw = [
            {"dsn": "living", "product_name": "Living room", "connection_status": "Offline",
             "connected_at": "2026-11-20T10:00:00Z"},
            {"dsn": "bedroom", "product_name": "Bedroom", "connection_status": "Online"},
        ]
        self.api = SimpleNamespace(
            check_auth=Mock(), async_refresh_auth=AsyncMock(), europe=False,
            async_list_devices=AsyncMock(side_effect=lambda: self.raw),
        )
        self.coordinator = coordinator_module.NomaIQDataUpdateCoordinator(
            SimpleNamespace(loop=asyncio.get_running_loop()), logging.getLogger(__name__),
            timedelta(seconds=30), self.api,
        )

    async def refresh(self):
        self.coordinator.data = await self.coordinator._async_update_data()

    def entity(self, serial):
        return entity_module.NomaIQPropertyEntity(
            self.coordinator, self.coordinator.device(serial), "power_switch", None
        )

    async def test_offline_device_with_cached_properties_is_unavailable(self):
        await self.refresh()
        self.coordinator.device("living").properties_full = {"power_switch": {"value": 0}}
        self.assertFalse(self.entity("living").available)
        self.assertTrue(self.entity("bedroom").available)
        self.api.async_list_devices.assert_awaited_once()

    async def test_existing_entity_recovers_and_follows_replacement_objects(self):
        await self.refresh()
        entity = self.entity("living")
        for status, expected in [("online", True), ("OFFLINE", False),
                                 ("Polling Online", True), (None, True)]:
            with self.subTest(status=status):
                self.raw[0]["connection_status"] = status
                await self.refresh()
                self.assertEqual(entity.available, expected)
        self.raw[0].pop("connection_status")
        await self.refresh()
        self.assertTrue(entity.available)
        self.coordinator.last_update_success = False
        self.assertFalse(entity.available)
        self.coordinator.last_update_success = True
        self.raw.pop(0)
        await self.refresh()
        self.assertFalse(entity.available)

    async def test_transition_poll_refreshes_connection_without_losing_properties(self):
        await self.refresh()
        old = self.coordinator.device("living")
        old.properties_full = {"power_switch": {"value": 0}}
        self.coordinator.set_device_transition_state("bedroom", True)
        self.raw[0]["connection_status"] = "Online"
        await self.refresh()
        self.assertEqual(self.coordinator.device("living").properties_full, old.properties_full)
        self.coordinator.device("living").async_update.assert_not_awaited()
        self.assertTrue(self.entity("living").available)

    async def test_diagnostics_include_connection_fields_without_serials(self):
        await self.refresh()
        result = await diagnostics.async_get_config_entry_diagnostics(
            None, SimpleNamespace(runtime_data=self.coordinator)
        )
        living = result["devices"][0]
        self.assertEqual(living["connection_status"], "Offline")
        self.assertEqual(living["connected_at"], "2026-11-20T10:00:00Z")
        self.assertNotIn("dsn", living)
        self.assertNotIn("serial_number", living)

    async def test_failed_poll_does_not_publish_partial_connection_info(self):
        await self.refresh()
        self.raw[0]["connection_status"] = "Online"
        self.api.async_list_devices.side_effect = OSError("Cloud unavailable")
        with self.assertRaisesRegex(RuntimeError, "Cloud unavailable"):
            await self.refresh()
        self.assertEqual(
            self.coordinator.connection_info["living"]["connection_status"], "Offline"
        )


if __name__ == "__main__":
    unittest.main()
