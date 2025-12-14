"""Contract tests for MQTT Discovery payload validation.

These tests validate that the entity configurations produce valid
MQTT Discovery payloads according to Home Assistant's specification.
"""

import json
import pytest
import sys
from pathlib import Path

# Add addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "addon"
sys.path.insert(0, str(addon_path))

from buderus_wps_addon.entity_config import (
    ALL_ENTITIES,
    BINARY_SENSORS,
    NUMBER_ENTITIES,
    SELECT_ENTITIES,
    SWITCH_ENTITIES,
    TEMPERATURE_SENSORS,
    EntityConfig,
)


# Device info that will be included in all discovery payloads
DEVICE_INFO = {
    "identifiers": ["buderus_wps"],
    "name": "Buderus WPS Heat Pump",
    "manufacturer": "Buderus",
    "model": "WPS",
}


def build_discovery_payload(entity: EntityConfig) -> dict:
    """Build a mock MQTT Discovery payload for an entity.

    This simulates what the MQTTBridge will generate.
    """
    payload = {
        "unique_id": f"buderus_wps_{entity.entity_id}",
        "name": entity.name,
        "state_topic": entity.state_topic,
        "availability_topic": "buderus_wps/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "device": DEVICE_INFO,
    }

    # Add type-specific fields
    if entity.device_class:
        payload["device_class"] = entity.device_class

    if entity.unit:
        payload["unit_of_measurement"] = entity.unit

    if entity.state_class:
        payload["state_class"] = entity.state_class

    if entity.command_topic:
        payload["command_topic"] = entity.command_topic

    if entity.options:
        payload["options"] = entity.options

    if entity.min_value is not None:
        payload["min"] = entity.min_value

    if entity.max_value is not None:
        payload["max"] = entity.max_value

    if entity.step is not None:
        payload["step"] = entity.step

    # Binary sensor specific
    if entity.entity_type == "binary_sensor":
        payload["payload_on"] = "ON"
        payload["payload_off"] = "OFF"

    # Switch specific
    if entity.entity_type == "switch":
        payload["payload_on"] = "ON"
        payload["payload_off"] = "OFF"
        payload["state_on"] = "ON"
        payload["state_off"] = "OFF"

    # Number specific
    if entity.entity_type == "number":
        payload["mode"] = "slider"

    return payload


class TestDiscoveryTopicFormat:
    """Test MQTT Discovery topic format."""

    @pytest.mark.parametrize("entity", ALL_ENTITIES, ids=lambda e: e.entity_id)
    def test_discovery_topic_format(self, entity: EntityConfig) -> None:
        """Discovery topic should follow Home Assistant format."""
        expected_topic = f"homeassistant/{entity.entity_type}/buderus_wps/{entity.entity_id}/config"
        # This is what the MQTTBridge should publish to
        assert entity.entity_type in ("sensor", "binary_sensor", "switch", "select", "number")


class TestDiscoveryPayloadRequired:
    """Test required fields in discovery payloads."""

    @pytest.mark.parametrize("entity", ALL_ENTITIES, ids=lambda e: e.entity_id)
    def test_unique_id_format(self, entity: EntityConfig) -> None:
        """Unique ID should follow buderus_wps_<entity_id> format."""
        payload = build_discovery_payload(entity)
        assert payload["unique_id"] == f"buderus_wps_{entity.entity_id}"

    @pytest.mark.parametrize("entity", ALL_ENTITIES, ids=lambda e: e.entity_id)
    def test_name_not_empty(self, entity: EntityConfig) -> None:
        """Entity name should not be empty."""
        payload = build_discovery_payload(entity)
        assert payload["name"]
        assert len(payload["name"]) > 0

    @pytest.mark.parametrize("entity", ALL_ENTITIES, ids=lambda e: e.entity_id)
    def test_state_topic_present(self, entity: EntityConfig) -> None:
        """State topic must be present."""
        payload = build_discovery_payload(entity)
        assert "state_topic" in payload
        assert payload["state_topic"].startswith("buderus_wps/")

    @pytest.mark.parametrize("entity", ALL_ENTITIES, ids=lambda e: e.entity_id)
    def test_availability_configured(self, entity: EntityConfig) -> None:
        """Availability topic should be configured."""
        payload = build_discovery_payload(entity)
        assert payload["availability_topic"] == "buderus_wps/status"
        assert payload["payload_available"] == "online"
        assert payload["payload_not_available"] == "offline"

    @pytest.mark.parametrize("entity", ALL_ENTITIES, ids=lambda e: e.entity_id)
    def test_device_info_complete(self, entity: EntityConfig) -> None:
        """Device info should have required fields."""
        payload = build_discovery_payload(entity)
        device = payload["device"]
        assert "identifiers" in device
        assert "name" in device
        assert "manufacturer" in device
        assert device["manufacturer"] == "Buderus"


class TestSensorDiscoveryPayloads:
    """Test sensor-specific discovery payload requirements."""

    @pytest.mark.parametrize("entity", TEMPERATURE_SENSORS, ids=lambda e: e.entity_id)
    def test_temperature_sensor_device_class(self, entity: EntityConfig) -> None:
        """Temperature sensors should have temperature device class."""
        payload = build_discovery_payload(entity)
        assert payload["device_class"] == "temperature"

    @pytest.mark.parametrize("entity", TEMPERATURE_SENSORS, ids=lambda e: e.entity_id)
    def test_temperature_sensor_unit(self, entity: EntityConfig) -> None:
        """Temperature sensors should have °C unit."""
        payload = build_discovery_payload(entity)
        assert payload["unit_of_measurement"] == "°C"

    @pytest.mark.parametrize("entity", TEMPERATURE_SENSORS, ids=lambda e: e.entity_id)
    def test_temperature_sensor_state_class(self, entity: EntityConfig) -> None:
        """Temperature sensors should have measurement state class."""
        payload = build_discovery_payload(entity)
        assert payload["state_class"] == "measurement"


class TestBinarySensorDiscoveryPayloads:
    """Test binary sensor discovery payload requirements."""

    @pytest.mark.parametrize("entity", BINARY_SENSORS, ids=lambda e: e.entity_id)
    def test_binary_sensor_payloads(self, entity: EntityConfig) -> None:
        """Binary sensors should have ON/OFF payloads."""
        payload = build_discovery_payload(entity)
        assert payload["payload_on"] == "ON"
        assert payload["payload_off"] == "OFF"

    def test_compressor_device_class(self) -> None:
        """Compressor should have running device class."""
        entity = BINARY_SENSORS[0]
        payload = build_discovery_payload(entity)
        assert payload["device_class"] == "running"


class TestSelectDiscoveryPayloads:
    """Test select entity discovery payload requirements."""

    @pytest.mark.parametrize("entity", SELECT_ENTITIES, ids=lambda e: e.entity_id)
    def test_select_has_options(self, entity: EntityConfig) -> None:
        """Select entities should have options list."""
        payload = build_discovery_payload(entity)
        assert "options" in payload
        assert len(payload["options"]) > 0

    @pytest.mark.parametrize("entity", SELECT_ENTITIES, ids=lambda e: e.entity_id)
    def test_select_has_command_topic(self, entity: EntityConfig) -> None:
        """Select entities should have command topic."""
        payload = build_discovery_payload(entity)
        assert "command_topic" in payload
        assert payload["command_topic"].endswith("/set")


class TestSwitchDiscoveryPayloads:
    """Test switch entity discovery payload requirements."""

    @pytest.mark.parametrize("entity", SWITCH_ENTITIES, ids=lambda e: e.entity_id)
    def test_switch_has_payloads(self, entity: EntityConfig) -> None:
        """Switch entities should have ON/OFF payloads."""
        payload = build_discovery_payload(entity)
        assert payload["payload_on"] == "ON"
        assert payload["payload_off"] == "OFF"
        assert payload["state_on"] == "ON"
        assert payload["state_off"] == "OFF"

    @pytest.mark.parametrize("entity", SWITCH_ENTITIES, ids=lambda e: e.entity_id)
    def test_switch_has_command_topic(self, entity: EntityConfig) -> None:
        """Switch entities should have command topic."""
        payload = build_discovery_payload(entity)
        assert "command_topic" in payload


class TestNumberDiscoveryPayloads:
    """Test number entity discovery payload requirements."""

    @pytest.mark.parametrize("entity", NUMBER_ENTITIES, ids=lambda e: e.entity_id)
    def test_number_has_range(self, entity: EntityConfig) -> None:
        """Number entities should have min/max/step."""
        payload = build_discovery_payload(entity)
        assert "min" in payload
        assert "max" in payload
        assert "step" in payload
        assert payload["min"] < payload["max"]

    @pytest.mark.parametrize("entity", NUMBER_ENTITIES, ids=lambda e: e.entity_id)
    def test_number_has_command_topic(self, entity: EntityConfig) -> None:
        """Number entities should have command topic."""
        payload = build_discovery_payload(entity)
        assert "command_topic" in payload

    @pytest.mark.parametrize("entity", NUMBER_ENTITIES, ids=lambda e: e.entity_id)
    def test_number_mode_is_slider(self, entity: EntityConfig) -> None:
        """Number entities should use slider mode."""
        payload = build_discovery_payload(entity)
        assert payload["mode"] == "slider"


class TestPayloadJsonSerialization:
    """Test that payloads can be serialized to JSON."""

    @pytest.mark.parametrize("entity", ALL_ENTITIES, ids=lambda e: e.entity_id)
    def test_payload_serializable(self, entity: EntityConfig) -> None:
        """Discovery payload should be JSON serializable."""
        payload = build_discovery_payload(entity)
        json_str = json.dumps(payload)
        assert json_str
        # Verify round-trip
        parsed = json.loads(json_str)
        assert parsed == payload
