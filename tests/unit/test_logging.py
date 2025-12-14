"""Unit tests for logging configuration.

Tests the logging setup and format for the add-on service.
"""

import logging
import pytest
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "addon"
sys.path.insert(0, str(addon_path))


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    root_logger.setLevel(logging.WARNING)
    yield
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


class TestSetupLogging:
    """Test logging setup function."""

    def test_setup_logging_debug_level(self) -> None:
        """DEBUG level should be configured correctly."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("debug")
        assert logging.getLogger().level == logging.DEBUG

    def test_setup_logging_info_level(self) -> None:
        """INFO level should be configured correctly."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("info")
        assert logging.getLogger().level == logging.INFO

    def test_setup_logging_warning_level(self) -> None:
        """WARNING level should be configured correctly."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("warning")
        assert logging.getLogger().level == logging.WARNING

    def test_setup_logging_error_level(self) -> None:
        """ERROR level should be configured correctly."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("error")
        assert logging.getLogger().level == logging.ERROR

    def test_setup_logging_invalid_defaults_info(self) -> None:
        """Invalid log level should default to INFO."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("invalid")
        assert logging.getLogger().level == logging.INFO

    def test_setup_logging_case_insensitive(self) -> None:
        """Log level should be case insensitive."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)

        setup_logging("Info")
        assert logging.getLogger().level == logging.INFO


class TestLogFormat:
    """Test log message format."""

    def test_log_format_includes_timestamp(self) -> None:
        """Log format should include timestamp."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("info")

        # Get the handler and check format
        handlers = logging.getLogger().handlers
        assert len(handlers) > 0

        handler = handlers[0]
        assert handler.formatter is not None
        format_str = handler.formatter._fmt
        assert "%(asctime)s" in format_str

    def test_log_format_includes_level(self) -> None:
        """Log format should include log level."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("info")

        handlers = logging.getLogger().handlers
        assert len(handlers) > 0

        handler = handlers[0]
        assert handler.formatter is not None
        format_str = handler.formatter._fmt
        assert "%(levelname)s" in format_str

    def test_log_format_includes_logger_name(self) -> None:
        """Log format should include logger name."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("info")

        handlers = logging.getLogger().handlers
        assert len(handlers) > 0

        handler = handlers[0]
        assert handler.formatter is not None
        format_str = handler.formatter._fmt
        assert "%(name)s" in format_str

    def test_log_format_includes_message(self) -> None:
        """Log format should include message."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("info")

        handlers = logging.getLogger().handlers
        assert len(handlers) > 0

        handler = handlers[0]
        assert handler.formatter is not None
        format_str = handler.formatter._fmt
        assert "%(message)s" in format_str


@pytest.fixture
def valid_config():
    """Create a valid test configuration."""
    from buderus_wps_addon.config import AddonConfig
    return AddonConfig(
        serial_device="/dev/ttyACM0",
        mqtt_host="core-mosquitto",
        mqtt_port=1883,
        mqtt_username=None,
        mqtt_password=None,
        scan_interval=60,
        log_level="info",
    )


class TestLogVerbosity:
    """Test log verbosity at different levels."""

    def test_debug_level_set_correctly(self) -> None:
        """DEBUG level should be set on root logger."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("debug")
        assert logging.getLogger().level == logging.DEBUG

    def test_info_level_set_correctly(self) -> None:
        """INFO level should be set on root logger."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("info")
        assert logging.getLogger().level == logging.INFO

    def test_warning_level_set_correctly(self) -> None:
        """WARNING level should be set on root logger."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("warning")
        assert logging.getLogger().level == logging.WARNING

    def test_debug_logger_respects_level(self) -> None:
        """Logger at DEBUG level should have DEBUG effective level."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("debug")
        test_logger = logging.getLogger("test_debug_effective")
        assert test_logger.getEffectiveLevel() == logging.DEBUG

    def test_info_logger_respects_level(self) -> None:
        """Logger at INFO level should have INFO effective level."""
        from buderus_wps_addon.main import setup_logging

        setup_logging("info")
        test_logger = logging.getLogger("test_info_effective")
        assert test_logger.getEffectiveLevel() == logging.INFO


class TestConnectionLogging:
    """Test connection-related log messages."""

    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.get_default_sensor_map")
    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    def test_connection_success_logged(
        self,
        mock_mqtt: MagicMock,
        mock_sensor_map: MagicMock,
        mock_menu: MagicMock,
        mock_broadcast: MagicMock,
        mock_client: MagicMock,
        mock_adapter_class: MagicMock,
        valid_config,
        caplog,
    ) -> None:
        """Successful connection should be logged."""
        from buderus_wps_addon.main import BuderusService
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        mqtt_bridge = MQTTBridge(valid_config)
        service = BuderusService(valid_config, mqtt_bridge)

        with caplog.at_level(logging.INFO):
            service.connect()

        assert "Successfully connected" in caplog.text

    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    def test_device_not_found_logged(
        self,
        mock_mqtt: MagicMock,
        mock_adapter_class: MagicMock,
        valid_config,
        caplog,
    ) -> None:
        """Device not found should be logged."""
        from buderus_wps_addon.main import BuderusService
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        mock_adapter_class.side_effect = FileNotFoundError("Device not found")

        mqtt_bridge = MQTTBridge(valid_config)
        service = BuderusService(valid_config, mqtt_bridge)

        with caplog.at_level(logging.ERROR):
            service.connect()

        assert "not found" in caplog.text.lower()

    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    def test_permission_error_logged(
        self,
        mock_mqtt: MagicMock,
        mock_adapter_class: MagicMock,
        valid_config,
        caplog,
    ) -> None:
        """Permission error should be logged with helpful message."""
        from buderus_wps_addon.main import BuderusService
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        mock_adapter = MagicMock()
        mock_adapter.open.side_effect = PermissionError("Permission denied")
        mock_adapter_class.return_value = mock_adapter

        mqtt_bridge = MQTTBridge(valid_config)
        service = BuderusService(valid_config, mqtt_bridge)

        with caplog.at_level(logging.ERROR):
            service.connect()

        assert "Permission denied" in caplog.text


class TestMQTTLogging:
    """Test MQTT-related log messages."""

    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    def test_mqtt_connection_logged(
        self, mock_mqtt_class: MagicMock, valid_config, caplog
    ) -> None:
        """MQTT connection should be logged."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        mock_mqtt_client = MagicMock()
        mock_mqtt_class.return_value = mock_mqtt_client

        bridge = MQTTBridge(valid_config)

        with caplog.at_level(logging.INFO):
            bridge.connect()

        assert "Connecting to MQTT" in caplog.text

    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    def test_mqtt_connected_logged(
        self, mock_mqtt_class: MagicMock, valid_config, caplog
    ) -> None:
        """MQTT connected status should be logged."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        mock_mqtt_client = MagicMock()
        mock_mqtt_class.return_value = mock_mqtt_client

        bridge = MQTTBridge(valid_config)

        with caplog.at_level(logging.INFO):
            bridge._on_connect(bridge._client, None, None, 0)

        assert "Connected to MQTT" in caplog.text

    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    def test_mqtt_disconnected_logged(
        self, mock_mqtt_class: MagicMock, valid_config, caplog
    ) -> None:
        """MQTT disconnection should be logged."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        mock_mqtt_client = MagicMock()
        mock_mqtt_class.return_value = mock_mqtt_client

        bridge = MQTTBridge(valid_config)

        with caplog.at_level(logging.WARNING):
            bridge._on_disconnect(bridge._client, None, 0)

        assert "Disconnected" in caplog.text


class TestCommandLogging:
    """Test command execution log messages."""

    def test_command_execution_logged(self, caplog) -> None:
        """Command execution should be logged."""
        from buderus_wps_addon.command_queue import CommandQueue, Command
        from buderus_wps_addon.entity_config import get_entity_by_id

        mock_client = MagicMock()
        mock_client.write_parameter = MagicMock(return_value=True)

        queue = CommandQueue(mock_client)
        entity = get_entity_by_id("heating_season_mode")
        cmd = Command(entity=entity, value="Winter")

        with caplog.at_level(logging.INFO):
            queue._execute_command(cmd)

        assert "Executing command" in caplog.text

    def test_command_failure_logged(self, caplog) -> None:
        """Command failure should be logged."""
        from buderus_wps_addon.command_queue import CommandQueue, Command
        from buderus_wps_addon.entity_config import get_entity_by_id

        mock_client = MagicMock()
        mock_client.write_parameter = MagicMock(side_effect=Exception("CAN timeout"))

        queue = CommandQueue(mock_client)
        entity = get_entity_by_id("heating_season_mode")
        cmd = Command(entity=entity, value="Winter")

        with caplog.at_level(logging.ERROR):
            queue._execute_command(cmd)

        assert "failed" in caplog.text.lower()

    def test_command_timeout_logged(self, caplog) -> None:
        """Command timeout should be logged."""
        import time
        from buderus_wps_addon.command_queue import (
            CommandQueue,
            Command,
            COMMAND_TIMEOUT,
        )
        from buderus_wps_addon.entity_config import get_entity_by_id

        mock_client = MagicMock()
        queue = CommandQueue(mock_client)
        entity = get_entity_by_id("heating_season_mode")

        # Create an expired command
        cmd = Command(entity=entity, value="Winter")
        cmd.timestamp = time.time() - COMMAND_TIMEOUT - 1

        with caplog.at_level(logging.WARNING):
            queue._execute_command(cmd)

        assert "expired" in caplog.text.lower()


class TestDebugLogging:
    """Test debug-level log messages."""

    def test_sensor_publish_debug(self, valid_config, caplog) -> None:
        """Sensor state publishing should be logged at debug level."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        with patch("buderus_wps_addon.mqtt_bridge.mqtt.Client"):
            bridge = MQTTBridge(valid_config)

            with caplog.at_level(logging.DEBUG):
                bridge.publish_state("outdoor_temp", 15.5)

            assert "Published state" in caplog.text

    def test_discovery_publish_debug(self, valid_config, caplog) -> None:
        """Discovery publishing should be logged at debug level."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        with patch("buderus_wps_addon.mqtt_bridge.mqtt.Client"):
            bridge = MQTTBridge(valid_config)

            with caplog.at_level(logging.DEBUG):
                bridge.publish_discovery()

            assert "Published discovery" in caplog.text
