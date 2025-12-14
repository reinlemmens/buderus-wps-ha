"""Unit tests for addon entity configuration."""

import pytest
import sys
from pathlib import Path

# Add addon to path for testing
addon_path = Path(__file__).parent.parent.parent / "addon"
sys.path.insert(0, str(addon_path))

from buderus_wps_addon.entity_config import (
    ALL_ENTITIES,
    BINARY_SENSORS,
    DHW_PROGRAM_MODE_MAP,
    HEATING_SEASON_MODE_MAP,
    NUMBER_ENTITIES,
    SELECT_ENTITIES,
    SWITCH_ENTITIES,
    TEMPERATURE_SENSORS,
    EntityConfig,
    get_controllable_entities,
    get_entities_by_type,
    get_entity_by_id,
    map_option_to_value,
    map_value_to_option,
)


class TestEntityConfig:
    """Test EntityConfig dataclass."""

    def test_entity_config_creates_default_state_topic(self) -> None:
        """State topic should be auto-generated if not provided."""
        entity = EntityConfig(
            entity_id="test_sensor",
            entity_type="sensor",
            name="Test Sensor",
        )
        assert entity.state_topic == "buderus_wps/sensor/test_sensor/state"

    def test_entity_config_creates_command_topic_for_controllable(self) -> None:
        """Command topic should be auto-generated for controllable entities."""
        entity = EntityConfig(
            entity_id="test_switch",
            entity_type="switch",
            name="Test Switch",
            parameter_name="TEST_PARAM",
        )
        assert entity.command_topic == "buderus_wps/switch/test_switch/set"

    def test_entity_config_no_command_topic_for_sensor(self) -> None:
        """Sensors should not have command topics."""
        entity = EntityConfig(
            entity_id="test_sensor",
            entity_type="sensor",
            name="Test Sensor",
        )
        assert entity.command_topic is None


class TestTemperatureSensors:
    """Test temperature sensor definitions."""

    def test_temperature_sensors_count(self) -> None:
        """Should have 6 temperature sensors as per spec."""
        assert len(TEMPERATURE_SENSORS) == 6

    def test_all_temperature_sensors_have_broadcast_idx(self) -> None:
        """All temperature sensors should have broadcast index."""
        for sensor in TEMPERATURE_SENSORS:
            assert sensor.broadcast_idx is not None, f"{sensor.entity_id} missing broadcast_idx"

    def test_temperature_sensors_have_correct_attributes(self) -> None:
        """Temperature sensors should have proper device class and unit."""
        for sensor in TEMPERATURE_SENSORS:
            assert sensor.device_class == "temperature"
            assert sensor.unit == "°C"
            assert sensor.state_class == "measurement"
            assert sensor.entity_type == "sensor"

    def test_temperature_sensor_ids(self) -> None:
        """Verify expected temperature sensor IDs."""
        expected_ids = {
            "outdoor_temp",
            "supply_temp",
            "return_temp",
            "dhw_temp",
            "buffer_top_temp",
            "buffer_bottom_temp",
        }
        actual_ids = {s.entity_id for s in TEMPERATURE_SENSORS}
        assert actual_ids == expected_ids


class TestBinarySensors:
    """Test binary sensor definitions."""

    def test_binary_sensors_count(self) -> None:
        """Should have 1 binary sensor (compressor)."""
        assert len(BINARY_SENSORS) == 1

    def test_compressor_sensor(self) -> None:
        """Compressor sensor should use MenuAPI."""
        compressor = BINARY_SENSORS[0]
        assert compressor.entity_id == "compressor"
        assert compressor.device_class == "running"
        assert compressor.use_menu_api is True


class TestSelectEntities:
    """Test select entity definitions."""

    def test_select_entities_count(self) -> None:
        """Should have 2 select entities."""
        assert len(SELECT_ENTITIES) == 2

    def test_heating_season_mode(self) -> None:
        """Heating season mode should have correct options."""
        entity = get_entity_by_id("heating_season_mode")
        assert entity is not None
        assert entity.options == ["Winter", "Automatic", "Summer"]
        assert entity.parameter_name == "HEATING_SEASON_MODE"

    def test_dhw_program_mode(self) -> None:
        """DHW program mode should have correct options."""
        entity = get_entity_by_id("dhw_program_mode")
        assert entity is not None
        assert entity.options == ["Automatic", "Always On", "Always Off"]
        assert entity.parameter_name == "DHW_PROGRAM_MODE"


class TestSwitchEntities:
    """Test switch entity definitions."""

    def test_switch_entities_count(self) -> None:
        """Should have 1 switch entity."""
        assert len(SWITCH_ENTITIES) == 1

    def test_holiday_mode(self) -> None:
        """Holiday mode should have correct parameter."""
        entity = get_entity_by_id("holiday_mode")
        assert entity is not None
        assert entity.parameter_name == "HOLIDAY_ACTIVE_GLOBAL"
        assert entity.entity_type == "switch"


class TestNumberEntities:
    """Test number entity definitions."""

    def test_number_entities_count(self) -> None:
        """Should have 2 number entities."""
        assert len(NUMBER_ENTITIES) == 2

    def test_extra_dhw_duration(self) -> None:
        """Extra DHW duration should have correct range."""
        entity = get_entity_by_id("extra_dhw_duration")
        assert entity is not None
        assert entity.min_value == 0
        assert entity.max_value == 48
        assert entity.step == 1
        assert entity.unit == "h"
        assert entity.use_menu_api is True

    def test_extra_dhw_target(self) -> None:
        """Extra DHW target should have correct range."""
        entity = get_entity_by_id("extra_dhw_target")
        assert entity is not None
        assert entity.min_value == 50.0
        assert entity.max_value == 65.0
        assert entity.step == 0.5
        assert entity.unit == "°C"
        assert entity.device_class == "temperature"


class TestAllEntities:
    """Test combined entity list."""

    def test_all_entities_count(self) -> None:
        """Total entity count should be correct."""
        expected = (
            len(TEMPERATURE_SENSORS)
            + len(BINARY_SENSORS)
            + len(SELECT_ENTITIES)
            + len(SWITCH_ENTITIES)
            + len(NUMBER_ENTITIES)
        )
        assert len(ALL_ENTITIES) == expected
        assert len(ALL_ENTITIES) == 12  # 6 + 1 + 2 + 1 + 2

    def test_unique_entity_ids(self) -> None:
        """All entity IDs should be unique."""
        ids = [e.entity_id for e in ALL_ENTITIES]
        assert len(ids) == len(set(ids))


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_entity_by_id_found(self) -> None:
        """Should return entity when found."""
        entity = get_entity_by_id("outdoor_temp")
        assert entity is not None
        assert entity.name == "Outdoor Temperature"

    def test_get_entity_by_id_not_found(self) -> None:
        """Should return None when not found."""
        entity = get_entity_by_id("nonexistent")
        assert entity is None

    def test_get_entities_by_type(self) -> None:
        """Should filter entities by type."""
        sensors = get_entities_by_type("sensor")
        assert len(sensors) == 6
        assert all(e.entity_type == "sensor" for e in sensors)

    def test_get_controllable_entities(self) -> None:
        """Should return entities with command topics."""
        controllable = get_controllable_entities()
        assert all(e.command_topic is not None for e in controllable)
        # selects (2) + switches (1) + numbers (2) = 5
        assert len(controllable) == 5


class TestValueMappings:
    """Test value mapping functions."""

    def test_heating_season_mode_map(self) -> None:
        """Heating season mode mapping should be correct."""
        assert HEATING_SEASON_MODE_MAP["Winter"] == 0
        assert HEATING_SEASON_MODE_MAP["Automatic"] == 1
        assert HEATING_SEASON_MODE_MAP["Summer"] == 2

    def test_dhw_program_mode_map(self) -> None:
        """DHW program mode mapping should be correct."""
        assert DHW_PROGRAM_MODE_MAP["Automatic"] == 0
        assert DHW_PROGRAM_MODE_MAP["Always On"] == 1
        assert DHW_PROGRAM_MODE_MAP["Always Off"] == 2

    def test_map_option_to_value(self) -> None:
        """Should map option string to parameter value."""
        assert map_option_to_value("heating_season_mode", "Summer") == 2
        assert map_option_to_value("dhw_program_mode", "Always Off") == 2
        assert map_option_to_value("unknown", "test") is None

    def test_map_value_to_option(self) -> None:
        """Should map parameter value to option string."""
        assert map_value_to_option("heating_season_mode", 2) == "Summer"
        assert map_value_to_option("dhw_program_mode", 0) == "Automatic"
        assert map_value_to_option("unknown", 0) is None
