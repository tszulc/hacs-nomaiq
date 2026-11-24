# Technical documentation

This page explains how the Noma IQ integration works, which devices it supports, and how the tools in the repository fit in. For setup and for helping add a device, see the [README](../README.md) and [capturing device states](capturing-device-states.md).

## How it connects

Noma IQ devices are cloud devices on the Ayla IoT platform. The integration signs in to Ayla with the username and password from the Noma IQ app, then polls the cloud for device properties and writes changes back to it.

- **Library:** `ayla_iot_unofficial` 1.5.0, pinned in `manifest.json`.
- **Client ID and secret:** the app's credentials, in `custom_components/nomaiq/const.py`. These aren't user secrets, but they are hardcoded.
- **Config flow:** asks for username and password, checks them by signing in, and stores them in the config entry. Reauthentication uses the same form.
- **Polling:** the coordinator (`coordinator.py`) refreshes every 30 seconds. While a cover is opening or closing, it speeds up to every 2 seconds until the door reaches a stable state.

## Files

| File | Purpose |
|---|---|
| `__init__.py` | Sets up the config entry, registers the platforms, and registers the `capture_state` service |
| `config_flow.py` | Credentials form and reauthentication |
| `coordinator.py` | Polls devices, tracks devices in transition, and holds captured states |
| `cover.py` | Garage door (`oem_model` `gdo`) |
| `light.py` | Light on a device that has `light_control` and `light_name` |
| `humidifier.py` | AY028MHU1 humidifier and AY028MHA1 dehumidifier controls |
| `select.py` | Dehumidifier fan speed, humidifier mist output and temperature, and unit lights |
| `switch.py` | Writable boolean properties, including plug outlets |
| `sensor.py` and `binary_sensor.py` | Humidity measurements and device alerts |
| `device.py` and `entity.py` | Device identification, humidity steps, and current device access |
| `diagnostics.py` | Diagnostics download |
| `services.yaml` | Describes the `capture_state` service in the Home Assistant UI |

## How devices are matched

On setup, each device returned by the cloud is checked against the platforms:

- `gdo` becomes a garage door cover.
- A device with `light_control` and `light_name` properties becomes a light.
- `dehum` or model `AY028MHA1` becomes a dehumidifier and fan speed select, with sensors for properties the device exposes.
- `AY028MHU1` uses the exact device model number and has its own controls and alerts.
- Other writable boolean properties can become switches. `plug-2` only exposes numbered outlets.

Devices that match none of these are ignored. Their properties still appear in the diagnostics download.

## Dehumidifier

The dehumidifier stores its settings as raw strings, which don't match the labels in the app. The mapping lives in `humidifier.py` and `select.py`.

| Entity | Property | Read | Write | Values |
|---|---|---|---|---|
| Humidifier (on/off) | `power` | yes | yes | 1 = on, 0 = off |
| Humidifier (target) | `humidity` | yes | yes | 30–80, step 5 |
| Humidifier (current) | `indoor_humidity` | yes | no | Measured value |
| Humidifier (mode) | `mode` | yes | yes | manual ↔ `Normal`, auto dry ↔ `Auto`, continuous ↔ `Persistent` |
| Select (fan speed) | `fan_speed` | yes | yes | auto ↔ `Smart`, slow ↔ `Low`, fast ↔ `High` |

The device only accepts multiples of 5 for target humidity. Home Assistant's +/- buttons change the target by 1%, so the integration rounds in the direction of the change: increasing rounds up to the next multiple of 5, and decreasing rounds down. From 60, one press up sends 65 and one press down sends 55. Values are clamped to 30–80.

**Verified:** writing `humidity` through the cloud, confirmed by reading it back.

**Not verified:** writing `mode` and `fan_speed` through the cloud. The mappings above come from changes made in the app, not from the integration.

**Unknown:** whether `humidity` takes effect in every mode.

## AY028MHU1 humidifier

| Ayla property | Home Assistant behavior |
|---|---|
| `power_switch` | Humidifier power |
| `night_mode` | Unit lights select. The app shows Bright for the captured `0` state, so the other boolean value is mapped to Dim. |
| `water_runout` | Water tank empty alert |
| `change_filter` | Replace filter alert. The state is unknown until the device reports a value. |
| `vapour_setting` | Mist output select. Low is `1`, Medium is `3`, and High is `7`. |
| `mist_setting` | Mist temperature select. Cool is `1` and Warm is `2`. |
| `timer_setting` | Raw values are available in diagnostics. Labeled captures are needed to map the timer options. |
| `refill_timer`, `filter_replace` | Available in diagnostics. Both were unset in the startup captures. |
| `version` | Firmware shown on the Home Assistant device page when reported. |

The device reports mist settings and has no reported current or target humidity property. Capture each timer option and any refill or filter reset action to map the remaining settings.

## Diagnostics and captured states

The `capture_state` service fetches fresh values for one device and stores them with a timestamp and a description. It's available under **Developer Tools > Actions** as **Noma IQ: Capture device state**.

Captured states are kept in memory on the coordinator. A restart clears them.

Downloading diagnostics (**Settings > Devices & services > Noma IQ > Download diagnostics**) returns:

- `devices`: each device's name, `oem_model`, model number, and property values.
- `captured_states`: every capture so far.

The download omits the config entry credentials and device serial numbers as top-level fields. Property values and device names may still contain identifying information, so review the file before sharing it.

## Tools

Scripts in `tools/` run outside Home Assistant and need `NOMAIQ_USER` and `NOMAIQ_PASS` set in the environment. They read the client ID and secret from `const.py`.

- `discover_devices.py`: signs in, lists devices, and prints each device's properties. It only reads data.
- `write_test.py`: changes the target humidity on the dehumidifier, reads it back, and restores the original value. It asks for confirmation first, and it changes the real device.

## Adding support for a device

1. Capture states as described in [capturing device states](capturing-device-states.md).
2. Find the device's `oem_model` and property names in the diagnostics file.
3. Add a platform for it, or extend an existing one, and register it in `_PLATFORMS` in `__init__.py`.
4. Add the value mapping for any labels that differ from the stored values.
5. Test the writes on the device before relying on them.

## Limitations

- The Ayla library is unofficial and may change without notice.
- Writes are confirmed only for `humidity`.
- Mode and fan speed mappings come from the app and haven't been checked against the cloud.
- Captured states are lost on restart.
- The integration hasn't been tested with more than one dehumidifier.
