# Add-on Configuration Contract

**Feature**: 013-ha-supervisor-addon
**Date**: 2025-12-13

## Overview

This contract defines the configuration schema for the Home Assistant Supervisor add-on.

## config.yaml Structure

```yaml
name: "Buderus WPS Heat Pump"
version: "1.0.0"
slug: buderus-wps
description: "Control Buderus WPS heat pumps via CAN bus over USB serial"
url: "https://github.com/your-username/buderus-wps-ha"

# Architecture support
arch:
  - amd64
  - aarch64

# Startup behavior
startup: application
boot: auto

# Device access
devices:
  - "/dev/ttyUSB0"
  - "/dev/ttyACM0"
  - "/dev/serial/by-id/*"
uart: true

# Ingress (optional web UI)
ingress: false

# Options schema
options:
  serial_device: "/dev/ttyACM0"
  scan_interval: 60
  log_level: "info"

schema:
  serial_device: str
  mqtt_host: str?
  mqtt_port: int(1883)?
  mqtt_username: str?
  mqtt_password: str?
  scan_interval: int(60)?
  log_level: list(debug|info|warning|error)?
```

## Configuration Options

### serial_device (required)

Path to the USB serial device connected to the USBtin CAN adapter.

| Property | Value |
|----------|-------|
| Type | string |
| Required | Yes |
| Default | "/dev/ttyACM0" |
| Examples | "/dev/ttyACM0", "/dev/ttyUSB0", "/dev/serial/by-id/usb-MCS_USBtin-if00" |

**Validation**:
- Must start with "/dev/"
- Device must be accessible at runtime

### mqtt_host (optional)

MQTT broker hostname. If not specified, auto-detected via Supervisor API.

| Property | Value |
|----------|-------|
| Type | string |
| Required | No |
| Default | Auto-detected |
| Examples | "core-mosquitto", "192.168.1.100" |

**Auto-detection**:
- Checks for `hassio.supervisor` service
- Falls back to "core-mosquitto" for Mosquitto add-on

### mqtt_port (optional)

MQTT broker port.

| Property | Value |
|----------|-------|
| Type | integer |
| Required | No |
| Default | 1883 |
| Range | 1-65535 |

### mqtt_username (optional)

MQTT authentication username.

| Property | Value |
|----------|-------|
| Type | string |
| Required | No |
| Default | None |

### mqtt_password (optional)

MQTT authentication password.

| Property | Value |
|----------|-------|
| Type | string |
| Required | No |
| Default | None |

### scan_interval (optional)

Polling interval for sensor updates in seconds.

| Property | Value |
|----------|-------|
| Type | integer |
| Required | No |
| Default | 60 |
| Range | 10-3600 |

**Notes**:
- Lower values increase CAN bus traffic
- Values below 30 seconds may cause issues with some heat pump models

### log_level (optional)

Logging verbosity level.

| Property | Value |
|----------|-------|
| Type | enum |
| Required | No |
| Default | "info" |
| Options | "debug", "info", "warning", "error" |

**Log content by level**:
- **debug**: CAN bus messages, MQTT traffic, internal state
- **info**: Connection events, polling cycles, errors
- **warning**: Recoverable errors, timeouts, reconnections
- **error**: Failures, unrecoverable errors

## Environment Variables

The add-on exposes configuration via environment variables:

| Variable | Source |
|----------|--------|
| BUDERUS_SERIAL_DEVICE | options.serial_device |
| BUDERUS_MQTT_HOST | options.mqtt_host or auto-detected |
| BUDERUS_MQTT_PORT | options.mqtt_port |
| BUDERUS_MQTT_USERNAME | options.mqtt_username |
| BUDERUS_MQTT_PASSWORD | options.mqtt_password |
| BUDERUS_SCAN_INTERVAL | options.scan_interval |
| BUDERUS_LOG_LEVEL | options.log_level |

## Bashio Configuration Access

```bash
#!/usr/bin/with-contenv bashio

SERIAL_DEVICE=$(bashio::config 'serial_device')
MQTT_HOST=$(bashio::config 'mqtt_host' 'core-mosquitto')
MQTT_PORT=$(bashio::config 'mqtt_port' '1883')
SCAN_INTERVAL=$(bashio::config 'scan_interval' '60')
LOG_LEVEL=$(bashio::config 'log_level' 'info')
```

## Python Configuration Access

```python
import os

config = AddonConfig(
    serial_device=os.environ["BUDERUS_SERIAL_DEVICE"],
    mqtt_host=os.environ.get("BUDERUS_MQTT_HOST", "core-mosquitto"),
    mqtt_port=int(os.environ.get("BUDERUS_MQTT_PORT", "1883")),
    mqtt_username=os.environ.get("BUDERUS_MQTT_USERNAME"),
    mqtt_password=os.environ.get("BUDERUS_MQTT_PASSWORD"),
    scan_interval=int(os.environ.get("BUDERUS_SCAN_INTERVAL", "60")),
    log_level=os.environ.get("BUDERUS_LOG_LEVEL", "info"),
)
```

## Validation Behavior

### On Startup

1. Validate serial_device exists and is accessible
2. If serial_device not found, log error and retry every 30 seconds
3. Validate MQTT connection if credentials provided
4. If MQTT fails, log warning and use auto-detection

### Runtime Validation

1. Commands validated against parameter ranges before transmission
2. Invalid commands rejected with error logged
3. Connection state monitored, availability updated accordingly

## Error Handling

| Error | Behavior |
|-------|----------|
| Serial device not found | Log error, retry every 30s |
| Serial permission denied | Log error with "add user to dialout" hint |
| MQTT connection failed | Log warning, retry with exponential backoff |
| Invalid configuration value | Log error, use default |
