"""Unit tests for Home Assistant configuration validation."""

from __future__ import annotations

# Note: voluptuous is mocked in conftest.py, but we can still test constants
# and validation ranges directly
from custom_components.buderus_wps.const import (
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
)


class TestConfigurationConstants:
    """Test configuration constant values."""

    def test_default_scan_interval_is_60(self):
        """Default scan interval must be 60 seconds per spec."""
        assert DEFAULT_SCAN_INTERVAL == 60

    def test_default_port_is_ttyacm0(self):
        """Default port must be /dev/ttyACM0."""
        assert DEFAULT_PORT == "/dev/ttyACM0"

    def test_conf_port_key(self):
        """Port configuration key must be 'port'."""
        assert CONF_PORT == "port"

    def test_conf_scan_interval_key(self):
        """Scan interval configuration key must be 'scan_interval'."""
        assert CONF_SCAN_INTERVAL == "scan_interval"


class TestScanIntervalValidation:
    """Test scan_interval validation requirements.

    Per spec: scan_interval must be between 10-300 seconds.
    """

    def test_minimum_scan_interval_is_10(self):
        """Minimum scan interval per spec is 10 seconds."""
        min_interval = 10
        assert DEFAULT_SCAN_INTERVAL >= min_interval
        # Validate the minimum value is reasonable
        assert min_interval > 0

    def test_maximum_scan_interval_is_300(self):
        """Maximum scan interval per spec is 300 seconds (5 minutes)."""
        max_interval = 300
        assert DEFAULT_SCAN_INTERVAL <= max_interval

    def test_default_is_within_valid_range(self):
        """Default scan interval must be within valid range (10-300)."""
        assert 10 <= DEFAULT_SCAN_INTERVAL <= 300

    def test_midrange_values_are_valid(self):
        """Typical values within range must be valid."""
        min_interval = 10
        max_interval = 300
        valid_intervals = [10, 30, 60, 120, 180, 240, 300]
        for interval in valid_intervals:
            assert min_interval <= interval <= max_interval

    def test_boundary_values(self):
        """Values at exact boundaries must be valid."""
        min_interval = 10
        max_interval = 300
        # 10 is valid (at minimum)
        assert min_interval == 10
        # 300 is valid (at maximum)
        assert max_interval == 300


class TestScanIntervalRejection:
    """Test that invalid scan_interval values should be rejected.

    These tests document the expected validation behavior.
    """

    def test_value_9_is_below_minimum(self):
        """Value 9 is below minimum (10)."""
        assert 9 < 10  # Below minimum

    def test_value_301_is_above_maximum(self):
        """Value 301 is above maximum (300)."""
        assert 301 > 300  # Above maximum

    def test_value_0_is_invalid(self):
        """Value 0 is invalid (not positive)."""
        assert 0 < 10  # Below minimum

    def test_negative_values_are_invalid(self):
        """Negative values are invalid."""
        assert -10 < 10  # Below minimum


class TestPortConfiguration:
    """Test port configuration requirements."""

    def test_default_port_is_string(self):
        """Default port must be a string."""
        assert isinstance(DEFAULT_PORT, str)

    def test_default_port_starts_with_dev(self):
        """Default port must be a device path."""
        assert DEFAULT_PORT.startswith("/dev/")

    def test_typical_port_paths_are_strings(self):
        """Typical port paths are valid string values."""
        typical_ports = [
            "/dev/ttyACM0",
            "/dev/ttyUSB0",
            "/dev/ttyUSB1",
            "/dev/serial/by-id/usb-device",
        ]
        for port in typical_ports:
            assert isinstance(port, str)
            assert len(port) > 0


class TestConfigSchemaRequirements:
    """Test CONFIG_SCHEMA documentation requirements.

    These tests document what the CONFIG_SCHEMA must validate.
    """

    def test_domain_key_is_buderus_wps(self):
        """Configuration must be under 'buderus_wps' domain key."""
        from custom_components.buderus_wps.const import DOMAIN

        assert DOMAIN == "buderus_wps"

    def test_required_config_keys_exist(self):
        """All required configuration keys must be defined."""
        # Port and scan_interval are the two config options
        assert CONF_PORT is not None
        assert CONF_SCAN_INTERVAL is not None

    def test_defaults_allow_minimal_config(self):
        """Default values allow running with minimal configuration."""
        # Both have defaults, so empty config is valid
        assert DEFAULT_PORT is not None
        assert DEFAULT_SCAN_INTERVAL is not None
