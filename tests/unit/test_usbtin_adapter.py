"""Unit tests for USBtinAdapter parameter validation and basic functionality.

Tests cover:
- T021: USBtinAdapter.__init__() parameter validation
"""

import pytest
from buderus_wps.can_adapter import USBtinAdapter


class TestUSBtinAdapterInitialization:
    """Test USBtinAdapter initialization and parameter validation."""

    def test_init_with_port_only(self):
        """Initialize adapter with port path only (defaults for other params)."""
        adapter = USBtinAdapter('/dev/ttyACM0')
        assert adapter.port == '/dev/ttyACM0'
        assert adapter.baudrate == 115200  # Default
        assert adapter.timeout == 5.0  # Default

    def test_init_with_custom_baudrate(self):
        """Initialize adapter with custom baud rate."""
        adapter = USBtinAdapter('/dev/ttyACM0', baudrate=57600)
        assert adapter.baudrate == 57600

    def test_init_with_custom_timeout(self):
        """Initialize adapter with custom timeout."""
        adapter = USBtinAdapter('/dev/ttyACM0', timeout=10.0)
        assert adapter.timeout == 10.0

    def test_init_with_all_parameters(self):
        """Initialize adapter with all parameters specified."""
        adapter = USBtinAdapter('/dev/ttyUSB0', baudrate=9600, timeout=2.5)
        assert adapter.port == '/dev/ttyUSB0'
        assert adapter.baudrate == 9600
        assert adapter.timeout == 2.5

    def test_init_empty_port_path(self):
        """Initialize adapter with empty port path (invalid)."""
        with pytest.raises(ValueError, match="Port path cannot be empty"):
            USBtinAdapter('')

    def test_init_invalid_baudrate_zero(self):
        """Initialize adapter with zero baud rate (invalid)."""
        with pytest.raises(ValueError, match="Baudrate must be positive"):
            USBtinAdapter('/dev/ttyACM0', baudrate=0)

    def test_init_invalid_baudrate_negative(self):
        """Initialize adapter with negative baud rate (invalid)."""
        with pytest.raises(ValueError, match="Baudrate must be positive"):
            USBtinAdapter('/dev/ttyACM0', baudrate=-115200)

    def test_init_invalid_timeout_zero(self):
        """Initialize adapter with zero timeout (invalid)."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            USBtinAdapter('/dev/ttyACM0', timeout=0.0)

    def test_init_invalid_timeout_negative(self):
        """Initialize adapter with negative timeout (invalid)."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            USBtinAdapter('/dev/ttyACM0', timeout=-5.0)

    def test_init_timeout_too_small(self):
        """Initialize adapter with timeout below minimum (0.1s)."""
        with pytest.raises(ValueError, match="Timeout must be at least 0.1 seconds"):
            USBtinAdapter('/dev/ttyACM0', timeout=0.05)

    def test_init_timeout_too_large(self):
        """Initialize adapter with timeout above maximum (60s)."""
        with pytest.raises(ValueError, match="Timeout must not exceed 60 seconds"):
            USBtinAdapter('/dev/ttyACM0', timeout=61.0)

    def test_init_state_is_closed(self):
        """Adapter should be in closed state after initialization."""
        adapter = USBtinAdapter('/dev/ttyACM0')
        assert adapter.is_open is False

    def test_init_does_not_auto_connect(self):
        """Initialization should not automatically open connection."""
        adapter = USBtinAdapter('/dev/ttyACM0')
        assert adapter.is_open is False
        # This test just verifies state - actual serial port not opened
