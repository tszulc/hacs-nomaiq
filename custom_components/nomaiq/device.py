"""Device identification and dehumidifier setpoint rules."""

from __future__ import annotations

import math

DEHUMIDIFIER_MODEL = "AY028MHA1"
DEHUMIDIFIER_OEM_MODEL = "dehum"
MIN_HUMIDITY = 30
MAX_HUMIDITY = 80


def is_dehumidifier(device: object) -> bool:
    """Recognize both model identifiers seen in the device PRs."""
    return (
        getattr(device, "device_model_number", None) == DEHUMIDIFIER_MODEL
        or getattr(device, "oem_model_number", None) == DEHUMIDIFIER_OEM_MODEL
    )


def stepped_humidity(requested: int, current: int | None) -> int:
    """Step to the next valid 5% value in the requested direction."""
    requested = min(max(int(requested), MIN_HUMIDITY), MAX_HUMIDITY)
    if current is None:
        value = round(requested / 5) * 5
    elif requested > current:
        value = math.ceil(requested / 5) * 5
    elif requested < current:
        value = math.floor(requested / 5) * 5
    else:
        value = requested
    return min(max(value, MIN_HUMIDITY), MAX_HUMIDITY)
