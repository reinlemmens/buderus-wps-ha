"""Contract tests for addon config.yaml schema validation.

These tests validate that config.yaml follows Home Assistant add-on conventions.
"""

import pytest
import yaml
from pathlib import Path


@pytest.fixture
def config_yaml() -> dict:
    """Load addon config.yaml."""
    config_path = Path(__file__).parent.parent.parent / "addon" / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


class TestAddonMetadata:
    """Test add-on metadata fields."""

    def test_name_present(self, config_yaml: dict) -> None:
        """Add-on must have a name."""
        assert "name" in config_yaml
        assert config_yaml["name"] == "Buderus WPS Heat Pump"

    def test_version_format(self, config_yaml: dict) -> None:
        """Version should be semantic versioning format."""
        assert "version" in config_yaml
        version = config_yaml["version"]
        # Simple check for semver-like format
        parts = version.split(".")
        assert len(parts) >= 2, "Version should have at least major.minor"

    def test_slug_present(self, config_yaml: dict) -> None:
        """Add-on must have a slug."""
        assert "slug" in config_yaml
        assert config_yaml["slug"] == "buderus-wps"

    def test_description_present(self, config_yaml: dict) -> None:
        """Add-on should have a description."""
        assert "description" in config_yaml
        assert len(config_yaml["description"]) > 10


class TestArchitectureSupport:
    """Test architecture configuration."""

    def test_arch_list_present(self, config_yaml: dict) -> None:
        """Architecture list must be present."""
        assert "arch" in config_yaml
        assert isinstance(config_yaml["arch"], list)

    def test_amd64_supported(self, config_yaml: dict) -> None:
        """Must support amd64 (Intel/AMD 64-bit)."""
        assert "amd64" in config_yaml["arch"]

    def test_aarch64_supported(self, config_yaml: dict) -> None:
        """Must support aarch64 (Raspberry Pi 4)."""
        assert "aarch64" in config_yaml["arch"]


class TestDeviceAccess:
    """Test USB device access configuration."""

    def test_devices_list_present(self, config_yaml: dict) -> None:
        """Devices list should be present for USB access."""
        assert "devices" in config_yaml
        assert isinstance(config_yaml["devices"], list)

    def test_ttyacm_devices_included(self, config_yaml: dict) -> None:
        """Should include /dev/ttyACM* devices (most USBtin adapters)."""
        devices = config_yaml["devices"]
        ttyacm_found = any("/dev/ttyACM" in d for d in devices)
        assert ttyacm_found, "Should include ttyACM devices"

    def test_ttyusb_devices_included(self, config_yaml: dict) -> None:
        """Should include /dev/ttyUSB* devices (some adapters)."""
        devices = config_yaml["devices"]
        ttyusb_found = any("/dev/ttyUSB" in d for d in devices)
        assert ttyusb_found, "Should include ttyUSB devices"

    def test_uart_enabled(self, config_yaml: dict) -> None:
        """UART should be enabled for serial communication."""
        assert config_yaml.get("uart") is True


class TestOptionsSchema:
    """Test configuration options schema."""

    def test_options_present(self, config_yaml: dict) -> None:
        """Default options should be present."""
        assert "options" in config_yaml
        assert isinstance(config_yaml["options"], dict)

    def test_serial_device_default(self, config_yaml: dict) -> None:
        """Serial device should have a default."""
        assert "serial_device" in config_yaml["options"]

    def test_scan_interval_default(self, config_yaml: dict) -> None:
        """Scan interval should have a default."""
        assert "scan_interval" in config_yaml["options"]
        assert config_yaml["options"]["scan_interval"] == 60

    def test_log_level_default(self, config_yaml: dict) -> None:
        """Log level should have a default."""
        assert "log_level" in config_yaml["options"]
        assert config_yaml["options"]["log_level"] == "info"

    def test_schema_present(self, config_yaml: dict) -> None:
        """Schema should be present for validation."""
        assert "schema" in config_yaml
        assert isinstance(config_yaml["schema"], dict)

    def test_schema_has_required_fields(self, config_yaml: dict) -> None:
        """Schema should define all required fields."""
        schema = config_yaml["schema"]
        assert "serial_device" in schema
        assert "scan_interval" in schema
        assert "log_level" in schema

    def test_schema_has_optional_mqtt_fields(self, config_yaml: dict) -> None:
        """Schema should define optional MQTT fields (marked with ?)."""
        schema = config_yaml["schema"]
        assert "mqtt_host" in schema
        assert "mqtt_port" in schema
        assert "mqtt_username" in schema
        assert "mqtt_password" in schema


class TestStartupConfiguration:
    """Test startup behavior configuration."""

    def test_startup_type(self, config_yaml: dict) -> None:
        """Startup should be 'application' (non-system service)."""
        assert config_yaml.get("startup") == "application"

    def test_boot_auto(self, config_yaml: dict) -> None:
        """Boot should be 'auto' to start on HA boot."""
        assert config_yaml.get("boot") == "auto"


class TestIngressConfiguration:
    """Test ingress (web UI) configuration."""

    def test_no_web_ui(self, config_yaml: dict) -> None:
        """Ingress should be disabled (no web UI)."""
        assert config_yaml.get("ingress") is False
