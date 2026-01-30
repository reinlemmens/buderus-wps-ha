"""Unit tests for BroadcastMonitor class."""

from unittest.mock import MagicMock

import pytest
from buderus_wps.broadcast_monitor import (
    KNOWN_BROADCASTS,
    BroadcastMonitor,
    BroadcastReading,
    decode_can_id,
    encode_can_id,
)


class TestDecodeCanId:
    """Test CAN ID decoding utility."""

    def test_decode_outdoor_temp_c0(self) -> None:
        """Test decoding outdoor temperature CAN ID."""
        # 0x00030060 = idx=12, base=0x0060
        direction, idx, base = decode_can_id(0x00030060)
        assert idx == 12
        assert base == 0x0060

    def test_decode_rc10_c3_demand(self) -> None:
        """Test decoding RC10 C3 demand CAN ID."""
        # 0x0C1AC402 = idx=107, base=0x0402
        direction, idx, base = decode_can_id(0x0C1AC402)
        assert idx == 107
        assert base == 0x0402

    def test_decode_rc10_c1_room_temp(self) -> None:
        """Test decoding RC10 C1 room temp CAN ID."""
        # 0x0C000060 = idx=0, base=0x0060
        direction, idx, base = decode_can_id(0x0C000060)
        assert idx == 0
        assert base == 0x0060


class TestEncodeCanId:
    """Test CAN ID encoding utility."""

    def test_encode_roundtrip(self) -> None:
        """Test encode/decode roundtrip."""
        original = 0x0C1AC402
        direction, idx, base = decode_can_id(original)
        encoded = encode_can_id(direction, idx, base)
        assert encoded == original


class TestBroadcastReading:
    """Test BroadcastReading dataclass."""

    def test_temperature_property(self) -> None:
        """Test temperature property decodes correctly."""
        reading = BroadcastReading(
            can_id=0x0C000060,
            base=0x0060,
            idx=0,
            dlc=2,
            raw_data=b"\x00\xcd",  # 205 = 20.5°C
            raw_value=205,
            timestamp=0.0,
        )
        assert reading.temperature == 20.5

    def test_is_temperature_valid(self) -> None:
        """Test is_temperature for valid temperature."""
        reading = BroadcastReading(
            can_id=0x0C000060,
            base=0x0060,
            idx=0,
            dlc=2,
            raw_data=b"\x00\xcd",
            raw_value=205,
            timestamp=0.0,
        )
        assert reading.is_temperature is True

    def test_is_temperature_out_of_range(self) -> None:
        """Test is_temperature for out-of-range value."""
        reading = BroadcastReading(
            can_id=0x0C000060,
            base=0x0060,
            idx=0,
            dlc=2,
            raw_data=b"\xff\xff",
            raw_value=65535,  # Too high for temperature
            timestamp=0.0,
        )
        assert reading.is_temperature is False

    def test_circuit_property(self) -> None:
        """Test circuit property extracts circuit number."""
        for circuit in range(4):
            reading = BroadcastReading(
                can_id=0x0C000060 + circuit,
                base=0x0060 + circuit,
                idx=0,
                dlc=2,
                raw_data=b"\x00\x00",
                raw_value=0,
                timestamp=0.0,
            )
            assert reading.circuit == circuit


class TestGetKnownName:
    """Test BroadcastMonitor.get_known_name() method."""

    @pytest.fixture
    def monitor(self) -> BroadcastMonitor:
        """Create monitor with mock adapter."""
        adapter = MagicMock()
        adapter.is_open = True
        return BroadcastMonitor(adapter)

    def test_known_outdoor_temp_c0(self, monitor: BroadcastMonitor) -> None:
        """Test get_known_name returns correct name for outdoor temp."""
        reading = BroadcastReading(
            can_id=0x00030060,
            base=0x0060,
            idx=12,
            dlc=2,
            raw_data=b"\x00\x69",  # 10.5°C
            raw_value=105,
            timestamp=0.0,
        )
        name = monitor.get_known_name(reading)
        assert name == "OUTDOOR_TEMP_C0"

    def test_known_rc10_c1_room_temp(self, monitor: BroadcastMonitor) -> None:
        """Test get_known_name returns correct name for RC10 C1 room temp."""
        reading = BroadcastReading(
            can_id=0x0C000060,
            base=0x0060,
            idx=0,
            dlc=2,
            raw_data=b"\x00\xcd",
            raw_value=205,
            timestamp=0.0,
        )
        name = monitor.get_known_name(reading)
        assert name == "RC10_C1_ROOM_TEMP"

    def test_known_rc10_c1_demand(self, monitor: BroadcastMonitor) -> None:
        """Test get_known_name returns correct name for RC10 C1 demand."""
        reading = BroadcastReading(
            can_id=0x0C048060,
            base=0x0060,
            idx=18,
            dlc=2,
            raw_data=b"\x00\xbe",
            raw_value=190,
            timestamp=0.0,
        )
        name = monitor.get_known_name(reading)
        assert name == "RC10_C1_DEMAND_TEMP"

    def test_known_rc10_c3_room_temp(self, monitor: BroadcastMonitor) -> None:
        """Test get_known_name returns correct name for RC10 C3 room temp."""
        reading = BroadcastReading(
            can_id=0x0C0DC402,
            base=0x0402,
            idx=55,
            dlc=2,
            raw_data=b"\x00\xdd",
            raw_value=221,
            timestamp=0.0,
        )
        name = monitor.get_known_name(reading)
        # Renamed to _ALT since primary C3 room temp is now on base 0x0062, idx=0
        assert name == "RC10_C3_ROOM_TEMP_ALT"

    def test_known_rc10_c3_demand(self, monitor: BroadcastMonitor) -> None:
        """Test get_known_name returns correct name for RC10 C3 demand."""
        reading = BroadcastReading(
            can_id=0x0C1AC402,
            base=0x0402,
            idx=107,
            dlc=2,
            raw_data=b"\x00\xe1",
            raw_value=225,
            timestamp=0.0,
        )
        name = monitor.get_known_name(reading)
        assert name == "RC10_C3_DEMAND_TEMP"

    def test_known_dhw_temp(self, monitor: BroadcastMonitor) -> None:
        """Test get_known_name returns correct name for DHW temperature.

        NOTE: (0x0060, 58) was previously misidentified as DHW_TEMP_ACTUAL.
        Testing shows it's actually DHW_SETPOINT_OR_SUPPLY (~54°C).
        Actual DHW tank temp is at (0x0402, 78).
        """
        # Test the correct DHW temp mapping at base=0x0402, idx=78
        reading = BroadcastReading(
            can_id=0x0C138402,  # base 0x0402
            base=0x0402,
            idx=78,
            dlc=2,
            raw_data=b"\x01\x0e",  # 270 = 27.0°C
            raw_value=270,
            timestamp=0.0,
        )
        name = monitor.get_known_name(reading)
        assert name == "DHW_TEMP_ACTUAL"

    def test_unknown_reading_returns_none(self, monitor: BroadcastMonitor) -> None:
        """Test get_known_name returns None for unknown base/idx."""
        reading = BroadcastReading(
            can_id=0x0CFFFF00,
            base=0xFF00,  # Unknown base
            idx=999,  # Unknown idx
            dlc=2,
            raw_data=b"\x00\x00",
            raw_value=0,
            timestamp=0.0,
        )
        name = monitor.get_known_name(reading)
        assert name is None

    def test_unknown_idx_on_known_base_returns_none(
        self, monitor: BroadcastMonitor
    ) -> None:
        """Test get_known_name returns None for unknown idx on known base."""
        reading = BroadcastReading(
            can_id=0x0C000060,
            base=0x0060,  # Known base
            idx=999,  # Unknown idx for this base
            dlc=2,
            raw_data=b"\x00\x00",
            raw_value=0,
            timestamp=0.0,
        )
        name = monitor.get_known_name(reading)
        assert name is None

    def test_all_known_broadcasts_have_names(self, monitor: BroadcastMonitor) -> None:
        """Test that all entries in KNOWN_BROADCASTS have valid names."""
        for (base, idx), (name, _fmt) in KNOWN_BROADCASTS.items():
            reading = BroadcastReading(
                can_id=0x0C000000 | (idx << 14) | base,
                base=base,
                idx=idx,
                dlc=2,
                raw_data=b"\x00\x00",
                raw_value=0,
                timestamp=0.0,
            )
            result = monitor.get_known_name(reading)
            assert result == name, f"Expected {name} for base=0x{base:04X}, idx={idx}"


class TestParamToBroadcast:
    """Test PARAM_TO_BROADCAST mapping and helper functions."""

    def test_get_broadcast_for_gt2_temp(self) -> None:
        """Test get_broadcast_for_param returns correct mapping for GT2_TEMP.

        GT2_TEMP has base=None to search all circuit bases (0x0060-0x0063).
        """
        from buderus_wps.broadcast_monitor import get_broadcast_for_param

        result = get_broadcast_for_param("GT2_TEMP")
        assert result == (None, 12)

    def test_get_broadcast_for_gt3_temp_not_in_broadcast(self) -> None:
        """Test get_broadcast_for_param returns None for GT3_TEMP.

        GT3_TEMP (DHW temperature) is NOT available via broadcast monitoring.
        It must be read via RTR with the discovered parameter idx.
        The broadcast at (0x0402, 78) does NOT contain actual DHW tank temperature.
        """
        from buderus_wps.broadcast_monitor import get_broadcast_for_param

        result = get_broadcast_for_param("GT3_TEMP")
        assert result is None  # GT3 must be read via RTR, not broadcast

    def test_get_broadcast_case_insensitive(self) -> None:
        """Test get_broadcast_for_param is case-insensitive."""
        from buderus_wps.broadcast_monitor import get_broadcast_for_param

        assert get_broadcast_for_param("gt2_temp") == (None, 12)
        assert get_broadcast_for_param("Gt2_Temp") == (None, 12)
        assert get_broadcast_for_param("GT2_TEMP") == (None, 12)

    def test_get_broadcast_unknown_param(self) -> None:
        """Test get_broadcast_for_param returns None for unknown parameter."""
        from buderus_wps.broadcast_monitor import get_broadcast_for_param

        result = get_broadcast_for_param("UNKNOWN_PARAM")
        assert result is None

    def test_get_broadcast_empty_string(self) -> None:
        """Test get_broadcast_for_param handles empty string."""
        from buderus_wps.broadcast_monitor import get_broadcast_for_param

        result = get_broadcast_for_param("")
        assert result is None


class TestIsTemperatureParam:
    """Test is_temperature_param helper function."""

    def test_is_temperature_tem_format(self) -> None:
        """Test is_temperature_param returns True for 'tem' format."""
        from buderus_wps.broadcast_monitor import is_temperature_param

        assert is_temperature_param("tem") is True

    def test_is_temperature_temp_prefix(self) -> None:
        """Test is_temperature_param returns True for 'temp*' formats."""
        from buderus_wps.broadcast_monitor import is_temperature_param

        assert is_temperature_param("temp") is True
        assert is_temperature_param("temp1") is True
        assert is_temperature_param("temperature") is True

    def test_is_temperature_non_temp_format(self) -> None:
        """Test is_temperature_param returns False for non-temperature formats."""
        from buderus_wps.broadcast_monitor import is_temperature_param

        assert is_temperature_param("int") is False
        assert is_temperature_param("dp1") is False
        assert is_temperature_param("str") is False
        assert is_temperature_param("") is False
