# Noma IQ HACS integration

## About

This integration exposes devices from the Noma IQ app through the Ayla cloud. Supported devices include:

- Garage door opener and its light
- AY028MHA1 dehumidifier: power, humidity target and reading, mode, fan speed, tank and fault alerts
- AY028MHU1 humidifier: power, Dim/Bright unit lights, water tank and filter alerts
- Smart plugs with writable outlet properties, including `plug-2`

See the [AY028MHU1 property notes](docs/technical.md#ay028mhu1-humidifier) for settings still being mapped. To identify other devices, use the diagnostics download and [state capture service](docs/capturing-device-states.md).

## Installation

Installation is done like any other Home Assistant HACS integration.

### Requirements

In order to setup this integration you will need:

- A Home Assistant instance with [HACS](https://hacs.xyz/) installed.

### HACS Installation

Click the button below:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=mnfjorge&repository=https%3A%2F%2Fgithub.com%2Fmnfjorge%2Fhacs-nomaiq&category=integration)

Or search for "Noma IQ" in the HACS store. If you don't see it there, you can [add this repository url as a HACS custom repository](https://hacs.xyz/docs/faq/custom_repositories).

## Home Assistant Integration

[![Open your Home Assistant instance and start setting up a new integration of a specific brand.](https://my.home-assistant.io/badges/brand.svg)](https://my.home-assistant.io/redirect/brand/?brand=+Noma+IQ)

After installation, setup the integration via the web UI like any other integration. When prompted, provide the following:

- Username: your username to log into the Noma IQ app
- Password: your password to log into the Noma IQ app

### Troubleshooting

If you are having issues connecting, make sure your credentials are correct using the Noma IQ in your mobile app. If you're still having trouble, you can open a new issue here: https://github.com/mnfjorge/hacs-nomaiq/issues/new

## Contributions

Contributions are welcome!
