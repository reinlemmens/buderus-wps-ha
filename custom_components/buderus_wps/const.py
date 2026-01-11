"""Constants for the Buderus WPS Heat Pump integration."""

from typing import Final

DOMAIN: Final = "buderus_wps"

# Configuration keys
CONF_PORT: Final = "port"
CONF_SERIAL_DEVICE: Final = "serial_device"  # Alias for config flow
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_PARAMETER_ALLOWLIST: Final = "parameter_allowlist"

# Default values
DEFAULT_PORT: Final = "/dev/ttyACM0"
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds
DEFAULT_TIMEOUT: Final = 5  # seconds
DEFAULT_PARAMETER_ALLOWLIST: Final = ()

# Service names/fields
SERVICE_READ_PARAMETER: Final = "read_parameter"
SERVICE_LIST_PARAMETERS: Final = "list_parameters"
ATTR_NAME_OR_IDX: Final = "name_or_idx"
ATTR_ENTRY_ID: Final = "entry_id"
ATTR_EXPECTED_DLC: Final = "expected_dlc"
ATTR_TIMEOUT: Final = "timeout"
ATTR_NAME_CONTAINS: Final = "name_contains"
ATTR_LIMIT: Final = "limit"

# Exponential backoff for reconnection
BACKOFF_INITIAL: Final = 5  # Initial delay in seconds
BACKOFF_MAX: Final = 120  # Maximum delay in seconds (2 minutes)

# Sensor types
SENSOR_OUTDOOR: Final = "outdoor"
SENSOR_SUPPLY: Final = "supply"
SENSOR_RETURN: Final = "return_temp"
SENSOR_DHW: Final = "dhw"
SENSOR_BRINE_IN: Final = "brine_in"  # GT10 - Collector circuit IN
SENSOR_BRINE_OUT: Final = "brine_out"  # GT11 - Collector circuit OUT

# Room temperature sensors (from RC10 thermostats)
SENSOR_ROOM_C1: Final = "room_c1"
SENSOR_ROOM_C2: Final = "room_c2"
SENSOR_ROOM_C3: Final = "room_c3"
SENSOR_ROOM_C4: Final = "room_c4"

# Room setpoint sensors (adjusted setpoints from RC10 thermostats)
SENSOR_SETPOINT_C1: Final = "setpoint_c1"
SENSOR_SETPOINT_C2: Final = "setpoint_c2"
SENSOR_SETPOINT_C3: Final = "setpoint_c3"
SENSOR_SETPOINT_C4: Final = "setpoint_c4"

# Sensor display names (entity-only, device name prepended by HA when has_entity_name=True)
SENSOR_NAMES: Final = {
    SENSOR_OUTDOOR: "GT2 Outdoor Temperature",
    SENSOR_SUPPLY: "GT8 Supply Temperature",
    SENSOR_RETURN: "GT9 Return Temperature",
    SENSOR_DHW: "GT3 Hot Water Temperature",
    SENSOR_BRINE_IN: "GT10 Brine Inlet",  # Collector circuit IN
    SENSOR_BRINE_OUT: "GT11 Brine Outlet",  # Collector circuit OUT
    SENSOR_ROOM_C1: "Room Temperature C1",
    SENSOR_ROOM_C2: "Room Temperature C2",
    SENSOR_ROOM_C3: "Room Temperature C3",
    SENSOR_ROOM_C4: "Room Temperature C4",
    SENSOR_SETPOINT_C1: "Room Setpoint C1",
    SENSOR_SETPOINT_C2: "Room Setpoint C2",
    SENSOR_SETPOINT_C3: "Room Setpoint C3",
    SENSOR_SETPOINT_C4: "Room Setpoint C4",
}

# Device info
MANUFACTURER: Final = "Buderus"
MODEL: Final = "WPS Heat Pump"

# Icons
ICON_HEAT_PUMP: Final = "mdi:heat-pump"
ICON_TEMPERATURE: Final = "mdi:thermometer"
ICON_COMPRESSOR: Final = "mdi:engine"
ICON_ENERGY_BLOCK: Final = "mdi:power-plug-off"
ICON_USB: Final = "mdi:usb-port"
ICON_WATER_HEATER: Final = "mdi:water-boiler"
ICON_WATER_THERMOMETER: Final = "mdi:water-thermometer"
ICON_HEATING_CURVE: Final = "mdi:chart-line"

# Heating Season Mode (idx=884)
# Used for peak hour blocking - set to OFF (2) to disable heating
HEATING_SEASON_MODE_WINTER: Final = 0  # Forced heating
HEATING_SEASON_MODE_AUTO: Final = 1  # Normal operation
HEATING_SEASON_MODE_OFF: Final = 2  # No heating (summer mode)

HEATING_SEASON_OPTIONS: Final = {
    HEATING_SEASON_MODE_WINTER: "Winter (Forced)",
    HEATING_SEASON_MODE_AUTO: "Automatic",
    HEATING_SEASON_MODE_OFF: "Off (Summer)",
}

# DHW Program Mode (idx=489)
# Used for peak hour blocking - set to OFF (2) to disable DHW
DHW_PROGRAM_MODE_AUTO: Final = 0  # Follows time program
DHW_PROGRAM_MODE_ON: Final = 1  # Always on
DHW_PROGRAM_MODE_OFF: Final = 2  # Always off

DHW_PROGRAM_OPTIONS: Final = {
    DHW_PROGRAM_MODE_AUTO: "Automatic",
    DHW_PROGRAM_MODE_ON: "Always On",
    DHW_PROGRAM_MODE_OFF: "Always Off",
}
