"""Unit tests for CANMessage dataclass validation and properties.

Tests cover:
- T016: CANMessage.__init__() validation (ID ranges, data length)
- T017: CANMessage.dlc property
"""

import pytest

from buderus_wps.can_message import CANMessage


class TestCANMessageInitialization:
    """Test CANMessage initialization and validation."""

    def test_standard_frame_valid_id_min(self):
        """Standard frame with minimum valid ID (0x000)."""
        msg = CANMessage(arbitration_id=0x000, data=b"\x01\x02", is_extended_id=False)
        assert msg.arbitration_id == 0x000
        assert msg.data == b"\x01\x02"
        assert msg.is_extended_id is False

    def test_standard_frame_valid_id_max(self):
        """Standard frame with maximum valid ID (0x7FF)."""
        msg = CANMessage(arbitration_id=0x7FF, data=b"\x01\x02", is_extended_id=False)
        assert msg.arbitration_id == 0x7FF

    def test_standard_frame_invalid_id_too_large(self):
        """Standard frame with ID exceeding 11-bit range."""
        with pytest.raises(ValueError, match="Standard frame.*0x000.*0x7FF"):
            CANMessage(arbitration_id=0x800, data=b"\x01", is_extended_id=False)

    def test_standard_frame_invalid_id_negative(self):
        """Standard frame with negative ID."""
        with pytest.raises(ValueError, match="Standard frame.*0x000.*0x7FF"):
            CANMessage(arbitration_id=-1, data=b"\x01", is_extended_id=False)

    def test_extended_frame_valid_id_min(self):
        """Extended frame with minimum valid ID (0x00000000)."""
        msg = CANMessage(
            arbitration_id=0x00000000, data=b"\x01\x02", is_extended_id=True
        )
        assert msg.arbitration_id == 0x00000000
        assert msg.is_extended_id is True

    def test_extended_frame_valid_id_max(self):
        """Extended frame with maximum valid ID (0x1FFFFFFF)."""
        msg = CANMessage(
            arbitration_id=0x1FFFFFFF, data=b"\x01\x02", is_extended_id=True
        )
        assert msg.arbitration_id == 0x1FFFFFFF

    def test_extended_frame_invalid_id_too_large(self):
        """Extended frame with ID exceeding 32-bit range."""
        with pytest.raises(ValueError, match="Extended frame.*0x00000000.*0xFFFFFFFF"):
            CANMessage(arbitration_id=0x100000000, data=b"\x01", is_extended_id=True)

    def test_extended_frame_invalid_id_negative(self):
        """Extended frame with negative ID."""
        with pytest.raises(ValueError, match="Extended frame.*0x00000000.*0xFFFFFFFF"):
            CANMessage(arbitration_id=-1, data=b"\x01", is_extended_id=True)

    def test_valid_data_empty(self):
        """Message with empty data payload."""
        msg = CANMessage(arbitration_id=0x123, data=b"", is_extended_id=False)
        assert msg.data == b""
        assert len(msg.data) == 0

    def test_valid_data_max_length(self):
        """Message with 8-byte data payload (maximum)."""
        data = b"\x01\x02\x03\x04\x05\x06\x07\x08"
        msg = CANMessage(arbitration_id=0x123, data=data, is_extended_id=False)
        assert msg.data == data
        assert len(msg.data) == 8

    def test_invalid_data_too_long(self):
        """Message with data payload exceeding 8 bytes."""
        with pytest.raises(ValueError, match="Data length must be 0-8 bytes"):
            CANMessage(arbitration_id=0x123, data=b"\x01" * 9, is_extended_id=False)

    def test_invalid_data_type_string(self):
        """Message with string instead of bytes for data."""
        with pytest.raises(TypeError, match="Data must be bytes"):
            CANMessage(arbitration_id=0x123, data="test", is_extended_id=False)  # type: ignore

    def test_invalid_data_type_list(self):
        """Message with list instead of bytes for data."""
        with pytest.raises(TypeError, match="Data must be bytes"):
            CANMessage(arbitration_id=0x123, data=[1, 2, 3], is_extended_id=False)  # type: ignore

    def test_remote_frame_empty_data(self):
        """Remote frame with empty data (valid)."""
        msg = CANMessage(
            arbitration_id=0x123, data=b"", is_extended_id=False, is_remote_frame=True
        )
        assert msg.is_remote_frame is True
        assert len(msg.data) == 0

    def test_remote_frame_with_data(self):
        """Remote frame with data payload (invalid)."""
        with pytest.raises(ValueError, match="Remote frames cannot contain data"):
            CANMessage(
                arbitration_id=0x123,
                data=b"\x01",
                is_extended_id=False,
                is_remote_frame=True,
            )

    def test_timestamp_none_for_outbound(self):
        """Outbound message should have timestamp=None."""
        msg = CANMessage(arbitration_id=0x123, data=b"\x01", is_extended_id=False)
        assert msg.timestamp is None

    def test_timestamp_set_for_inbound(self):
        """Inbound message can have explicit timestamp."""
        msg = CANMessage(
            arbitration_id=0x123,
            data=b"\x01",
            is_extended_id=False,
            timestamp=1234567890.123,
        )
        assert msg.timestamp == 1234567890.123


class TestCANMessageDLCProperty:
    """Test CANMessage.dlc property (Data Length Code)."""

    def test_dlc_empty_data(self):
        """DLC for message with no data."""
        msg = CANMessage(arbitration_id=0x123, data=b"", is_extended_id=False)
        assert msg.dlc == 0

    def test_dlc_one_byte(self):
        """DLC for message with 1 byte."""
        msg = CANMessage(arbitration_id=0x123, data=b"\x01", is_extended_id=False)
        assert msg.dlc == 1

    def test_dlc_four_bytes(self):
        """DLC for message with 4 bytes."""
        msg = CANMessage(
            arbitration_id=0x123, data=b"\x01\x02\x03\x04", is_extended_id=False
        )
        assert msg.dlc == 4

    def test_dlc_max_length(self):
        """DLC for message with 8 bytes (maximum)."""
        msg = CANMessage(
            arbitration_id=0x123,
            data=b"\x01\x02\x03\x04\x05\x06\x07\x08",
            is_extended_id=False,
        )
        assert msg.dlc == 8

    def test_dlc_is_read_only(self):
        """DLC property should be read-only."""
        msg = CANMessage(arbitration_id=0x123, data=b"\x01\x02", is_extended_id=False)
        with pytest.raises(AttributeError):
            msg.dlc = 5  # type: ignore


class TestCANMessageDecodeBroadcastId:
    """Test CANMessage.decode_broadcast_id() method.

    T071: Unit tests for decode_broadcast_id() method
    T072: Unit tests for CAN ID prefix extraction
    T073: Unit tests for element type extraction

    CAN ID Structure (Broadcast Data) from hardware verification:
        Bits 31-24: Prefix (0x0C = data, 0x00 = status, 0x08 = counter)
        Bits 23-12: Parameter Index
        Bits 11-0:  Element Type (0x060-0x063 = E21/E22/E31/E32)
    """

    # T071: Basic decode_broadcast_id() functionality

    def test_decode_data_frame_gt1_temperature(self):
        """Decode CAN ID 0x0C084060 - GT1 temperature (hardware verified)."""
        msg = CANMessage(
            arbitration_id=0x0C084060,
            data=b"\x00\xd6",  # 214 = 21.4°C
            is_extended_id=True,
        )
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0x0C  # Data/response prefix
        assert param_idx == 0x084  # Parameter index 132
        assert element_type == 0x060  # E21 element type

    def test_decode_data_frame_gt1_unit2(self):
        """Decode CAN ID 0x0C084061 - GT1-2 temperature."""
        msg = CANMessage(
            arbitration_id=0x0C084061,
            data=b"\x00\xe9",  # 233 = 23.3°C
            is_extended_id=True,
        )
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0x0C
        assert param_idx == 0x084
        assert element_type == 0x061  # E22 element type

    def test_decode_data_frame_gt8_temperature(self):
        """Decode CAN ID 0x0C0E8060 - GT8 temperature (hardware verified)."""
        msg = CANMessage(
            arbitration_id=0x0C0E8060,
            data=b"\x02\x28",  # 552 = 55.2°C
            is_extended_id=True,
        )
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0x0C
        assert param_idx == 0x0E8  # Parameter index 232
        assert element_type == 0x060

    # T072: Prefix extraction tests

    def test_decode_status_prefix(self):
        """Decode CAN ID with status prefix 0x00 (hardware verified)."""
        msg = CANMessage(arbitration_id=0x00008060, data=b"\x04", is_extended_id=True)
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0x00  # Status prefix
        assert param_idx == 0x008
        assert element_type == 0x060

    def test_decode_counter_prefix(self):
        """Decode CAN ID with counter prefix 0x08."""
        msg = CANMessage(
            arbitration_id=0x08000270,
            data=b"\x01\x95",  # Counter value 405
            is_extended_id=True,
        )
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0x08  # Counter prefix
        assert param_idx == 0x000
        assert element_type == 0x270  # Counter element type

    def test_decode_response_prefix(self):
        """Decode CAN ID with response prefix 0x0C."""
        msg = CANMessage(
            arbitration_id=0x0C000060,
            data=b"\x00\xc9",  # 201 = 20.1°C
            is_extended_id=True,
        )
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0x0C  # Response/data prefix
        assert param_idx == 0x000
        assert element_type == 0x060

    # T073: Element type extraction tests

    def test_decode_element_e21(self):
        """Decode element type E21 (0x060)."""
        msg = CANMessage(arbitration_id=0x0C084060, data=b"\x00", is_extended_id=True)
        _, _, element_type = msg.decode_broadcast_id()
        assert element_type == 0x060

    def test_decode_element_e22(self):
        """Decode element type E22 (0x061)."""
        msg = CANMessage(arbitration_id=0x0C084061, data=b"\x00", is_extended_id=True)
        _, _, element_type = msg.decode_broadcast_id()
        assert element_type == 0x061

    def test_decode_element_e31(self):
        """Decode element type E31 (0x062)."""
        msg = CANMessage(arbitration_id=0x0C084062, data=b"\x00", is_extended_id=True)
        _, _, element_type = msg.decode_broadcast_id()
        assert element_type == 0x062

    def test_decode_element_e32(self):
        """Decode element type E32 (0x063)."""
        msg = CANMessage(arbitration_id=0x0C084063, data=b"\x00", is_extended_id=True)
        _, _, element_type = msg.decode_broadcast_id()
        assert element_type == 0x063

    def test_decode_element_counter(self):
        """Decode element type for counter (0x270)."""
        msg = CANMessage(arbitration_id=0x08000270, data=b"\x00", is_extended_id=True)
        _, _, element_type = msg.decode_broadcast_id()
        assert element_type == 0x270

    def test_decode_element_config(self):
        """Decode element type for config (0x403)."""
        msg = CANMessage(arbitration_id=0x0C000403, data=b"\x00", is_extended_id=True)
        _, _, element_type = msg.decode_broadcast_id()
        assert element_type == 0x403

    # Edge cases

    def test_decode_zero_id(self):
        """Decode CAN ID 0x00000000."""
        msg = CANMessage(arbitration_id=0x00000000, data=b"\x00", is_extended_id=True)
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0x00
        assert param_idx == 0x000
        assert element_type == 0x000

    def test_decode_max_id(self):
        """Decode CAN ID with maximum values."""
        msg = CANMessage(arbitration_id=0xFFFFFFFF, data=b"\x00", is_extended_id=True)
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0xFF
        assert param_idx == 0xFFF
        assert element_type == 0xFFF

    def test_decode_outdoor_temp(self):
        """Decode CAN ID 0x00030060 - Outdoor temperature (hardware verified)."""
        msg = CANMessage(
            arbitration_id=0x00030060, data=b"\x37", is_extended_id=True  # 55 = 5.5°C
        )
        prefix, param_idx, element_type = msg.decode_broadcast_id()
        assert prefix == 0x00
        # Bits 23-12: (0x00030060 >> 12) & 0xFFF = 0x030 = 48
        assert param_idx == 0x030
        assert element_type == 0x060


class TestCANMessagePrefixConstants:
    """Test CAN ID prefix constants.

    T075: Verify constants for known prefixes are defined.
    """

    def test_prefix_data_constant_exists(self):
        """CAN_PREFIX_DATA constant should be 0x0C."""
        from buderus_wps.can_message import CAN_PREFIX_DATA

        assert CAN_PREFIX_DATA == 0x0C

    def test_prefix_status_constant_exists(self):
        """CAN_PREFIX_STATUS constant should be 0x00."""
        from buderus_wps.can_message import CAN_PREFIX_STATUS

        assert CAN_PREFIX_STATUS == 0x00

    def test_prefix_counter_constant_exists(self):
        """CAN_PREFIX_COUNTER constant should be 0x08."""
        from buderus_wps.can_message import CAN_PREFIX_COUNTER

        assert CAN_PREFIX_COUNTER == 0x08


class TestCANMessageElementTypeConstants:
    """Test CAN element type constants.

    T076: Verify constants for element types are defined.
    """

    def test_element_e21_constant_exists(self):
        """ELEMENT_E21 constant should be 0x060."""
        from buderus_wps.can_message import ELEMENT_E21

        assert ELEMENT_E21 == 0x060

    def test_element_e22_constant_exists(self):
        """ELEMENT_E22 constant should be 0x061."""
        from buderus_wps.can_message import ELEMENT_E22

        assert ELEMENT_E22 == 0x061

    def test_element_e31_constant_exists(self):
        """ELEMENT_E31 constant should be 0x062."""
        from buderus_wps.can_message import ELEMENT_E31

        assert ELEMENT_E31 == 0x062

    def test_element_e32_constant_exists(self):
        """ELEMENT_E32 constant should be 0x063."""
        from buderus_wps.can_message import ELEMENT_E32

        assert ELEMENT_E32 == 0x063

    def test_element_counter_constant_exists(self):
        """ELEMENT_COUNTER constant should be 0x270."""
        from buderus_wps.can_message import ELEMENT_COUNTER

        assert ELEMENT_COUNTER == 0x270

    def test_element_config_constant_exists(self):
        """ELEMENT_CONFIG constant should be 0x403."""
        from buderus_wps.can_message import ELEMENT_CONFIG

        assert ELEMENT_CONFIG == 0x403
