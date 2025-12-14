"""Integration tests for control entity functionality.

Tests the end-to-end flow from MQTT command to heat pump parameter write.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "addon"
sys.path.insert(0, str(addon_path))

from buderus_wps_addon.config import AddonConfig
from buderus_wps_addon.entity_config import (
    EntityConfig,
    get_entity_by_id,
    get_controllable_entities,
    map_option_to_value,
    map_value_to_option,
)


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


class TestControlEntityDefinitions:
    """Test that control entities are properly defined."""

    def test_controllable_entities_exist(self) -> None:
        """Should have controllable entities defined."""
        controllable = get_controllable_entities()
        assert len(controllable) > 0

    def test_heating_season_mode_entity(self) -> None:
        """heating_season_mode should be properly configured."""
        entity = get_entity_by_id("heating_season_mode")
        assert entity is not None
        assert entity.entity_type == "select"
        assert entity.parameter_name == "HEATING_SEASON_MODE"
        assert entity.options == ["Winter", "Automatic", "Summer"]
        assert entity.command_topic is not None

    def test_dhw_program_mode_entity(self) -> None:
        """dhw_program_mode should be properly configured."""
        entity = get_entity_by_id("dhw_program_mode")
        assert entity is not None
        assert entity.entity_type == "select"
        assert entity.parameter_name == "DHW_PROGRAM_MODE"
        assert entity.options == ["Automatic", "Always On", "Always Off"]

    def test_holiday_mode_entity(self) -> None:
        """holiday_mode should be properly configured."""
        entity = get_entity_by_id("holiday_mode")
        assert entity is not None
        assert entity.entity_type == "switch"
        assert entity.parameter_name == "HOLIDAY_ACTIVE_GLOBAL"

    def test_extra_dhw_duration_entity(self) -> None:
        """extra_dhw_duration should be properly configured."""
        entity = get_entity_by_id("extra_dhw_duration")
        assert entity is not None
        assert entity.entity_type == "number"
        assert entity.use_menu_api is True
        assert entity.min_value == 0
        assert entity.max_value == 48

    def test_extra_dhw_target_entity(self) -> None:
        """extra_dhw_target should be properly configured."""
        entity = get_entity_by_id("extra_dhw_target")
        assert entity is not None
        assert entity.entity_type == "number"
        assert entity.use_menu_api is True
        assert entity.min_value == 50.0
        assert entity.max_value == 65.0


class TestValueMappings:
    """Test value mapping between HA and heat pump."""

    def test_heating_season_mode_mapping(self) -> None:
        """heating_season_mode should map correctly."""
        assert map_option_to_value("heating_season_mode", "Winter") == 0
        assert map_option_to_value("heating_season_mode", "Automatic") == 1
        assert map_option_to_value("heating_season_mode", "Summer") == 2

    def test_heating_season_mode_reverse_mapping(self) -> None:
        """heating_season_mode should reverse map correctly."""
        assert map_value_to_option("heating_season_mode", 0) == "Winter"
        assert map_value_to_option("heating_season_mode", 1) == "Automatic"
        assert map_value_to_option("heating_season_mode", 2) == "Summer"

    def test_dhw_program_mode_mapping(self) -> None:
        """dhw_program_mode should map correctly."""
        assert map_option_to_value("dhw_program_mode", "Automatic") == 0
        assert map_option_to_value("dhw_program_mode", "Always On") == 1
        assert map_option_to_value("dhw_program_mode", "Always Off") == 2

    def test_dhw_program_mode_reverse_mapping(self) -> None:
        """dhw_program_mode should reverse map correctly."""
        assert map_value_to_option("dhw_program_mode", 0) == "Automatic"
        assert map_value_to_option("dhw_program_mode", 1) == "Always On"
        assert map_value_to_option("dhw_program_mode", 2) == "Always Off"

    def test_invalid_option_returns_none(self) -> None:
        """Invalid option should return None."""
        assert map_option_to_value("heating_season_mode", "Invalid") is None
        assert map_value_to_option("heating_season_mode", 99) is None


class TestEndToEndControlFlow:
    """Test end-to-end control flow from MQTT to heat pump."""

    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    def test_mqtt_to_command_queue_flow(
        self, mock_mqtt_class: MagicMock, valid_config: AddonConfig
    ) -> None:
        """MQTT message should flow through to command queue."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge
        from buderus_wps_addon.command_queue import CommandQueue, CommandStatus

        # Setup mocks
        mock_mqtt_client = MagicMock()
        mock_mqtt_class.return_value = mock_mqtt_client
        mock_heat_pump_client = MagicMock()
        mock_heat_pump_client.write_parameter = MagicMock(return_value=True)

        # Create command queue
        command_queue = CommandQueue(client=mock_heat_pump_client)

        # Create handler that enqueues to command queue
        def command_handler(entity: EntityConfig, value: str) -> None:
            command_queue.enqueue(entity, value)

        # Create MQTT bridge with handler
        mqtt_bridge = MQTTBridge(valid_config, command_handler=command_handler)

        # Simulate incoming MQTT message
        mock_msg = MagicMock()
        mock_msg.topic = "buderus_wps/select/heating_season_mode/set"
        mock_msg.payload = b"Winter"

        mqtt_bridge._on_message(mqtt_bridge._client, None, mock_msg)

        # Verify command was queued
        assert command_queue.pending_count() == 1

        # Process the command
        result = command_queue.process_one()

        # Verify write was called with correct parameters
        mock_heat_pump_client.write_parameter.assert_called_once_with(
            "HEATING_SEASON_MODE", 0  # Winter = 0
        )
        assert result.status == CommandStatus.SUCCESS

    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    def test_switch_control_flow(
        self, mock_mqtt_class: MagicMock, valid_config: AddonConfig
    ) -> None:
        """Switch entity should toggle correctly."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge
        from buderus_wps_addon.command_queue import CommandQueue, CommandStatus

        mock_mqtt_client = MagicMock()
        mock_mqtt_class.return_value = mock_mqtt_client
        mock_heat_pump_client = MagicMock()
        mock_heat_pump_client.write_parameter = MagicMock(return_value=True)

        command_queue = CommandQueue(client=mock_heat_pump_client)

        def command_handler(entity: EntityConfig, value: str) -> None:
            command_queue.enqueue(entity, value)

        mqtt_bridge = MQTTBridge(valid_config, command_handler=command_handler)

        # Test ON
        mock_msg = MagicMock()
        mock_msg.topic = "buderus_wps/switch/holiday_mode/set"
        mock_msg.payload = b"ON"

        mqtt_bridge._on_message(mqtt_bridge._client, None, mock_msg)
        result = command_queue.process_one()

        mock_heat_pump_client.write_parameter.assert_called_with(
            "HOLIDAY_ACTIVE_GLOBAL", 1
        )
        assert result.status == CommandStatus.SUCCESS

        # Test OFF
        mock_heat_pump_client.write_parameter.reset_mock()
        mock_msg.payload = b"OFF"

        mqtt_bridge._on_message(mqtt_bridge._client, None, mock_msg)
        result = command_queue.process_one()

        mock_heat_pump_client.write_parameter.assert_called_with(
            "HOLIDAY_ACTIVE_GLOBAL", 0
        )
        assert result.status == CommandStatus.SUCCESS


class TestServiceIntegration:
    """Test service-level command integration."""

    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.get_default_sensor_map")
    def test_service_processes_commands(
        self,
        mock_sensor_map: MagicMock,
        mock_menu_api: MagicMock,
        mock_broadcast: MagicMock,
        mock_client_class: MagicMock,
        mock_adapter_class: MagicMock,
        mock_mqtt_class: MagicMock,
        valid_config: AddonConfig,
    ) -> None:
        """BuderusService should process queued commands."""
        from buderus_wps_addon.main import BuderusService
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        # Setup mocks
        mock_mqtt_client = MagicMock()
        mock_mqtt_class.return_value = mock_mqtt_client

        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        mock_client = MagicMock()
        mock_client.write_parameter = MagicMock(return_value=True)
        mock_client_class.return_value = mock_client

        # Create service
        mqtt_bridge = MQTTBridge(valid_config)
        service = BuderusService(valid_config, mqtt_bridge)
        service.connect()

        # Enqueue a command via the MQTT handler
        entity = get_entity_by_id("heating_season_mode")
        service._handle_mqtt_command(entity, "Summer")

        # Verify command was queued
        assert service.command_queue.pending_count() == 1

        # Process commands (normally called in poll_and_publish)
        service.command_queue.process_one()

        # Verify write was called
        mock_client.write_parameter.assert_called_once_with(
            "HEATING_SEASON_MODE", 2  # Summer = 2
        )

    @patch("buderus_wps_addon.mqtt_bridge.mqtt.Client")
    @patch("buderus_wps_addon.main.USBtinAdapter")
    @patch("buderus_wps_addon.main.HeatPumpClient")
    @patch("buderus_wps_addon.main.BroadcastMonitor")
    @patch("buderus_wps_addon.main.MenuAPI")
    @patch("buderus_wps_addon.main.get_default_sensor_map")
    def test_service_publishes_result_state(
        self,
        mock_sensor_map: MagicMock,
        mock_menu_api: MagicMock,
        mock_broadcast: MagicMock,
        mock_client_class: MagicMock,
        mock_adapter_class: MagicMock,
        mock_mqtt_class: MagicMock,
        valid_config: AddonConfig,
    ) -> None:
        """Service should publish state after successful command."""
        from buderus_wps_addon.main import BuderusService
        from buderus_wps_addon.mqtt_bridge import MQTTBridge
        from buderus_wps_addon.command_queue import CommandResult, CommandStatus

        mock_mqtt_client = MagicMock()
        mock_mqtt_class.return_value = mock_mqtt_client

        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mqtt_bridge = MQTTBridge(valid_config)
        service = BuderusService(valid_config, mqtt_bridge)

        # Test the callback directly
        result = CommandResult(
            entity_id="heating_season_mode",
            status=CommandStatus.SUCCESS,
            value=1,  # Automatic
        )

        mqtt_bridge._client.publish.reset_mock()
        service._on_command_result(result)

        # Should have published state
        mqtt_bridge._client.publish.assert_called()
        call_kwargs = mqtt_bridge._client.publish.call_args.kwargs
        assert "heating_season_mode" in call_kwargs.get("topic", "")
        assert call_kwargs.get("payload") == "Automatic"
