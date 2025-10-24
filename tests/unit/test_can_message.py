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
        msg = CANMessage(arbitration_id=0x000, data=b'\x01\x02', is_extended_id=False)
        assert msg.arbitration_id == 0x000
        assert msg.data == b'\x01\x02'
        assert msg.is_extended_id is False

    def test_standard_frame_valid_id_max(self):
        """Standard frame with maximum valid ID (0x7FF)."""
        msg = CANMessage(arbitration_id=0x7FF, data=b'\x01\x02', is_extended_id=False)
        assert msg.arbitration_id == 0x7FF

    def test_standard_frame_invalid_id_too_large(self):
        """Standard frame with ID exceeding 11-bit range."""
        with pytest.raises(ValueError, match="Standard frame.*0x000.*0x7FF"):
            CANMessage(arbitration_id=0x800, data=b'\x01', is_extended_id=False)

    def test_standard_frame_invalid_id_negative(self):
        """Standard frame with negative ID."""
        with pytest.raises(ValueError, match="Standard frame.*0x000.*0x7FF"):
            CANMessage(arbitration_id=-1, data=b'\x01', is_extended_id=False)

    def test_extended_frame_valid_id_min(self):
        """Extended frame with minimum valid ID (0x00000000)."""
        msg = CANMessage(arbitration_id=0x00000000, data=b'\x01\x02', is_extended_id=True)
        assert msg.arbitration_id == 0x00000000
        assert msg.is_extended_id is True

    def test_extended_frame_valid_id_max(self):
        """Extended frame with maximum valid ID (0x1FFFFFFF)."""
        msg = CANMessage(arbitration_id=0x1FFFFFFF, data=b'\x01\x02', is_extended_id=True)
        assert msg.arbitration_id == 0x1FFFFFFF

    def test_extended_frame_invalid_id_too_large(self):
        """Extended frame with ID exceeding 32-bit range."""
        with pytest.raises(ValueError, match="Extended frame.*0x00000000.*0xFFFFFFFF"):
            CANMessage(arbitration_id=0x100000000, data=b'\x01', is_extended_id=True)

    def test_extended_frame_invalid_id_negative(self):
        """Extended frame with negative ID."""
        with pytest.raises(ValueError, match="Extended frame.*0x00000000.*0xFFFFFFFF"):
            CANMessage(arbitration_id=-1, data=b'\x01', is_extended_id=True)

    def test_valid_data_empty(self):
        """Message with empty data payload."""
        msg = CANMessage(arbitration_id=0x123, data=b'', is_extended_id=False)
        assert msg.data == b''
        assert len(msg.data) == 0

    def test_valid_data_max_length(self):
        """Message with 8-byte data payload (maximum)."""
        data = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        msg = CANMessage(arbitration_id=0x123, data=data, is_extended_id=False)
        assert msg.data == data
        assert len(msg.data) == 8

    def test_invalid_data_too_long(self):
        """Message with data payload exceeding 8 bytes."""
        with pytest.raises(ValueError, match="Data length must be 0-8 bytes"):
            CANMessage(arbitration_id=0x123, data=b'\x01' * 9, is_extended_id=False)

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
            arbitration_id=0x123,
            data=b'',
            is_extended_id=False,
            is_remote_frame=True
        )
        assert msg.is_remote_frame is True
        assert len(msg.data) == 0

    def test_remote_frame_with_data(self):
        """Remote frame with data payload (invalid)."""
        with pytest.raises(ValueError, match="Remote frames cannot contain data"):
            CANMessage(
                arbitration_id=0x123,
                data=b'\x01',
                is_extended_id=False,
                is_remote_frame=True
            )

    def test_timestamp_none_for_outbound(self):
        """Outbound message should have timestamp=None."""
        msg = CANMessage(arbitration_id=0x123, data=b'\x01', is_extended_id=False)
        assert msg.timestamp is None

    def test_timestamp_set_for_inbound(self):
        """Inbound message can have explicit timestamp."""
        msg = CANMessage(
            arbitration_id=0x123,
            data=b'\x01',
            is_extended_id=False,
            timestamp=1234567890.123
        )
        assert msg.timestamp == 1234567890.123


class TestCANMessageDLCProperty:
    """Test CANMessage.dlc property (Data Length Code)."""

    def test_dlc_empty_data(self):
        """DLC for message with no data."""
        msg = CANMessage(arbitration_id=0x123, data=b'', is_extended_id=False)
        assert msg.dlc == 0

    def test_dlc_one_byte(self):
        """DLC for message with 1 byte."""
        msg = CANMessage(arbitration_id=0x123, data=b'\x01', is_extended_id=False)
        assert msg.dlc == 1

    def test_dlc_four_bytes(self):
        """DLC for message with 4 bytes."""
        msg = CANMessage(arbitration_id=0x123, data=b'\x01\x02\x03\x04', is_extended_id=False)
        assert msg.dlc == 4

    def test_dlc_max_length(self):
        """DLC for message with 8 bytes (maximum)."""
        msg = CANMessage(
            arbitration_id=0x123,
            data=b'\x01\x02\x03\x04\x05\x06\x07\x08',
            is_extended_id=False
        )
        assert msg.dlc == 8

    def test_dlc_is_read_only(self):
        """DLC property should be read-only."""
        msg = CANMessage(arbitration_id=0x123, data=b'\x01\x02', is_extended_id=False)
        with pytest.raises(AttributeError):
            msg.dlc = 5  # type: ignore
