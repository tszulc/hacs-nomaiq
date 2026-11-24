"""Pure device rules, runnable without Home Assistant installed."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


MODULE = Path(__file__).resolve().parents[1] / "custom_components/nomaiq/device.py"
spec = importlib.util.spec_from_file_location("nomaiq_device_rules", MODULE)
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


class DeviceRulesTest(unittest.TestCase):
    def test_dehumidifier_matches_either_identifier_only(self):
        for model, oem, expected in [
            ("AY028MHA1", None, True),
            (None, "dehum", True),
            ("AY028MHU1", "humid", False),
            ("AY028MHU1", "dehum", False),
            ("other", "other", False),
        ]:
            with self.subTest(model=model, oem=oem):
                self.assertEqual(
                    rules.is_dehumidifier(
                        SimpleNamespace(device_model_number=model, oem_model_number=oem)
                    ),
                    expected,
                )

    def test_humidifier_matches_the_model_without_relying_on_oem(self):
        for model, oem, expected in [
            ("AY028MHU1", None, True),
            ("AY028MHA1", "humid", False),
            ("future_humidifier", "humid", False),
        ]:
            with self.subTest(model=model, oem=oem):
                self.assertEqual(
                    rules.is_humidifier(
                        SimpleNamespace(device_model_number=model, oem_model_number=oem)
                    ),
                    expected,
                )

    def test_setpoint_steps_and_bounds(self):
        for requested, current, expected in [
            (61, 60, 65),
            (59, 60, 55),
            (60, 60, 60),
            (81, 80, 80),
            (29, 30, 30),
            (63, None, 65),
        ]:
            with self.subTest(requested=requested, current=current):
                self.assertEqual(rules.stepped_humidity(requested, current), expected)


if __name__ == "__main__":
    unittest.main()
