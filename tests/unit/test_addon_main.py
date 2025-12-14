"""Unit tests for addon main service."""

import logging
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# Add addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "addon"
sys.path.insert(0, str(addon_path))

from buderus_wps_addon.main import (  # noqa: E402
    BuderusService,
    setup_logging,
    INITIAL_RETRY_DELAY,
    MAX_RETRY_DELAY,
    RETRY_BACKOFF_FACTOR,
)
from buderus_wps_addon.config import AddonConfig


@pytest.fixture
def valid_config() -> AddonConfig:
    """Create a valid test configuration."""
    return AddonConfig(
        serial_device="/dev/ttyACM0",
        mqtt_host="core-mosquitto",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        scan_interval=60,
        log_level="info",
    )


@pytest.fixture
def mock_mqtt_bridge() -> MagicMock:
    """Create a mock MQTT bridge."""
    bridge = MagicMock()
    bridge.publish_state = MagicMock()
    bridge.publish_availability = MagicMock()
    bridge.connect = MagicMock()
    bridge.disconnect = MagicMock()
    return bridge


class TestBuderusService:
    """Test BuderusService class."""

    def test_init(self, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock) -> None:
        """Service should initialize with config."""
        service = BuderusService(valid_config, mock_mqtt_bridge)
        assert service.config == valid_config
        assert service.mqtt_bridge is mock_mqtt_bridge
        assert service.adapter is None
        assert service.client is None
        assert service._running is False

    @patch("buderus_wps_addon.main.get_default_sensor_map")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    def test_connect_success(
        self,
        mock_client_class: MagicMock,
        mock_adapter_class: MagicMock,
        mock_broadcast_class: MagicMock,
        mock_menu_class: MagicMock,
        mock_sensor_map: MagicMock,
        valid_config: AddonConfig,
        mock_mqtt_bridge: MagicMock,
    ) -> None:
        """Connect should return True on success."""
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        service = BuderusService(valid_config, mock_mqtt_bridge)
        result = service.connect()

        assert result is True
        mock_adapter_class.assert_called_once_with(port="/dev/ttyACM0")
        mock_adapter.open.assert_called_once()
        assert service.adapter is mock_adapter
        assert service.client is not None

    @patch("buderus_wps_addon.main.USBtinAdapter")
    def test_connect_file_not_found(
        self, mock_adapter_class: MagicMock, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock
    ) -> None:
        """Connect should return False when device not found."""
        mock_adapter_class.side_effect = FileNotFoundError("Device not found")

        service = BuderusService(valid_config, mock_mqtt_bridge)
        result = service.connect()

        assert result is False
        assert service.adapter is None
        assert service.client is None

    @patch("buderus_wps_addon.main.USBtinAdapter")
    def test_connect_permission_error(
        self, mock_adapter_class: MagicMock, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock
    ) -> None:
        """Connect should return False when permission denied."""
        mock_adapter = MagicMock()
        mock_adapter.open.side_effect = PermissionError("Permission denied")
        mock_adapter_class.return_value = mock_adapter

        service = BuderusService(valid_config, mock_mqtt_bridge)
        result = service.connect()

        assert result is False

    @patch("buderus_wps_addon.main.USBtinAdapter")
    def test_connect_generic_error(
        self, mock_adapter_class: MagicMock, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock
    ) -> None:
        """Connect should return False on generic error."""
        mock_adapter_class.side_effect = Exception("Unknown error")

        service = BuderusService(valid_config, mock_mqtt_bridge)
        result = service.connect()

        assert result is False

    @patch("buderus_wps_addon.main.get_default_sensor_map")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    def test_disconnect(
        self,
        mock_client_class: MagicMock,
        mock_adapter_class: MagicMock,
        mock_broadcast_class: MagicMock,
        mock_menu_class: MagicMock,
        mock_sensor_map: MagicMock,
        valid_config: AddonConfig,
        mock_mqtt_bridge: MagicMock,
    ) -> None:
        """Disconnect should close adapter."""
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        service = BuderusService(valid_config, mock_mqtt_bridge)
        service.connect()
        service.disconnect()

        mock_adapter.close.assert_called_once()
        assert service.adapter is None
        assert service.client is None

    def test_disconnect_when_not_connected(self, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock) -> None:
        """Disconnect should be safe when not connected."""
        service = BuderusService(valid_config, mock_mqtt_bridge)
        service.disconnect()  # Should not raise
        assert service.adapter is None

    @patch("buderus_wps_addon.main.get_default_sensor_map")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    def test_is_connected_true(
        self,
        mock_client_class: MagicMock,
        mock_adapter_class: MagicMock,
        mock_broadcast_class: MagicMock,
        mock_menu_class: MagicMock,
        mock_sensor_map: MagicMock,
        valid_config: AddonConfig,
        mock_mqtt_bridge: MagicMock,
    ) -> None:
        """is_connected should return True when connected."""
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        service = BuderusService(valid_config, mock_mqtt_bridge)
        service.connect()

        assert service.is_connected() is True

    def test_is_connected_false(self, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock) -> None:
        """is_connected should return False when not connected."""
        service = BuderusService(valid_config, mock_mqtt_bridge)
        assert service.is_connected() is False

    @patch("buderus_wps_addon.main.get_default_sensor_map")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    def test_check_connection_success(
        self,
        mock_client_class: MagicMock,
        mock_adapter_class: MagicMock,
        mock_broadcast_class: MagicMock,
        mock_menu_class: MagicMock,
        mock_sensor_map: MagicMock,
        valid_config: AddonConfig,
        mock_mqtt_bridge: MagicMock,
    ) -> None:
        """check_connection should return True when serial is open."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_adapter = MagicMock()
        mock_adapter._serial = mock_serial
        mock_adapter_class.return_value = mock_adapter

        service = BuderusService(valid_config, mock_mqtt_bridge)
        service.connect()
        result = service.check_connection()

        assert result is True

    @patch("buderus_wps_addon.main.get_default_sensor_map")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    def test_check_connection_closed(
        self,
        mock_client_class: MagicMock,
        mock_adapter_class: MagicMock,
        mock_broadcast_class: MagicMock,
        mock_menu_class: MagicMock,
        mock_sensor_map: MagicMock,
        valid_config: AddonConfig,
        mock_mqtt_bridge: MagicMock,
    ) -> None:
        """check_connection should return False when serial is closed."""
        mock_serial = MagicMock()
        mock_serial.is_open = False
        mock_adapter = MagicMock()
        mock_adapter._serial = mock_serial
        mock_adapter_class.return_value = mock_adapter

        service = BuderusService(valid_config, mock_mqtt_bridge)
        service.connect()
        result = service.check_connection()

        assert result is False

    def test_check_connection_not_connected(self, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock) -> None:
        """check_connection should return False when not connected."""
        service = BuderusService(valid_config, mock_mqtt_bridge)
        assert service.check_connection() is False

    @patch("buderus_wps_addon.main.time.sleep")
    @patch("buderus_wps_addon.main.get_default_sensor_map")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    def test_reconnect_with_backoff_success(
        self,
        mock_client_class: MagicMock,
        mock_adapter_class: MagicMock,
        mock_broadcast_class: MagicMock,
        mock_menu_class: MagicMock,
        mock_sensor_map: MagicMock,
        mock_sleep: MagicMock,
        valid_config: AddonConfig,
        mock_mqtt_bridge: MagicMock,
    ) -> None:
        """reconnect_with_backoff should succeed and reset delay."""
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        service = BuderusService(valid_config, mock_mqtt_bridge)
        service._retry_delay = 60.0  # Simulate previous failures

        result = service.reconnect_with_backoff()

        assert result is True
        assert service._retry_delay == INITIAL_RETRY_DELAY
        mock_sleep.assert_called_once_with(60.0)

    @patch("buderus_wps_addon.main.time.sleep")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    def test_reconnect_with_backoff_failure(
        self, mock_adapter_class: MagicMock, mock_sleep: MagicMock, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock
    ) -> None:
        """reconnect_with_backoff should increase delay on failure."""
        mock_adapter_class.side_effect = Exception("Failed")

        service = BuderusService(valid_config, mock_mqtt_bridge)
        initial_delay = service._retry_delay

        result = service.reconnect_with_backoff()

        assert result is False
        assert service._retry_delay == initial_delay * RETRY_BACKOFF_FACTOR

    @patch("buderus_wps_addon.main.time.sleep")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    def test_reconnect_delay_capped_at_max(
        self, mock_adapter_class: MagicMock, mock_sleep: MagicMock, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock
    ) -> None:
        """reconnect_with_backoff should cap delay at MAX_RETRY_DELAY."""
        mock_adapter_class.side_effect = Exception("Failed")

        service = BuderusService(valid_config, mock_mqtt_bridge)
        service._retry_delay = MAX_RETRY_DELAY  # Already at max

        service.reconnect_with_backoff()

        assert service._retry_delay == MAX_RETRY_DELAY

    def test_stop(self, valid_config: AddonConfig, mock_mqtt_bridge: MagicMock) -> None:
        """stop should set running to False."""
        service = BuderusService(valid_config, mock_mqtt_bridge)
        service._running = True
        service.stop()
        assert service._running is False
        mock_mqtt_bridge.disconnect.assert_called_once()


class TestSetupLogging:
    """Test logging setup."""

    @pytest.fixture(autouse=True)
    def reset_logging(self):
        """Reset logging configuration before each test."""
        # Remove all handlers from root logger
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)  # Reset to default
        yield
        # Cleanup after test
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_logging_debug(self) -> None:
        """Debug level should be set correctly."""
        setup_logging("debug")
        # Root logger level is set by basicConfig
        assert logging.getLogger().level == logging.DEBUG

    def test_setup_logging_info(self) -> None:
        """Info level should be set correctly."""
        setup_logging("info")
        assert logging.getLogger().level == logging.INFO

    def test_setup_logging_warning(self) -> None:
        """Warning level should be set correctly."""
        setup_logging("warning")
        assert logging.getLogger().level == logging.WARNING

    def test_setup_logging_error(self) -> None:
        """Error level should be set correctly."""
        setup_logging("error")
        assert logging.getLogger().level == logging.ERROR

    def test_setup_logging_invalid_defaults_to_info(self) -> None:
        """Invalid level should default to INFO."""
        setup_logging("invalid")
        assert logging.getLogger().level == logging.INFO

    def test_setup_logging_case_insensitive(self) -> None:
        """Log levels should be case insensitive."""
        # Remove handlers between calls
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

        # Need to reset handlers again
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("Info")
        assert logging.getLogger().level == logging.INFO


class TestBackoffConstants:
    """Test backoff constant values."""

    def test_initial_retry_delay(self) -> None:
        """Initial retry delay should be reasonable."""
        assert INITIAL_RETRY_DELAY == 5.0

    def test_max_retry_delay(self) -> None:
        """Max retry delay should be 5 minutes."""
        assert MAX_RETRY_DELAY == 300.0

    def test_backoff_factor(self) -> None:
        """Backoff factor should double the delay."""
        assert RETRY_BACKOFF_FACTOR == 2.0
