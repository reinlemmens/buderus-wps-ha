"""Unit tests for the configuration module.

Tests cover:
- SensorMapping validation
- CircuitConfig validation (with HeatingType)
- DHWConfig.has_access()
- InstallationConfig methods
- load_config() with various scenarios
- get_default_sensor_map()
- get_default_config()

Per Constitution Principle IV: All described functionality must have tests.
"""

import pytest
from pathlib import Path
from typing import Dict, Tuple
from unittest.mock import patch, mock_open

from buderus_wps.config import (
    SensorType,
    HeatingType,
    SensorMapping,
    CircuitConfig,
    DHWConfig,
    InstallationConfig,
    DEFAULT_SENSOR_MAPPINGS,
    DEFAULT_SENSOR_LABELS,
    get_default_sensor_map,
    get_default_config,
    load_config,
    _find_config_file,
    _parse_sensor_mappings,
    _parse_circuits,
    _parse_dhw,
    _parse_labels,
)


# =============================================================================
# SensorMapping Tests
# =============================================================================


class TestSensorMapping:
    """Tests for SensorMapping dataclass validation."""

    def test_valid_sensor_mapping(self) -> None:
        """Test creating a valid sensor mapping."""
        mapping = SensorMapping(base=0x0402, idx=38, sensor=SensorType.OUTDOOR)
        assert mapping.base == 0x0402
        assert mapping.idx == 38
        assert mapping.sensor == SensorType.OUTDOOR

    def test_sensor_mapping_key_property(self) -> None:
        """Test that key property returns (base, idx) tuple."""
        mapping = SensorMapping(base=0x0060, idx=58, sensor=SensorType.DHW)
        assert mapping.key == (0x0060, 58)

    def test_invalid_base_too_high(self) -> None:
        """Test that base > 0xFFFF raises ValueError."""
        with pytest.raises(ValueError, match="base must be 0-65535"):
            SensorMapping(base=0x10000, idx=38, sensor=SensorType.OUTDOOR)

    def test_invalid_base_negative(self) -> None:
        """Test that negative base raises ValueError."""
        with pytest.raises(ValueError, match="base must be 0-65535"):
            SensorMapping(base=-1, idx=38, sensor=SensorType.OUTDOOR)

    def test_invalid_idx_too_high(self) -> None:
        """Test that idx > 2047 raises ValueError."""
        with pytest.raises(ValueError, match="idx must be 0-2047"):
            SensorMapping(base=0x0402, idx=2048, sensor=SensorType.OUTDOOR)

    def test_invalid_idx_negative(self) -> None:
        """Test that negative idx raises ValueError."""
        with pytest.raises(ValueError, match="idx must be 0-2047"):
            SensorMapping(base=0x0402, idx=-1, sensor=SensorType.OUTDOOR)

    def test_boundary_values_valid(self) -> None:
        """Test boundary values are accepted."""
        # Min values
        mapping_min = SensorMapping(base=0, idx=0, sensor=SensorType.OUTDOOR)
        assert mapping_min.base == 0
        assert mapping_min.idx == 0

        # Max values
        mapping_max = SensorMapping(base=0xFFFF, idx=2047, sensor=SensorType.OUTDOOR)
        assert mapping_max.base == 0xFFFF
        assert mapping_max.idx == 2047


# =============================================================================
# CircuitConfig Tests
# =============================================================================


class TestCircuitConfig:
    """Tests for CircuitConfig dataclass validation."""

    def test_valid_circuit_config(self) -> None:
        """Test creating a valid circuit configuration."""
        circuit = CircuitConfig(
            number=1,
            heating_type=HeatingType.VENTILO,
            apartment="Apartment 0",
            label="Living Room",
        )
        assert circuit.number == 1
        assert circuit.heating_type == HeatingType.VENTILO
        assert circuit.apartment == "Apartment 0"
        assert circuit.label == "Living Room"

    def test_circuit_config_defaults(self) -> None:
        """Test default values for optional fields."""
        circuit = CircuitConfig(number=2)
        assert circuit.heating_type == HeatingType.UNKNOWN
        assert circuit.apartment is None
        assert circuit.label is None

    def test_invalid_number_too_low(self) -> None:
        """Test that number < 1 raises ValueError."""
        with pytest.raises(ValueError, match="number must be 1-4"):
            CircuitConfig(number=0)

    def test_invalid_number_too_high(self) -> None:
        """Test that number > 4 raises ValueError."""
        with pytest.raises(ValueError, match="number must be 1-4"):
            CircuitConfig(number=5)

    def test_valid_numbers_1_to_4(self) -> None:
        """Test that numbers 1-4 are all valid."""
        for num in [1, 2, 3, 4]:
            circuit = CircuitConfig(number=num)
            assert circuit.number == num


# =============================================================================
# DHWConfig Tests
# =============================================================================


class TestDHWConfig:
    """Tests for DHWConfig dataclass and has_access method."""

    def test_has_access_returns_true_for_listed_apartment(self) -> None:
        """Test has_access returns true for apartment in list."""
        dhw = DHWConfig(apartments=["Apartment 0", "Apartment 2"])
        assert dhw.has_access("Apartment 0") is True
        assert dhw.has_access("Apartment 2") is True

    def test_has_access_returns_false_for_unlisted_apartment(self) -> None:
        """Test has_access returns false for apartment not in list."""
        dhw = DHWConfig(apartments=["Apartment 0"])
        assert dhw.has_access("Apartment 1") is False
        assert dhw.has_access("Apartment 2") is False

    def test_has_access_returns_true_for_all_when_apartments_none(self) -> None:
        """Test has_access returns true for all when apartments is None."""
        dhw = DHWConfig(apartments=None)
        assert dhw.has_access("Apartment 0") is True
        assert dhw.has_access("Apartment 1") is True
        assert dhw.has_access("Any Apartment") is True

    def test_has_access_empty_list_denies_all(self) -> None:
        """Test has_access returns false for all when apartments is empty list."""
        dhw = DHWConfig(apartments=[])
        assert dhw.has_access("Apartment 0") is False


# =============================================================================
# InstallationConfig Tests
# =============================================================================


class TestInstallationConfig:
    """Tests for InstallationConfig dataclass methods."""

    def test_get_sensor_map(self) -> None:
        """Test get_sensor_map returns correct dictionary."""
        mappings = [
            SensorMapping(base=0x0402, idx=38, sensor=SensorType.OUTDOOR),
            SensorMapping(base=0x0060, idx=58, sensor=SensorType.DHW),
        ]
        config = InstallationConfig(sensor_mappings=mappings)
        sensor_map = config.get_sensor_map()

        assert sensor_map == {
            (0x0402, 38): "outdoor",
            (0x0060, 58): "dhw",
        }

    def test_get_circuit_returns_correct_circuit(self) -> None:
        """Test get_circuit returns matching circuit."""
        circuits = [
            CircuitConfig(number=1, heating_type=HeatingType.VENTILO),
            CircuitConfig(number=2, heating_type=HeatingType.FLOOR_HEATING),
        ]
        config = InstallationConfig(circuits=circuits)

        circuit1 = config.get_circuit(1)
        assert circuit1 is not None
        assert circuit1.heating_type == HeatingType.VENTILO

        circuit2 = config.get_circuit(2)
        assert circuit2 is not None
        assert circuit2.heating_type == HeatingType.FLOOR_HEATING

    def test_get_circuit_returns_none_for_missing(self) -> None:
        """Test get_circuit returns None for non-existent circuit."""
        config = InstallationConfig(circuits=[])
        assert config.get_circuit(1) is None

    def test_get_circuits_by_apartment(self) -> None:
        """Test get_circuits_by_apartment groups correctly."""
        circuits = [
            CircuitConfig(number=1, apartment="Apt A"),
            CircuitConfig(number=2, apartment="Apt B"),
            CircuitConfig(number=3, apartment="Apt A"),
        ]
        config = InstallationConfig(circuits=circuits)

        apt_a_circuits = config.get_circuits_by_apartment("Apt A")
        assert len(apt_a_circuits) == 2
        assert all(c.apartment == "Apt A" for c in apt_a_circuits)

        apt_b_circuits = config.get_circuits_by_apartment("Apt B")
        assert len(apt_b_circuits) == 1

        apt_c_circuits = config.get_circuits_by_apartment("Apt C")
        assert len(apt_c_circuits) == 0

    def test_get_label_returns_custom_label(self) -> None:
        """Test get_label returns custom label when defined."""
        config = InstallationConfig(labels={"outdoor": "Outside Air"})
        assert config.get_label("outdoor") == "Outside Air"

    def test_get_label_returns_default_label(self) -> None:
        """Test get_label returns default label when not custom."""
        config = InstallationConfig(labels={})
        assert config.get_label("outdoor") == "Outdoor Temperature"
        assert config.get_label("dhw") == "Hot Water Temperature"

    def test_get_label_formats_unknown_sensor(self) -> None:
        """Test get_label formats unknown sensor names."""
        config = InstallationConfig(labels={})
        assert config.get_label("unknown_sensor") == "Unknown Sensor"


# =============================================================================
# get_default_sensor_map Tests
# =============================================================================


class TestGetDefaultSensorMap:
    """Tests for get_default_sensor_map function."""

    def test_returns_dict_with_expected_mappings(self) -> None:
        """Test that default map contains expected verified mappings."""
        sensor_map = get_default_sensor_map()

        # Check key verified mappings from 2024-12-02 testing
        assert sensor_map.get((0x0402, 38)) == "outdoor"
        assert sensor_map.get((0x0060, 58)) == "dhw"
        assert sensor_map.get((0x0270, 1)) == "supply"
        assert sensor_map.get((0x0270, 0)) == "return_temp"
        assert sensor_map.get((0x0060, 12)) == "brine_in"

    def test_returns_all_five_sensor_types(self) -> None:
        """Test that all 5 core sensors are represented."""
        sensor_map = get_default_sensor_map()
        sensor_values = set(sensor_map.values())

        expected_sensors = {"outdoor", "supply", "return_temp", "dhw", "brine_in"}
        assert expected_sensors.issubset(sensor_values)


# =============================================================================
# get_default_config Tests
# =============================================================================


class TestGetDefaultConfig:
    """Tests for get_default_config function."""

    def test_returns_installation_config(self) -> None:
        """Test that default config is InstallationConfig."""
        config = get_default_config()
        assert isinstance(config, InstallationConfig)

    def test_has_default_sensor_mappings(self) -> None:
        """Test that default config has sensor mappings."""
        config = get_default_config()
        assert len(config.sensor_mappings) > 0
        assert all(isinstance(m, SensorMapping) for m in config.sensor_mappings)

    def test_has_empty_circuits_by_default(self) -> None:
        """Test that default config has no circuits defined."""
        config = get_default_config()
        assert config.circuits == []

    def test_dhw_allows_all_by_default(self) -> None:
        """Test that default DHW allows all apartments."""
        config = get_default_config()
        assert config.dhw.has_access("Any Apartment") is True


# =============================================================================
# load_config Tests
# =============================================================================


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_with_valid_yaml_file(self, tmp_path: Path) -> None:
        """Test loading config from valid YAML file."""
        config_content = """
version: "1.0"
sensor_mappings:
  - base: 0x0402
    idx: 38
    sensor: outdoor
circuits:
  - number: 1
    type: ventilo
    apartment: "Apt 0"
dhw:
  apartments:
    - "Apt 0"
labels:
  outdoor: "Outside"
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))

        assert config.version == "1.0"
        assert len(config.sensor_mappings) == 1
        assert config.sensor_mappings[0].sensor == SensorType.OUTDOOR
        assert len(config.circuits) == 1
        assert config.circuits[0].heating_type == HeatingType.VENTILO
        assert config.dhw.has_access("Apt 0") is True
        assert config.dhw.has_access("Apt 1") is False
        assert config.labels.get("outdoor") == "Outside"

    def test_load_config_with_missing_file_returns_defaults(self) -> None:
        """Test that missing file returns default config."""
        config = load_config("/nonexistent/path/config.yaml")

        assert isinstance(config, InstallationConfig)
        assert len(config.sensor_mappings) > 0  # Has defaults

    def test_load_config_with_invalid_yaml_returns_defaults(
        self, tmp_path: Path
    ) -> None:
        """Test that invalid YAML returns default config."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [")

        config = load_config(str(config_file))

        assert isinstance(config, InstallationConfig)
        assert len(config.sensor_mappings) > 0  # Has defaults

    def test_load_config_with_empty_file_returns_defaults(self, tmp_path: Path) -> None:
        """Test that empty file returns default config."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        config = load_config(str(config_file))
        assert len(config.sensor_mappings) > 0  # Has defaults

    def test_load_config_uses_default_mappings_when_not_specified(
        self, tmp_path: Path
    ) -> None:
        """Test that config without sensor_mappings uses defaults."""
        config_content = """
version: "1.0"
circuits:
  - number: 1
    type: floor_heating
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(config_content)

        config = load_config(str(config_file))

        # Should have default mappings since none specified
        assert len(config.sensor_mappings) == len(DEFAULT_SENSOR_MAPPINGS)

    def test_load_config_finds_file_via_env_var(self, tmp_path: Path) -> None:
        """Test that config is found via environment variable."""
        config_content = "version: '2.0'"
        config_file = tmp_path / "env_config.yaml"
        config_file.write_text(config_content)

        with patch.dict("os.environ", {"BUDERUS_WPS_CONFIG": str(config_file)}):
            config = load_config()
            assert config.version == "2.0"


# =============================================================================
# Parser Helper Tests
# =============================================================================


class TestParseSensorMappings:
    """Tests for _parse_sensor_mappings helper."""

    def test_parse_valid_mappings(self) -> None:
        """Test parsing valid mapping data."""
        data = [
            {"base": 0x0402, "idx": 38, "sensor": "outdoor"},
            {"base": 96, "idx": 58, "sensor": "dhw"},  # Decimal base
        ]
        mappings = _parse_sensor_mappings(data)

        assert len(mappings) == 2
        assert mappings[0].base == 0x0402
        assert mappings[1].base == 96

    def test_parse_hex_string_base(self) -> None:
        """Test parsing base as hex string."""
        data = [{"base": "0x0402", "idx": 38, "sensor": "outdoor"}]
        mappings = _parse_sensor_mappings(data)

        assert len(mappings) == 1
        assert mappings[0].base == 0x0402

    def test_skip_invalid_sensor_type(self) -> None:
        """Test that invalid sensor types are skipped."""
        data = [{"base": 0x0402, "idx": 38, "sensor": "invalid_sensor"}]
        mappings = _parse_sensor_mappings(data)

        assert len(mappings) == 0


class TestParseCircuits:
    """Tests for _parse_circuits helper."""

    def test_parse_valid_circuits(self) -> None:
        """Test parsing valid circuit data."""
        data = [
            {"number": 1, "type": "ventilo", "apartment": "Apt 0"},
            {"number": 2, "type": "floor_heating"},
        ]
        circuits = _parse_circuits(data)

        assert len(circuits) == 2
        assert circuits[0].heating_type == HeatingType.VENTILO
        assert circuits[1].heating_type == HeatingType.FLOOR_HEATING

    def test_unknown_type_uses_unknown(self) -> None:
        """Test that unknown circuit type defaults to UNKNOWN."""
        data = [{"number": 1, "type": "invalid_type"}]
        circuits = _parse_circuits(data)

        assert len(circuits) == 1
        assert circuits[0].heating_type == HeatingType.UNKNOWN


class TestParseDHW:
    """Tests for _parse_dhw helper."""

    def test_parse_valid_dhw(self) -> None:
        """Test parsing valid DHW data."""
        data = {"apartments": ["Apt 0", "Apt 1"]}
        dhw = _parse_dhw(data)

        assert dhw.apartments == ["Apt 0", "Apt 1"]

    def test_parse_empty_dhw(self) -> None:
        """Test parsing empty DHW data."""
        dhw = _parse_dhw({})
        assert dhw.apartments is None


class TestParseLabels:
    """Tests for _parse_labels helper."""

    def test_parse_valid_labels(self) -> None:
        """Test parsing valid label data."""
        data = {"outdoor": "Outside Air", "dhw": "Hot Water"}
        labels = _parse_labels(data)

        assert labels == {"outdoor": "Outside Air", "dhw": "Hot Water"}

    def test_skip_non_string_values(self) -> None:
        """Test that non-string values are skipped."""
        data = {"outdoor": "Valid", "invalid": 123}
        labels = _parse_labels(data)

        assert labels == {"outdoor": "Valid"}
