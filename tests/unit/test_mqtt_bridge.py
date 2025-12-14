"""Unit tests for MQTT bridge functionality."""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# Add addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "addon"
sys.path.insert(0, str(addon_path))

from buderus_wps_addon.config import AddonConfig
from buderus_wps_addon.entity_config import ALL_ENTITIES


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
def config_with_auth() -> AddonConfig:
    """Create a configuration with MQTT authentication."""
    return AddonConfig(
        serial_device="/dev/ttyACM0",
        mqtt_host="mqtt.example.com",
        mqtt_port=8883,
        mqtt_username="testuser",
        mqtt_password="testpass",
        scan_interval=30,
        log_level="debug",
    )


@pytest.fixture
def mock_mqtt_client():
    """Create a mock MQTT client."""
    with patch("buderus_wps_addon.mqtt_bridge.mqtt.Client") as mock_class:
        mock_client = MagicMock()
        mock_class.return_value = mock_client
        yield mock_client


class TestMQTTBridgeInit:
    """Test MQTTBridge initialization."""

    def test_init_creates_client(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """MQTTBridge should create MQTT client on init."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        assert bridge.config == valid_config

    def test_init_sets_callbacks(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """MQTTBridge should set up client callbacks."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)

        # Callbacks are set on the mock
        assert mock_mqtt_client.on_connect is not None
        assert mock_mqtt_client.on_disconnect is not None

    def test_init_sets_will(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """MQTTBridge should set Last Will and Testament."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)

        mock_mqtt_client.will_set.assert_called_once()
        # Check that will_set was called with offline payload
        call_kwargs = mock_mqtt_client.will_set.call_args.kwargs
        assert call_kwargs.get("payload") == "offline"


class TestMQTTBridgeConnection:
    """Test MQTT connection handling."""

    def test_connect_without_auth(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Connect should work without authentication."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge.connect()

        mock_mqtt_client.connect.assert_called_once_with("core-mosquitto", 1883, keepalive=60)
        mock_mqtt_client.username_pw_set.assert_not_called()

    def test_connect_with_auth(self, mock_mqtt_client: MagicMock, config_with_auth: AddonConfig) -> None:
        """Connect should set credentials when provided."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(config_with_auth)
        bridge.connect()

        mock_mqtt_client.username_pw_set.assert_called_once_with("testuser", "testpass")
        mock_mqtt_client.connect.assert_called_once_with("mqtt.example.com", 8883, keepalive=60)

    def test_connect_starts_loop(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Connect should start the MQTT event loop."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge.connect()

        mock_mqtt_client.loop_start.assert_called_once()

    def test_disconnect(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Disconnect should stop loop and disconnect client."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge.disconnect()

        mock_mqtt_client.loop_stop.assert_called_once()
        mock_mqtt_client.disconnect.assert_called_once()


class TestMQTTDiscoveryPublish:
    """Test MQTT Discovery message publishing."""

    def test_publish_discovery_all_entities(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """publish_discovery should publish config for all entities."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        # Access the internal client (which is the mock)
        bridge._client.publish.reset_mock()

        bridge.publish_discovery()

        # Should publish for all entities
        assert bridge._client.publish.call_count == len(ALL_ENTITIES)

    def test_discovery_messages_are_retained(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Discovery messages should be retained."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.publish.reset_mock()

        bridge.publish_discovery()

        # All publish calls should have retain=True
        for call_item in bridge._client.publish.call_args_list:
            assert call_item.kwargs.get("retain") is True

    def test_discovery_topic_format(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Discovery topics should follow HA format."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.publish.reset_mock()

        bridge.publish_discovery()

        # Extract topics from calls
        topics = [call_item.kwargs.get("topic", call_item.args[0] if call_item.args else "")
                  for call_item in bridge._client.publish.call_args_list]

        # All topics should start with homeassistant/
        for topic in topics:
            assert topic.startswith("homeassistant/"), f"Topic {topic} doesn't start with homeassistant/"
            assert "/config" in topic, f"Topic {topic} doesn't contain /config"


class TestMQTTStatePublish:
    """Test MQTT state publishing."""

    def test_publish_sensor_state(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """publish_state should publish sensor value to state topic."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.publish.reset_mock()

        bridge.publish_state("outdoor_temp", 15.5)

        bridge._client.publish.assert_called_once()
        call_kwargs = bridge._client.publish.call_args.kwargs
        assert "outdoor_temp" in call_kwargs.get("topic", "")
        assert "state" in call_kwargs.get("topic", "")

    def test_state_not_retained(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """State messages should NOT be retained."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.publish.reset_mock()

        bridge.publish_state("outdoor_temp", 15.5)

        call_kwargs = bridge._client.publish.call_args.kwargs
        assert call_kwargs.get("retain") is False

    def test_publish_binary_sensor_on(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Binary sensor should publish ON/OFF."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.publish.reset_mock()

        bridge.publish_state("compressor", True)

        call_kwargs = bridge._client.publish.call_args.kwargs
        assert call_kwargs.get("payload") == "ON"

    def test_publish_binary_sensor_off(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Binary sensor should publish ON/OFF."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.publish.reset_mock()

        bridge.publish_state("compressor", False)

        call_kwargs = bridge._client.publish.call_args.kwargs
        assert call_kwargs.get("payload") == "OFF"

    def test_publish_float_formatted(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Float values should be formatted with one decimal."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.publish.reset_mock()

        bridge.publish_state("outdoor_temp", 15.567)

        call_kwargs = bridge._client.publish.call_args.kwargs
        assert call_kwargs.get("payload") == "15.6"


class TestMQTTAvailability:
    """Test availability topic publishing."""

    def test_publish_online(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """publish_availability should publish online status."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        mock_mqtt_client.publish.reset_mock()

        bridge.publish_availability(True)

        mock_mqtt_client.publish.assert_called_once()
        call_kwargs = mock_mqtt_client.publish.call_args.kwargs
        assert "status" in call_kwargs.get("topic", "")
        assert call_kwargs.get("payload") == "online"

    def test_publish_offline(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """publish_availability should publish offline status."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        mock_mqtt_client.publish.reset_mock()

        bridge.publish_availability(False)

        call_kwargs = mock_mqtt_client.publish.call_args.kwargs
        assert call_kwargs.get("payload") == "offline"

    def test_availability_retained(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """Availability messages should be retained."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        mock_mqtt_client.publish.reset_mock()

        bridge.publish_availability(True)

        call_kwargs = mock_mqtt_client.publish.call_args.kwargs
        assert call_kwargs.get("retain") is True


class TestHAStatusSubscription:
    """Test Home Assistant status topic subscription."""

    def test_subscribes_to_ha_status(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """MQTTBridge should subscribe to HA status for re-discovery."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.subscribe.reset_mock()

        # Simulate on_connect callback - pass the internal client
        bridge._on_connect(bridge._client, None, None, 0)

        # Should subscribe to homeassistant/status
        bridge._client.subscribe.assert_called()
        subscribe_calls = [str(c) for c in bridge._client.subscribe.call_args_list]
        assert any("homeassistant/status" in c for c in subscribe_calls)


class TestOnMessageHandler:
    """Test MQTT message handler."""

    def test_ha_online_triggers_discovery(self, mock_mqtt_client: MagicMock, valid_config: AddonConfig) -> None:
        """HA coming online should trigger re-discovery."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        bridge._client.publish.reset_mock()

        # Create a mock message
        mock_msg = MagicMock()
        mock_msg.topic = "homeassistant/status"
        mock_msg.payload = b"online"

        bridge._on_message(bridge._client, None, mock_msg)

        # Should have published discovery (12 entities) + availability (1)
        assert bridge._client.publish.call_count == len(ALL_ENTITIES) + 1


class TestCommandTopicSubscription:
    """Test command topic subscription."""

    def test_subscribes_to_command_topics_on_connect(
        self, mock_mqtt_client: MagicMock, valid_config: AddonConfig
    ) -> None:
        """Should subscribe to command topics for controllable entities."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge
        from buderus_wps_addon.entity_config import get_controllable_entities

        bridge = MQTTBridge(valid_config)
        bridge._client.subscribe.reset_mock()

        # Simulate on_connect callback
        bridge._on_connect(bridge._client, None, None, 0)

        # Get expected command topics
        controllable = get_controllable_entities()
        expected_topics = [e.command_topic for e in controllable if e.command_topic]

        # Should have subscribed to HA status + all command topics
        subscribe_calls = [str(c) for c in bridge._client.subscribe.call_args_list]

        # Verify command topics are subscribed
        for topic in expected_topics:
            assert any(topic in c for c in subscribe_calls), f"Missing subscription to {topic}"


class TestCommandHandler:
    """Test command handler functionality."""

    def test_command_handler_called_on_set_message(
        self, mock_mqtt_client: MagicMock, valid_config: AddonConfig
    ) -> None:
        """Command handler should be called when /set message received."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        handler = MagicMock()
        bridge = MQTTBridge(valid_config, command_handler=handler)

        # Create a command message
        mock_msg = MagicMock()
        mock_msg.topic = "buderus_wps/switch/holiday_mode/set"
        mock_msg.payload = b"ON"

        bridge._on_message(bridge._client, None, mock_msg)

        handler.assert_called_once()
        entity, value = handler.call_args[0]
        assert entity.entity_id == "holiday_mode"
        assert value == "ON"

    def test_command_handler_with_select_entity(
        self, mock_mqtt_client: MagicMock, valid_config: AddonConfig
    ) -> None:
        """Command handler should work with select entities."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        handler = MagicMock()
        bridge = MQTTBridge(valid_config, command_handler=handler)

        mock_msg = MagicMock()
        mock_msg.topic = "buderus_wps/select/heating_season_mode/set"
        mock_msg.payload = b"Winter"

        bridge._on_message(bridge._client, None, mock_msg)

        handler.assert_called_once()
        entity, value = handler.call_args[0]
        assert entity.entity_id == "heating_season_mode"
        assert value == "Winter"

    def test_no_handler_logs_warning(
        self, mock_mqtt_client: MagicMock, valid_config: AddonConfig, caplog
    ) -> None:
        """Should log warning if no handler registered."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge
        import logging

        bridge = MQTTBridge(valid_config)  # No handler

        mock_msg = MagicMock()
        mock_msg.topic = "buderus_wps/switch/holiday_mode/set"
        mock_msg.payload = b"ON"

        with caplog.at_level(logging.WARNING):
            bridge._on_message(bridge._client, None, mock_msg)

        assert "No command handler registered" in caplog.text

    def test_unknown_entity_logs_warning(
        self, mock_mqtt_client: MagicMock, valid_config: AddonConfig, caplog
    ) -> None:
        """Should log warning for unknown entity in command."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge
        import logging

        handler = MagicMock()
        bridge = MQTTBridge(valid_config, command_handler=handler)

        mock_msg = MagicMock()
        mock_msg.topic = "buderus_wps/switch/unknown_entity/set"
        mock_msg.payload = b"ON"

        with caplog.at_level(logging.WARNING):
            bridge._on_message(bridge._client, None, mock_msg)

        assert "Unknown entity" in caplog.text
        handler.assert_not_called()

    def test_set_command_handler_method(
        self, mock_mqtt_client: MagicMock, valid_config: AddonConfig
    ) -> None:
        """set_command_handler should update handler."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge

        bridge = MQTTBridge(valid_config)
        assert bridge._command_handler is None

        handler = MagicMock()
        bridge.set_command_handler(handler)

        assert bridge._command_handler is handler

    def test_handler_exception_logged(
        self, mock_mqtt_client: MagicMock, valid_config: AddonConfig, caplog
    ) -> None:
        """Handler exceptions should be logged."""
        from buderus_wps_addon.mqtt_bridge import MQTTBridge
        import logging

        handler = MagicMock(side_effect=Exception("Handler error"))
        bridge = MQTTBridge(valid_config, command_handler=handler)

        mock_msg = MagicMock()
        mock_msg.topic = "buderus_wps/switch/holiday_mode/set"
        mock_msg.payload = b"ON"

        with caplog.at_level(logging.ERROR):
            bridge._on_message(bridge._client, None, mock_msg)

        assert "Command handler failed" in caplog.text
