"""Constants for the Buderus WPS Heat Pump integration."""

from typing import Final

DOMAIN: Final = "buderus_wps"

# Configuration keys
CONF_PORT: Final = "port"
CONF_SCAN_INTERVAL: Final = "scan_interval"

# Default values
DEFAULT_PORT: Final = "/dev/ttyACM0"
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds

# Sensor types
SENSOR_OUTDOOR: Final = "outdoor"
SENSOR_SUPPLY: Final = "supply"
SENSOR_RETURN: Final = "return_temp"
SENSOR_DHW: Final = "dhw"
SENSOR_BRINE_IN: Final = "brine_in"

# Sensor display names
SENSOR_NAMES: Final = {
    SENSOR_OUTDOOR: "Outdoor Temperature",
    SENSOR_SUPPLY: "Supply Temperature",
    SENSOR_RETURN: "Return Temperature",
    SENSOR_DHW: "Hot Water Temperature",
    SENSOR_BRINE_IN: "Brine Inlet Temperature",
}

# Device info
MANUFACTURER: Final = "Buderus"
MODEL: Final = "WPS Heat Pump"
