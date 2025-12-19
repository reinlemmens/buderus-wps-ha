"""Acceptance tests for User Story 0: Discover Parameters from Device.

# PROTOCOL: Tests the discovery protocol from fhem/26_KM273v018.pm:2052-2187

User Story 0 - Discover Parameters from Device (Priority: P0)
A home automation developer needs to discover all available parameters from the
connected Buderus WPS heat pump before any read/write operations can occur.

Acceptance Scenarios:
1. System requests element count using CAN ID 0x01FD7FE0
2. System retrieves element data in 4096-byte chunks using CAN ID 0x01FD3FE0
3. Binary data parsed correctly: idx, extid, max, min, len, name
4. CAN IDs dynamically constructed using formula: rtr = 0x04003FE0 | (idx << 14)
5. Fallback to @KM273_elements_default when discovery fails
"""

import struct
import pytest
from buderus_wps.discovery import ParameterDiscovery
from buderus_wps.parameter import Parameter, HeatPump
from buderus_wps.parameter_data import PARAMETER_DATA


class TestAcceptanceScenario1:
    """Scenario 1: System requests element count using CAN ID 0x01FD7FE0."""

    def test_element_count_request_can_id(self):
        """Given a CAN bus connection, When discovery initiates,
        Then the system uses CAN ID 0x01FD7FE0 for element count request."""
        assert ParameterDiscovery.ELEMENT_COUNT_SEND == 0x01FD7FE0

    def test_element_count_response_can_id(self):
        """The system receives element count on CAN ID 0x09FD7FE0."""
        assert ParameterDiscovery.ELEMENT_COUNT_RECV == 0x09FD7FE0


class TestAcceptanceScenario2:
    """Scenario 2: System retrieves element data in 4096-byte chunks."""

    def test_element_data_request_can_id(self):
        """Given the element count is received, When requesting element data,
        Then the system uses CAN ID 0x01FD3FE0."""
        assert ParameterDiscovery.ELEMENT_DATA_SEND == 0x01FD3FE0

    def test_element_data_response_can_id(self):
        """The system receives element data on CAN ID 0x09FDBFE0."""
        assert ParameterDiscovery.ELEMENT_DATA_RECV == 0x09FDBFE0

    def test_chunk_size_is_4096(self):
        """The system uses 4096-byte chunks for data retrieval."""
        assert ParameterDiscovery.CHUNK_SIZE == 4096


class TestAcceptanceScenario3:
    """Scenario 3: Binary data parsed correctly for idx, extid, max, min, len, name."""

    def create_test_element(self, idx, extid, max_val, min_val, name):
        """Helper to create binary element data."""
        data = struct.pack('>H', idx)  # idx, 2 bytes, big-endian
        data += bytes.fromhex(extid)  # extid, 7 bytes
        data += struct.pack('>I', max_val & 0xFFFFFFFF)  # max, 4 bytes
        data += struct.pack('>I', min_val & 0xFFFFFFFF)  # min, 4 bytes
        name_bytes = name.encode('ascii') + b'\x00'
        data += struct.pack('b', len(name_bytes))  # len, 1 byte
        data += name_bytes  # name
        return data

    def test_parse_extracts_idx_correctly(self):
        """Given binary element data, When parsed, Then idx is correctly extracted."""
        data = self.create_test_element(42, "AABBCCDDEEFF00", 100, 0, "TEST")
        element, _ = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['idx'] == 42

    def test_parse_extracts_extid_correctly(self):
        """Given binary element data, When parsed, Then extid is correctly extracted."""
        data = self.create_test_element(1, "61E1E1FC660023", 5, 0, "ACCESS_LEVEL")
        element, _ = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['extid'] == "61E1E1FC660023"

    def test_parse_extracts_max_correctly(self):
        """Given binary element data, When parsed, Then max is correctly extracted."""
        data = self.create_test_element(1, "61E1E1FC660023", 16777216, 0, "TEST")
        element, _ = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['max'] == 16777216

    def test_parse_extracts_min_correctly(self):
        """Given binary element data, When parsed, Then min is correctly extracted."""
        data = self.create_test_element(11, "E555E4E11002E9", 40, -30, "TEMP_PARAM")
        element, _ = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['min'] == -30

    def test_parse_extracts_name_correctly(self):
        """Given binary element data, When parsed, Then name is correctly extracted."""
        data = self.create_test_element(1, "61E1E1FC660023", 5, 0, "ACCESS_LEVEL")
        element, _ = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['text'] == "ACCESS_LEVEL"


class TestAcceptanceScenario4:
    """Scenario 4: CAN IDs dynamically constructed using formula."""

    def test_read_can_id_formula_idx_0(self):
        """Given parameter with idx=0, When calculating read CAN ID,
        Then result is 0x04003FE0 (base value)."""
        param = Parameter(idx=0, extid="0000000000", min=0, max=0,
                          format="int", read=0, text="TEST")
        assert param.get_read_can_id() == 0x04003FE0

    def test_read_can_id_formula_idx_1(self):
        """Given parameter with idx=1, When calculating read CAN ID,
        Then result is 0x04003FE0 | (1 << 14) = 0x04007FE0."""
        param = Parameter(idx=1, extid="61E1E1FC660023", min=0, max=5,
                          format="int", read=0, text="ACCESS_LEVEL")
        assert param.get_read_can_id() == 0x04007FE0

    def test_write_can_id_formula_idx_0(self):
        """Given parameter with idx=0, When calculating write CAN ID,
        Then result is 0x0C003FE0 (base value)."""
        param = Parameter(idx=0, extid="0000000000", min=0, max=0,
                          format="int", read=0, text="TEST")
        assert param.get_write_can_id() == 0x0C003FE0

    def test_write_can_id_formula_idx_1(self):
        """Given parameter with idx=1, When calculating write CAN ID,
        Then result is 0x0C003FE0 | (1 << 14) = 0x0C007FE0."""
        param = Parameter(idx=1, extid="61E1E1FC660023", min=0, max=5,
                          format="int", read=0, text="ACCESS_LEVEL")
        assert param.get_write_can_id() == 0x0C007FE0

    def test_can_id_formula_matches_fhem(self):
        """Given any parameter, CAN ID calculation matches FHEM formula:
        rtr = 0x04003FE0 | (idx << 14)
        txd = 0x0C003FE0 | (idx << 14)
        """
        # Test with several known parameters from PARAMETER_DATA
        for param_data in PARAMETER_DATA[:10]:
            param = Parameter(**param_data)
            idx = param.idx

            expected_read = 0x04003FE0 | (idx << 14)
            expected_write = 0x0C003FE0 | (idx << 14)

            assert param.get_read_can_id() == expected_read, f"Read CAN ID mismatch for idx={idx}"
            assert param.get_write_can_id() == expected_write, f"Write CAN ID mismatch for idx={idx}"


class TestAcceptanceScenario5:
    """Scenario 5: Fallback to @KM273_elements_default when discovery fails."""

    def test_fallback_data_is_available(self):
        """Given discovery fails, When loading parameters,
        Then @KM273_elements_default static data is available."""
        # PARAMETER_DATA contains the fallback data
        assert len(PARAMETER_DATA) > 0
        assert len(PARAMETER_DATA) == 1788  # Known count from FHEM

    def test_heat_pump_loads_fallback_without_adapter(self):
        """Given no CAN adapter, When HeatPump is instantiated,
        Then it loads from static fallback data."""
        heat_pump = HeatPump()

        assert heat_pump.parameter_count() == 1788
        assert heat_pump.has_parameter_name("ACCESS_LEVEL")

    def test_fallback_parameters_have_can_id_methods(self):
        """Given fallback parameters, They have CAN ID calculation methods."""
        heat_pump = HeatPump()
        param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

        # CAN ID methods work on fallback data
        read_id = param.get_read_can_id()
        write_id = param.get_write_can_id()

        assert read_id == 0x04007FE0
        assert write_id == 0x0C007FE0

    def test_fallback_data_matches_known_values(self):
        """Fallback data matches known FHEM values for key parameters."""
        heat_pump = HeatPump()

        # Check idx=0: ACCESSORIES_CONNECTED_BITMASK
        p0 = heat_pump.get_parameter_by_index(0)
        assert p0.text == "ACCESSORIES_CONNECTED_BITMASK"
        assert p0.extid == "814A53C66A0802"
        assert p0.min == 0
        assert p0.max == 0

        # Check idx=1: ACCESS_LEVEL
        p1 = heat_pump.get_parameter_by_index(1)
        assert p1.text == "ACCESS_LEVEL"
        assert p1.extid == "61E1E1FC660023"
        assert p1.min == 0
        assert p1.max == 5

        # Check idx=11: ADDITIONAL_BLOCK_HIGH_T2_TEMP (negative min)
        p11 = heat_pump.get_parameter_by_index(11)
        assert p11.text == "ADDITIONAL_BLOCK_HIGH_T2_TEMP"
        assert p11.min == -30
        assert p11.max == 40
