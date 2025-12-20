"""Contract tests for USBtin SLCAN protocol compliance.

Tests cover:
- T040: SLCAN protocol format compliance
"""

from unittest.mock import MagicMock, PropertyMock, patch

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage


class TestSLCANProtocolCompliance:
    """Test USBtin adapter SLCAN protocol compliance (T040)."""

    @patch("serial.Serial")
    def test_initialization_command_sequence(self, mock_serial_class):
        """Verify SLCAN initialization sends correct 7-command sequence."""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)
        mock_serial.read.return_value = b"\r"  # ACK
        mock_serial_class.return_value = mock_serial

        # Connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Verify exact command sequence per SLCAN protocol
        expected_commands = [
            b"C\r",  # Close channel (safety - 1st)
            b"C\r",  # Close channel (safety - 2nd)
            b"V\r",  # Get hardware version (1st query)
            b"V\r",  # Get hardware version (2nd query)
            b"v\r",  # Get firmware version
            b"S4\r",  # Set bitrate to 125 kbps (S4 = 125k)
            b"O\r",  # Open channel
        ]

        # Verify all commands sent in order
        assert mock_serial.write.call_count == len(expected_commands)
        for i, expected_cmd in enumerate(expected_commands):
            actual_cmd = mock_serial.write.call_args_list[i][0][0]
            assert (
                actual_cmd == expected_cmd
            ), f"Command {i} mismatch: expected {expected_cmd}, got {actual_cmd}"

    @patch("serial.Serial")
    def test_standard_frame_format_compliance(self, mock_serial_class):
        """Verify standard CAN frames use correct SLCAN format: t<III><L><DD...>\\r"""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        mock_serial.read.side_effect = init_responses + [b"t1234AABBCCDD\r"]
        mock_serial_class.return_value = mock_serial

        # Connect and send standard frame
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        msg = CANMessage(arbitration_id=0x123, data=b"\xaa\xbb\xcc\xdd")
        adapter.send_frame(msg, timeout=1.0)

        # Verify SLCAN format: t<III><L><DD...>\r
        # t = standard frame command
        # 123 = 3-digit hex ID
        # 4 = DLC (4 bytes)
        # AABBCCDD = data in hex
        # \r = terminator
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        frame_writes = write_calls[7:]  # Skip init commands

        assert b"t1234AABBCCDD\r" in frame_writes

    @patch("serial.Serial")
    def test_extended_frame_format_compliance(self, mock_serial_class):
        """Verify extended CAN frames use correct SLCAN format: T<IIIIIIII><L><DD...>\\r"""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        mock_serial.read.side_effect = init_responses + [b"T31D011E93123445\r"]
        mock_serial_class.return_value = mock_serial

        # Connect and send extended frame
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        msg = CANMessage(
            arbitration_id=0x31D011E9, data=b"\x12\x34\x45", is_extended_id=True
        )
        adapter.send_frame(msg, timeout=1.0)

        # Verify SLCAN format: T<IIIIIIII><L><DD...>\r
        # T = extended frame command
        # 31D011E9 = 8-digit hex ID
        # 3 = DLC (3 bytes)
        # 123445 = data in hex
        # \r = terminator
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        frame_writes = write_calls[7:]

        assert b"T31D011E93123445\r" in frame_writes

    @patch("serial.Serial")
    def test_remote_frame_format_compliance(self, mock_serial_class):
        """Verify remote frames use correct SLCAN format: r<III><L>\\r or R<IIIIIIII><L>\\r"""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        # Remote frames have no data, just DLC
        mock_serial.read.side_effect = init_responses + [b"r1234\r", b"R31D011E98\r"]
        mock_serial_class.return_value = mock_serial

        # Connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Send standard remote frame
        msg1 = CANMessage(
            arbitration_id=0x123, data=b"", is_remote_frame=True, _requested_dlc=4
        )
        adapter.send_frame(msg1, timeout=1.0)

        # Send extended remote frame
        msg2 = CANMessage(
            arbitration_id=0x31D011E9,
            data=b"",
            is_extended_id=True,
            is_remote_frame=True,
            _requested_dlc=8,
        )
        adapter.send_frame(msg2, timeout=1.0)

        # Verify SLCAN formats
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        frame_writes = write_calls[7:]

        # r<III><L>\r - standard remote
        assert b"r1234\r" in frame_writes
        # R<IIIIIIII><L>\r - extended remote
        assert b"R31D011E98\r" in frame_writes

    @patch("serial.Serial")
    def test_carriage_return_terminator_required(self, mock_serial_class):
        """Verify all SLCAN commands and frames end with \\r (CR)."""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        mock_serial.read.side_effect = init_responses + [b"t1231AA\r"]
        mock_serial_class.return_value = mock_serial

        # Connect and send frame
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        msg = CANMessage(arbitration_id=0x123, data=b"\xaa")
        adapter.send_frame(msg, timeout=1.0)

        # Verify ALL commands end with \r
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]

        for cmd in write_calls:
            assert cmd.endswith(b"\r"), f"Command {cmd} does not end with \\r"

    @patch("serial.Serial")
    def test_bitrate_command_format(self, mock_serial_class):
        """Verify bitrate command follows SLCAN format: S<N>\\r"""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        # Connect with default 125 kbps
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Verify S4 command (125 kbps) was sent
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        assert b"S4\r" in write_calls

    @patch("serial.Serial")
    def test_hex_uppercase_compliance(self, mock_serial_class):
        """Verify all hex digits in SLCAN frames are uppercase."""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)

        init_responses = [b"\r"] * 7
        mock_serial.read.side_effect = init_responses + [b"T31D011E94DEADBEEF\r"]
        mock_serial_class.return_value = mock_serial

        # Connect and send frame with hex data
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        msg = CANMessage(
            arbitration_id=0x31D011E9, data=b"\xde\xad\xbe\xef", is_extended_id=True
        )
        adapter.send_frame(msg, timeout=1.0)

        # Verify hex is uppercase
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        frame_writes = write_calls[7:]

        # Should be uppercase: T31D011E94DEADBEEF\r
        assert b"T31D011E94DEADBEEF\r" in frame_writes
        # Should NOT contain lowercase hex
        for frame in frame_writes:
            frame_str = frame.decode("ascii")
            # Check that hex digits are uppercase (after command character)
            if frame_str[0] in "tTrR":
                hex_part = frame_str[1:-1]  # Remove command char and \r
                assert (
                    hex_part == hex_part.upper()
                ), f"Frame contains lowercase hex: {frame}"

    @patch("serial.Serial")
    def test_close_command_format(self, mock_serial_class):
        """Verify close command follows SLCAN format: C\\r"""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        # Connect
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Verify C\r commands sent during init (2x for safety)
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        close_commands = [cmd for cmd in write_calls if cmd == b"C\r"]

        # Should have at least 2 close commands at start of init
        assert len(close_commands) >= 2

    @patch("serial.Serial")
    def test_open_command_format(self, mock_serial_class):
        """Verify open command follows SLCAN format: O\\r"""
        # Setup mock
        mock_serial = MagicMock()
        mock_serial.is_open = True
        type(mock_serial).in_waiting = PropertyMock(return_value=10)
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        # Connect
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Verify O\r command sent as last init command
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]

        # Last command should be Open
        assert write_calls[-1] == b"O\r"
