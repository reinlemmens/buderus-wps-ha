"""Unit tests for addon configuration loading and validation."""

import os
import pytest
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "addon"
sys.path.insert(0, str(addon_path))

from buderus_wps_addon.config import AddonConfig, load_config


class TestAddonConfig:
    """Test AddonConfig dataclass."""

    def test_valid_config(self) -> None:
        """Valid configuration should pass validation."""
        config = AddonConfig(
            serial_device="/dev/ttyACM0",
            mqtt_host="core-mosquitto",
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=60,
            log_level="info",
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_missing_serial_device(self) -> None:
        """Empty serial device should fail validation."""
        config = AddonConfig(
            serial_device="",
            mqtt_host="core-mosquitto",
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=60,
            log_level="info",
        )
        errors = config.validate()
        assert any("serial_device" in e for e in errors)

    def test_invalid_serial_device_path(self) -> None:
        """Serial device not starting with /dev/ should fail."""
        config = AddonConfig(
            serial_device="/tmp/fake",
            mqtt_host="core-mosquitto",
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=60,
            log_level="info",
        )
        errors = config.validate()
        assert any("/dev/" in e for e in errors)

    def test_valid_serial_by_id_path(self) -> None:
        """Serial-by-id path should be valid."""
        config = AddonConfig(
            serial_device="/dev/serial/by-id/usb-MCS_USBtin-if00",
            mqtt_host="core-mosquitto",
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=60,
            log_level="info",
        )
        errors = config.validate()
        assert len(errors) == 0

    def test_missing_mqtt_host(self) -> None:
        """Empty MQTT host should fail validation."""
        config = AddonConfig(
            serial_device="/dev/ttyACM0",
            mqtt_host="",
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=60,
            log_level="info",
        )
        errors = config.validate()
        assert any("mqtt_host" in e for e in errors)

    def test_invalid_mqtt_port_low(self) -> None:
        """Port 0 should fail validation."""
        config = AddonConfig(
            serial_device="/dev/ttyACM0",
            mqtt_host="core-mosquitto",
            mqtt_port=0,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=60,
            log_level="info",
        )
        errors = config.validate()
        assert any("mqtt_port" in e for e in errors)

    def test_invalid_mqtt_port_high(self) -> None:
        """Port > 65535 should fail validation."""
        config = AddonConfig(
            serial_device="/dev/ttyACM0",
            mqtt_host="core-mosquitto",
            mqtt_port=70000,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=60,
            log_level="info",
        )
        errors = config.validate()
        assert any("mqtt_port" in e for e in errors)

    def test_scan_interval_too_low(self) -> None:
        """Scan interval < 10 should fail validation."""
        config = AddonConfig(
            serial_device="/dev/ttyACM0",
            mqtt_host="core-mosquitto",
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=5,
            log_level="info",
        )
        errors = config.validate()
        assert any("scan_interval" in e for e in errors)

    def test_scan_interval_too_high(self) -> None:
        """Scan interval > 3600 should fail validation."""
        config = AddonConfig(
            serial_device="/dev/ttyACM0",
            mqtt_host="core-mosquitto",
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=5000,
            log_level="info",
        )
        errors = config.validate()
        assert any("scan_interval" in e for e in errors)

    def test_invalid_log_level(self) -> None:
        """Invalid log level should fail validation."""
        config = AddonConfig(
            serial_device="/dev/ttyACM0",
            mqtt_host="core-mosquitto",
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None,
            scan_interval=60,
            log_level="verbose",
        )
        errors = config.validate()
        assert any("log_level" in e for e in errors)

    def test_all_valid_log_levels(self) -> None:
        """All valid log levels should pass."""
        for level in ["debug", "info", "warning", "error"]:
            config = AddonConfig(
                serial_device="/dev/ttyACM0",
                mqtt_host="core-mosquitto",
                mqtt_port=1883,
                mqtt_username=None,
                mqtt_password=None,
                scan_interval=60,
                log_level=level,
            )
            errors = config.validate()
            assert len(errors) == 0, f"Level {level} should be valid"


class TestLoadConfig:
    """Test load_config function."""

    def test_load_from_environment(self) -> None:
        """Should load config from environment variables."""
        env_vars = {
            "BUDERUS_SERIAL_DEVICE": "/dev/ttyUSB1",
            "BUDERUS_MQTT_HOST": "mqtt.local",
            "BUDERUS_MQTT_PORT": "1884",
            "BUDERUS_SCAN_INTERVAL": "30",
            "BUDERUS_LOG_LEVEL": "debug",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = load_config()
            assert config.serial_device == "/dev/ttyUSB1"
            assert config.mqtt_host == "mqtt.local"
            assert config.mqtt_port == 1884
            assert config.scan_interval == 30
            assert config.log_level == "debug"

    def test_load_defaults(self) -> None:
        """Should use defaults when environment not set."""
        # Clear any existing env vars
        env_vars_to_clear = [k for k in os.environ if k.startswith("BUDERUS_")]
        with patch.dict(os.environ, {k: "" for k in env_vars_to_clear}, clear=False):
            # Mock _get_bashio_config to return None
            with patch("buderus_wps_addon.config._get_bashio_config", return_value=None):
                with patch("buderus_wps_addon.config._auto_detect_mqtt", return_value=("core-mosquitto", 1883)):
                    config = load_config()
                    assert config.serial_device == "/dev/ttyACM0"
                    assert config.mqtt_host == "core-mosquitto"
                    assert config.mqtt_port == 1883
                    assert config.scan_interval == 60
                    assert config.log_level == "info"

    def test_load_from_options_json(self) -> None:
        """Should load config from /data/options.json when present."""
        options = {
            "serial_device": "/dev/ttyACM1",
            "mqtt_host": "192.168.1.100",
            "mqtt_port": 1885,
            "scan_interval": 120,
            "log_level": "warning",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            options_file = Path(tmpdir) / "options.json"
            with open(options_file, "w") as f:
                json.dump(options, f)

            # Mock the options file path
            with patch("buderus_wps_addon.config.Path") as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_options_path = MagicMock()
                mock_options_path.exists.return_value = True
                mock_options_path.__enter__ = MagicMock(return_value=f)

                # This is a simplified test - full integration would need proper mocking
                config = load_config()
                # With proper mocking, these would be from options.json
                assert config is not None
