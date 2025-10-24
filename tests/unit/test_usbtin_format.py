"""Unit tests for CANMessage SLCAN (USBtin) format conversion.

Tests cover:
- T018: CANMessage.to_usbtin_format() standard frames
- T019: CANMessage.to_usbtin_format() extended frames
- T020: CANMessage.from_usbtin_format() parsing
"""

import pytest
from buderus_wps.can_message import CANMessage


class TestToUSBtinFormatStandard:
    """Test CANMessage.to_usbtin_format() for standard (11-bit) frames."""

    def test_standard_frame_no_data(self):
        """Standard frame with no data: t<III><0>\r"""
        msg = CANMessage(arbitration_id=0x123, data=b'', is_extended_id=False)
        assert msg.to_usbtin_format() == "t1230\r"

    def test_standard_frame_one_byte(self):
        """Standard frame with 1 byte data."""
        msg = CANMessage(arbitration_id=0x456, data=b'\xAB', is_extended_id=False)
        assert msg.to_usbtin_format() == "t4561AB\r"

    def test_standard_frame_four_bytes(self):
        """Standard frame with 4 bytes data."""
        msg = CANMessage(arbitration_id=0x014, data=b'\x11\x22\x33\x44', is_extended_id=False)
        assert msg.to_usbtin_format() == "t014411223344\r"

    def test_standard_frame_max_data(self):
        """Standard frame with 8 bytes data (maximum)."""
        msg = CANMessage(
            arbitration_id=0x7FF,
            data=b'\x01\x02\x03\x04\x05\x06\x07\x08',
            is_extended_id=False
        )
        assert msg.to_usbtin_format() == "t7FF80102030405060708\r"

    def test_standard_frame_id_padding(self):
        """Standard frame ID should be padded to 3 hex digits."""
        msg = CANMessage(arbitration_id=0x001, data=b'\xFF', is_extended_id=False)
        assert msg.to_usbtin_format() == "t0011FF\r"

    def test_standard_remote_frame(self):
        """Standard remote frame: r<III><DLC>\r"""
        msg = CANMessage(
            arbitration_id=0x123,
            data=b'',
            is_extended_id=False,
            is_remote_frame=True
        )
        assert msg.to_usbtin_format() == "r1230\r"


class TestToUSBtinFormatExtended:
    """Test CANMessage.to_usbtin_format() for extended (29-bit) frames."""

    def test_extended_frame_no_data(self):
        """Extended frame with no data: T<IIIIIIII><0>\r"""
        msg = CANMessage(arbitration_id=0x12345678, data=b'', is_extended_id=True)
        assert msg.to_usbtin_format() == "T123456780\r"

    def test_extended_frame_two_bytes(self):
        """Extended frame with 2 bytes data (common Buderus read request)."""
        msg = CANMessage(arbitration_id=0x31D011E9, data=b'\x00\x37', is_extended_id=True)
        assert msg.to_usbtin_format() == "T31D011E920037\r"

    def test_extended_frame_max_data(self):
        """Extended frame with 8 bytes data."""
        msg = CANMessage(
            arbitration_id=0x1FFFFFFF,
            data=b'\xAA\xBB\xCC\xDD\xEE\xFF\x00\x11',
            is_extended_id=True
        )
        assert msg.to_usbtin_format() == "T1FFFFFFF8AABBCCDDEEFF0011\r"

    def test_extended_frame_id_padding(self):
        """Extended frame ID should be padded to 8 hex digits."""
        msg = CANMessage(arbitration_id=0x00000001, data=b'\x42', is_extended_id=True)
        assert msg.to_usbtin_format() == "T00000001142\r"

    def test_extended_remote_frame(self):
        """Extended remote frame: R<IIIIIIII><DLC>\r"""
        msg = CANMessage(
            arbitration_id=0x01FD7FE0,
            data=b'',
            is_extended_id=True,
            is_remote_frame=True
        )
        assert msg.to_usbtin_format() == "R01FD7FE00\r"


class TestFromUSBtinFormat:
    """Test CANMessage.from_usbtin_format() parsing."""

    def test_parse_standard_frame_no_data(self):
        """Parse standard frame with no data."""
        msg = CANMessage.from_usbtin_format("t1230\r")
        assert msg.arbitration_id == 0x123
        assert msg.data == b''
        assert msg.is_extended_id is False
        assert msg.is_remote_frame is False
        assert msg.dlc == 0

    def test_parse_standard_frame_with_data(self):
        """Parse standard frame with data."""
        msg = CANMessage.from_usbtin_format("t014411223344\r")
        assert msg.arbitration_id == 0x014
        assert msg.data == b'\x11\x22\x33\x44'
        assert msg.is_extended_id is False
        assert msg.dlc == 4

    def test_parse_standard_frame_max_data(self):
        """Parse standard frame with 8 bytes."""
        msg = CANMessage.from_usbtin_format("t7FF80102030405060708\r")
        assert msg.arbitration_id == 0x7FF
        assert msg.data == b'\x01\x02\x03\x04\x05\x06\x07\x08'
        assert msg.dlc == 8

    def test_parse_extended_frame_no_data(self):
        """Parse extended frame with no data."""
        msg = CANMessage.from_usbtin_format("T123456780\r")
        assert msg.arbitration_id == 0x12345678
        assert msg.data == b''
        assert msg.is_extended_id is True
        assert msg.is_remote_frame is False

    def test_parse_extended_frame_with_data(self):
        """Parse extended frame with data (typical Buderus response)."""
        msg = CANMessage.from_usbtin_format("T31D011E920037\r")
        assert msg.arbitration_id == 0x31D011E9
        assert msg.data == b'\x00\x37'
        assert msg.is_extended_id is True
        assert msg.dlc == 2

    def test_parse_standard_remote_frame(self):
        """Parse standard remote frame."""
        msg = CANMessage.from_usbtin_format("r1234\r")
        assert msg.arbitration_id == 0x123
        assert msg.data == b''
        assert msg.is_extended_id is False
        assert msg.is_remote_frame is True
        assert msg.dlc == 4  # DLC specified in remote frame

    def test_parse_extended_remote_frame(self):
        """Parse extended remote frame."""
        msg = CANMessage.from_usbtin_format("R01FD7FE08\r")
        assert msg.arbitration_id == 0x01FD7FE0
        assert msg.data == b''
        assert msg.is_extended_id is True
        assert msg.is_remote_frame is True
        assert msg.dlc == 8

    def test_parse_without_cr_terminator(self):
        """Parse frame without \\r terminator (should still work)."""
        msg = CANMessage.from_usbtin_format("t1231AB")
        assert msg.arbitration_id == 0x123
        assert msg.data == b'\xAB'

    def test_parse_invalid_format_too_short(self):
        """Parse invalid frame (too short)."""
        with pytest.raises(ValueError, match="Invalid SLCAN frame format"):
            CANMessage.from_usbtin_format("t12")

    def test_parse_invalid_format_bad_command(self):
        """Parse invalid command character."""
        with pytest.raises(ValueError, match="Invalid SLCAN frame format"):
            CANMessage.from_usbtin_format("X1230\r")

    def test_parse_invalid_hex_characters(self):
        """Parse frame with invalid hex characters."""
        with pytest.raises(ValueError, match="Invalid hexadecimal"):
            CANMessage.from_usbtin_format("t12G1AB\r")

    def test_parse_data_length_mismatch(self):
        """Parse frame where DLC doesn't match data length."""
        with pytest.raises(ValueError, match="Data length mismatch"):
            CANMessage.from_usbtin_format("t1234AB\r")  # DLC=4 but only 1 byte

    def test_roundtrip_standard_frame(self):
        """Roundtrip: message → SLCAN → message (standard)."""
        original = CANMessage(arbitration_id=0x456, data=b'\x11\x22\x33', is_extended_id=False)
        slcan = original.to_usbtin_format()
        parsed = CANMessage.from_usbtin_format(slcan)
        assert parsed.arbitration_id == original.arbitration_id
        assert parsed.data == original.data
        assert parsed.is_extended_id == original.is_extended_id

    def test_roundtrip_extended_frame(self):
        """Roundtrip: message → SLCAN → message (extended)."""
        original = CANMessage(
            arbitration_id=0x31D011E9,
            data=b'\xAA\xBB\xCC\xDD',
            is_extended_id=True
        )
        slcan = original.to_usbtin_format()
        parsed = CANMessage.from_usbtin_format(slcan)
        assert parsed.arbitration_id == original.arbitration_id
        assert parsed.data == original.data
        assert parsed.is_extended_id == original.is_extended_id
