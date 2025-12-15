"""Constants for the Buderus WPS Heat Pump integration."""

# Integration domain
DOMAIN = "buderus_wps"

# Configuration keys
CONF_SERIAL_DEVICE = "serial_device"
CONF_SCAN_INTERVAL = "scan_interval"

# Default values
DEFAULT_SCAN_INTERVAL = 60  # seconds
DEFAULT_TIMEOUT = 5  # seconds

# Platforms
PLATFORMS = ["sensor", "binary_sensor", "select", "number", "switch"]

# Device info
MANUFACTURER = "Buderus"
MODEL = "WPS Heat Pump"
