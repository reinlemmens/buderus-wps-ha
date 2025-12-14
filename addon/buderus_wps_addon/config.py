"""Configuration management for the Buderus WPS Add-on.

Loads configuration from Home Assistant Supervisor (via bashio/environment)
or from environment variables for testing.
"""

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AddonConfig:
    """Add-on configuration from Supervisor."""

    serial_device: str
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str | None
    mqtt_password: str | None
    scan_interval: int
    log_level: str

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors: list[str] = []

        # Serial device validation
        if not self.serial_device:
            errors.append("serial_device is required")
        elif not self.serial_device.startswith("/dev/"):
            errors.append(f"serial_device must start with /dev/, got: {self.serial_device}")

        # MQTT host validation
        if not self.mqtt_host:
            errors.append("mqtt_host is required (or auto-detect must work)")

        # Port validation
        if not 1 <= self.mqtt_port <= 65535:
            errors.append(f"mqtt_port must be 1-65535, got: {self.mqtt_port}")

        # Scan interval validation
        if not 10 <= self.scan_interval <= 3600:
            errors.append(f"scan_interval must be 10-3600 seconds, got: {self.scan_interval}")

        # Log level validation
        valid_levels = {"debug", "info", "warning", "error"}
        if self.log_level.lower() not in valid_levels:
            errors.append(f"log_level must be one of {valid_levels}, got: {self.log_level}")

        return errors


def _get_bashio_config(key: str, default: str | None = None) -> str | None:
    """Get configuration value via bashio (Supervisor API).

    In the actual add-on container, this reads from /data/options.json
    which is populated by Home Assistant Supervisor.
    """
    options_file = Path("/data/options.json")
    if options_file.exists():
        try:
            with open(options_file) as f:
                options = json.load(f)
                return options.get(key, default)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read options.json: {e}")

    # Fall back to environment variable for testing
    env_key = f"BUDERUS_{key.upper()}"
    return os.environ.get(env_key, default)


def _auto_detect_mqtt() -> tuple[str, int]:
    """Auto-detect MQTT broker via Supervisor API.

    In Home Assistant, the Mosquitto add-on is available at core-mosquitto:1883.
    """
    # Check for Supervisor service info
    services_file = Path("/data/services.json")
    if services_file.exists():
        try:
            with open(services_file) as f:
                services = json.load(f)
                mqtt_service = services.get("mqtt", {})
                host = mqtt_service.get("host", "core-mosquitto")
                port = mqtt_service.get("port", 1883)
                return host, port
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read services.json: {e}")

    # Default to Mosquitto add-on
    return "core-mosquitto", 1883


def load_config() -> AddonConfig:
    """Load configuration from Supervisor or environment.

    Priority:
    1. /data/options.json (Supervisor)
    2. Environment variables (testing)
    3. Defaults
    """
    # Serial device (required)
    serial_device = _get_bashio_config("serial_device", "/dev/ttyACM0") or "/dev/ttyACM0"

    # MQTT configuration
    mqtt_host = _get_bashio_config("mqtt_host")
    mqtt_port_str = _get_bashio_config("mqtt_port")
    mqtt_username = _get_bashio_config("mqtt_username")
    mqtt_password = _get_bashio_config("mqtt_password")

    # Auto-detect MQTT if not configured
    if not mqtt_host:
        mqtt_host, default_port = _auto_detect_mqtt()
        mqtt_port = int(mqtt_port_str) if mqtt_port_str else default_port
    else:
        mqtt_port = int(mqtt_port_str) if mqtt_port_str else 1883

    # Scan interval
    scan_interval_str = _get_bashio_config("scan_interval", "60")
    scan_interval = int(scan_interval_str) if scan_interval_str else 60

    # Log level
    log_level = _get_bashio_config("log_level", "info") or "info"

    return AddonConfig(
        serial_device=serial_device,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        scan_interval=scan_interval,
        log_level=log_level,
    )
