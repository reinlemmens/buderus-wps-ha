"""Unit tests for TUI Circuit Configuration - T100, T101, T106.

Tests for CircuitConfig loading and validation.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import List

from buderus_wps.config import (
    CircuitConfig,
    InstallationConfig,
    load_config,
    get_default_config,
)


class TestCircuitConfig:
    """Tests for CircuitConfig dataclass - T100."""

    def test_circuit_config_creation(self) -> None:
        """Can create CircuitConfig with all fields."""
        config = CircuitConfig(
            number=1,
            label="Ground Floor",
        )
        assert config.number == 1
        assert config.label == "Ground Floor"

    def test_circuit_config_with_tui_fields(self) -> None:
        """CircuitConfig includes TUI-specific sensor mapping fields."""
        config = CircuitConfig(
            number=2,
            label="First Floor",
            room_temp_sensor="room_temp_c2",
            setpoint_param="HEATING_CIRCUIT_2_SETPOINT",
            program_param="HEATING_CIRCUIT_2_PROGRAM",
        )
        assert config.number == 2
        assert config.label == "First Floor"
        assert config.room_temp_sensor == "room_temp_c2"
        assert config.setpoint_param == "HEATING_CIRCUIT_2_SETPOINT"
        assert config.program_param == "HEATING_CIRCUIT_2_PROGRAM"

    def test_circuit_config_defaults(self) -> None:
        """CircuitConfig has sensible defaults for optional fields."""
        config = CircuitConfig(number=1)
        assert config.room_temp_sensor == ""
        assert config.setpoint_param == ""
        assert config.program_param == ""

    def test_circuit_config_number_validation(self) -> None:
        """CircuitConfig validates number is 1-4."""
        with pytest.raises(ValueError, match="number must be 1-4"):
            CircuitConfig(number=0)
        with pytest.raises(ValueError, match="number must be 1-4"):
            CircuitConfig(number=5)

    def test_circuit_config_valid_numbers(self) -> None:
        """CircuitConfig accepts numbers 1-4."""
        for num in [1, 2, 3, 4]:
            config = CircuitConfig(number=num)
            assert config.number == num


class TestCircuitConfigLoading:
    """Tests for loading circuit config from YAML - T100, T101."""

    def test_load_config_with_circuits(self) -> None:
        """Can load circuits with TUI fields from YAML."""
        yaml_content = """
version: "1.0"
circuits:
  - number: 1
    label: "Ground Floor"
    type: floor_heating
    room_temp_sensor: room_temp_c1
    setpoint_param: HEATING_CIRCUIT_1_SETPOINT
    program_param: HEATING_CIRCUIT_1_PROGRAM
  - number: 2
    label: "First Floor"
    type: ventilo
    room_temp_sensor: room_temp_c2
    setpoint_param: HEATING_CIRCUIT_2_SETPOINT
    program_param: HEATING_CIRCUIT_2_PROGRAM
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_config(f.name)
                assert len(config.circuits) == 2

                c1 = config.circuits[0]
                assert c1.number == 1
                assert c1.label == "Ground Floor"
                assert c1.room_temp_sensor == "room_temp_c1"
                assert c1.setpoint_param == "HEATING_CIRCUIT_1_SETPOINT"

                c2 = config.circuits[1]
                assert c2.number == 2
                assert c2.label == "First Floor"
                assert c2.room_temp_sensor == "room_temp_c2"
            finally:
                os.unlink(f.name)

    def test_load_config_four_circuits(self) -> None:
        """Can load all four circuits from YAML."""
        yaml_content = """
version: "1.0"
circuits:
  - number: 1
    label: "Circuit 1"
    room_temp_sensor: room_temp_c1
  - number: 2
    label: "Circuit 2"
    room_temp_sensor: room_temp_c2
  - number: 3
    label: "Circuit 3"
    room_temp_sensor: room_temp_c3
  - number: 4
    label: "Circuit 4"
    room_temp_sensor: room_temp_c4
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_config(f.name)
                assert len(config.circuits) == 4

                for i, circuit in enumerate(config.circuits, 1):
                    assert circuit.number == i
                    assert circuit.label == f"Circuit {i}"
                    assert circuit.room_temp_sensor == f"room_temp_c{i}"
            finally:
                os.unlink(f.name)


class TestMissingInvalidConfig:
    """Tests for missing/invalid configuration handling - T101, T106."""

    def test_missing_config_file_uses_defaults(self) -> None:
        """Missing config file returns default configuration."""
        config = load_config("/nonexistent/path/config.yaml")
        assert isinstance(config, InstallationConfig)
        assert config.circuits == []  # Default is no circuits

    def test_empty_config_file_uses_defaults(self) -> None:
        """Empty config file returns default configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            f.flush()

            try:
                config = load_config(f.name)
                assert isinstance(config, InstallationConfig)
            finally:
                os.unlink(f.name)

    def test_malformed_yaml_uses_defaults(self) -> None:
        """Malformed YAML returns default configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            f.flush()

            try:
                config = load_config(f.name)
                assert isinstance(config, InstallationConfig)
            finally:
                os.unlink(f.name)

    def test_no_circuits_section_returns_empty_list(self) -> None:
        """Config without circuits section returns empty circuit list."""
        yaml_content = """
version: "1.0"
labels:
  outdoor: "Outside Temp"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_config(f.name)
                assert config.circuits == []
            finally:
                os.unlink(f.name)

    def test_invalid_circuit_number_skipped(self) -> None:
        """Invalid circuit numbers are skipped during loading."""
        yaml_content = """
version: "1.0"
circuits:
  - number: 0
    label: "Invalid"
  - number: 1
    label: "Valid"
  - number: 5
    label: "Also Invalid"
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_config(f.name)
                # Only valid circuit should be loaded
                assert len(config.circuits) == 1
                assert config.circuits[0].number == 1
            finally:
                os.unlink(f.name)

    def test_default_config_has_no_circuits(self) -> None:
        """Default configuration has no circuits configured."""
        config = get_default_config()
        assert config.circuits == []

    def test_default_config_has_sensor_mappings(self) -> None:
        """Default configuration has sensor mappings."""
        config = get_default_config()
        assert len(config.sensor_mappings) > 0


class TestInstallationConfigCircuitHelpers:
    """Tests for InstallationConfig circuit helper methods."""

    def test_get_circuit_by_number(self) -> None:
        """Can get circuit by number."""
        config = InstallationConfig(
            circuits=[
                CircuitConfig(number=1, label="First"),
                CircuitConfig(number=3, label="Third"),
            ]
        )

        assert config.get_circuit(1).label == "First"
        assert config.get_circuit(3).label == "Third"
        assert config.get_circuit(2) is None
        assert config.get_circuit(4) is None

    def test_get_circuit_display_name(self) -> None:
        """Get display name for circuit (label or default)."""
        config = InstallationConfig(
            circuits=[
                CircuitConfig(number=1, label="Ground Floor"),
                CircuitConfig(number=2),  # No label
            ]
        )

        c1 = config.get_circuit(1)
        c2 = config.get_circuit(2)

        # Circuit with label
        assert c1.label == "Ground Floor"
        # Circuit without label gets None
        assert c2.label is None
