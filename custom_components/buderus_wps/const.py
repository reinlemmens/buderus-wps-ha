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

# Heating Season Mode (idx=884)
# Used for peak hour blocking - set to OFF (2) to disable heating
HEATING_SEASON_MODE_WINTER: Final = 0  # Forced heating
HEATING_SEASON_MODE_AUTO: Final = 1    # Normal operation
HEATING_SEASON_MODE_OFF: Final = 2     # No heating (summer mode)

HEATING_SEASON_OPTIONS: Final = {
    HEATING_SEASON_MODE_WINTER: "Winter (Forced)",
    HEATING_SEASON_MODE_AUTO: "Automatic",
    HEATING_SEASON_MODE_OFF: "Off (Summer)",
}

# DHW Program Mode (idx=489)
# Used for peak hour blocking - set to OFF (2) to disable DHW
DHW_PROGRAM_MODE_AUTO: Final = 0       # Follows time program
DHW_PROGRAM_MODE_ON: Final = 1         # Always on
DHW_PROGRAM_MODE_OFF: Final = 2        # Always off

DHW_PROGRAM_OPTIONS: Final = {
    DHW_PROGRAM_MODE_AUTO: "Automatic",
    DHW_PROGRAM_MODE_ON: "Always On",
    DHW_PROGRAM_MODE_OFF: "Always Off",
}
