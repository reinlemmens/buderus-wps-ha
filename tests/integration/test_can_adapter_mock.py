"""Integration tests for USBtinAdapter with mocked serial port.

Tests cover:
- T022: USBtinAdapter.connect() with mocked serial
- T023: USBtinAdapter.disconnect() with mocked serial
- T024: USBtinAdapter.is_open property
- T039: Sequential message transmission
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage
from buderus_wps.exceptions import DeviceNotFoundError, DeviceInitializationError


class TestUSBtinAdapterConnect:
    """Test USBtinAdapter.connect() with mocked serial port."""

    @patch('serial.Serial')
    def test_connect_success(self, mock_serial_class):
        """Successfully connect to USBtin device."""
        # Setup mock serial port
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'  # ACK response
        mock_serial_class.return_value = mock_serial

        # Connect
        adapter = USBtinAdapter('/dev/ttyACM0')
        result = adapter.connect()

        # Verify serial port opened
        mock_serial_class.assert_called_once_with(
            '/dev/ttyACM0',
            baudrate=115200,
            timeout=1.0,
            write_timeout=1.0
        )

        # Verify initialization sequence sent
        expected_commands = [
            b'C\r',  # Close channel (1st)
            b'C\r',  # Close channel (2nd)
            b'V\r',  # Hardware version (1st)
            b'V\r',  # Hardware version (2nd)
            b'v\r',  # Firmware version
            b'S4\r', # Set bitrate 125 kbps
            b'O\r'   # Open channel
        ]

        # Check all commands were written
        assert mock_serial.write.call_count == len(expected_commands)
        for i, expected_cmd in enumerate(expected_commands):
            assert mock_serial.write.call_args_list[i][0][0] == expected_cmd

        # Verify return value
        assert result is adapter
        assert adapter.is_open is True

    @patch('serial.Serial')
    def test_connect_device_not_found(self, mock_serial_class):
        """Connect fails when serial port doesn't exist."""
        mock_serial_class.side_effect = FileNotFoundError("Port not found")

        adapter = USBtinAdapter('/dev/ttyACM0')
        with pytest.raises(DeviceNotFoundError, match="Serial port.*not found"):
            adapter.connect()

        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_connect_permission_denied(self, mock_serial_class):
        """Connect fails when user lacks permission."""
        mock_serial_class.side_effect = PermissionError("Permission denied")

        adapter = USBtinAdapter('/dev/ttyACM0')
        with pytest.raises(DeviceNotFoundError, match="Permission denied"):
            adapter.connect()

    @patch('serial.Serial')
    def test_connect_initialization_fails_nak(self, mock_serial_class):
        """Connect fails when device returns NAK (\\a) during init."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\a'  # NAK/Error response
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')
        with pytest.raises(DeviceInitializationError, match="Device returned error"):
            adapter.connect()

        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_connect_already_connected(self, mock_serial_class):
        """Connect when already connected should raise error."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()

        # Try to connect again
        with pytest.raises(RuntimeError, match="Already connected"):
            adapter.connect()

    @patch('serial.Serial')
    def test_connect_with_context_manager(self, mock_serial_class):
        """Connect using context manager (with statement)."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        with USBtinAdapter('/dev/ttyACM0') as adapter:
            assert adapter.is_open is True

        # After exiting context, should be closed
        mock_serial.close.assert_called()


class TestUSBtinAdapterDisconnect:
    """Test USBtinAdapter.disconnect() with mocked serial port."""

    @patch('serial.Serial')
    def test_disconnect_success(self, mock_serial_class):
        """Successfully disconnect from USBtin device."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()
        adapter.disconnect()

        # Verify close command sent
        # Find the 'C\r' command after open (last close command)
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        assert b'C\r' in write_calls[-1:] or mock_serial.close.called

        # Verify serial port closed
        mock_serial.close.assert_called()
        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_disconnect_when_not_connected(self, mock_serial_class):
        """Disconnect when not connected should be no-op."""
        adapter = USBtinAdapter('/dev/ttyACM0')

        # Should not raise error
        adapter.disconnect()
        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_disconnect_handles_errors_gracefully(self, mock_serial_class):
        """Disconnect should not raise errors during cleanup."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial.close.side_effect = Exception("Serial port error")
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()

        # Should not raise exception
        adapter.disconnect()
        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_disconnect_via_context_manager(self, mock_serial_class):
        """Disconnect automatically when exiting context manager."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')

        with adapter:
            assert adapter.is_open is True

        # After context, should be disconnected
        assert adapter.is_open is False
        mock_serial.close.assert_called()


class TestUSBtinAdapterIsOpen:
    """Test USBtinAdapter.is_open property."""

    def test_is_open_before_connect(self):
        """is_open should be False before connecting."""
        adapter = USBtinAdapter('/dev/ttyACM0')
        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_is_open_after_connect(self, mock_serial_class):
        """is_open should be True after successful connect."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()
        assert adapter.is_open is True

    @patch('serial.Serial')
    def test_is_open_after_disconnect(self, mock_serial_class):
        """is_open should be False after disconnect."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()
        adapter.disconnect()
        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_is_open_reflects_serial_state(self, mock_serial_class):
        """is_open should reflect actual serial port state."""
        mock_serial = MagicMock()
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')

        # Initially closed
        mock_serial.is_open = False
        assert adapter.is_open is False

        # After connect
        adapter.connect()
        mock_serial.is_open = True
        assert adapter.is_open is True

        # After disconnect
        adapter.disconnect()
        mock_serial.is_open = False
        assert adapter.is_open is False


class TestSequentialMessageTransmission:
    """Test sequential message transmission (T039)."""

    @patch('serial.Serial')
    def test_send_multiple_frames_sequentially(self, mock_serial_class):
        """T039: Send multiple CAN frames in sequence."""
        # Setup mock serial port with buffer for responses
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 10

        # Simulate initialization + 3 message responses
        init_responses = [b'\r'] * 7  # 7 init commands
        message_responses = [
            b't12344AABBCCDD\r',  # Response 1 (ID=0x123, DLC=4, Data=AABBCCDD)
            b't23454455666777\r',  # Response 2 (ID=0x234, DLC=5, Data=4455666777)
            b'T31D011E9100\r',     # Response 3 (ID=0x31D011E9, DLC=1, Data=00)
        ]
        mock_serial.read.side_effect = init_responses + message_responses
        mock_serial_class.return_value = mock_serial

        # Create and connect adapter
        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()

        # Send first message
        msg1 = CANMessage(arbitration_id=0x123, data=b'\xAA\xBB\xCC\xDD')
        response1 = adapter.send_frame(msg1, timeout=1.0)

        assert response1 is not None
        assert response1.arbitration_id == 0x123
        assert response1.data == b'\xAA\xBB\xCC\xDD'

        # Send second message
        msg2 = CANMessage(arbitration_id=0x234, data=b'\x44\x55\x66\x67\x77')
        response2 = adapter.send_frame(msg2, timeout=1.0)

        assert response2 is not None
        assert response2.arbitration_id == 0x234
        assert response2.data == b'\x44\x55\x66\x67\x77'

        # Send third message (extended ID)
        msg3 = CANMessage(arbitration_id=0x31D011E9, data=b'\x00', is_extended_id=True)
        response3 = adapter.send_frame(msg3, timeout=1.0)

        assert response3 is not None
        assert response3.arbitration_id == 0x31D011E9
        assert response3.is_extended_id is True

        # Verify all three messages were written in order
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        # Skip the 7 init commands and verify message order
        message_writes = write_calls[7:]
        assert b't12344AABBCCDD\r' in message_writes
        assert b't23454455666777\r' in message_writes  # DLC=5, 5 bytes = 10 hex chars
        assert b'T31D011E9100\r' in message_writes

    @patch('serial.Serial')
    def test_receive_multiple_frames_passively(self, mock_serial_class):
        """Receive multiple CAN frames passively in sequence."""
        # Setup mock serial port
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 10

        # Simulate initialization + passive frames
        init_responses = [b'\r'] * 7
        passive_frames = [
            b't11121122\r',        # Frame 1 (ID=0x111, DLC=2, Data=1122)
            b't22222244\r',        # Frame 2 (ID=0x222, DLC=2, Data=2244)
            b'T31D011E928666\r',   # Frame 3 (ID=0x31D011E9, DLC=2, Data=8666)
        ]
        mock_serial.read.side_effect = init_responses + passive_frames
        mock_serial_class.return_value = mock_serial

        # Create and connect adapter
        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()

        # Receive first frame
        frame1 = adapter.receive_frame(timeout=1.0)
        assert frame1.arbitration_id == 0x111
        assert frame1.data == b'\x11\x22'

        # Receive second frame
        frame2 = adapter.receive_frame(timeout=1.0)
        assert frame2.arbitration_id == 0x222
        assert frame2.data == b'\x22\x44'

        # Receive third frame (extended ID)
        frame3 = adapter.receive_frame(timeout=1.0)
        assert frame3.arbitration_id == 0x31D011E9
        assert frame3.data == b'\x86\x66'
        assert frame3.is_extended_id is True

    @patch('serial.Serial')
    def test_send_and_receive_mixed_operations(self, mock_serial_class):
        """Mix send and receive operations in sequence."""
        # Setup mock serial port
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 10

        # Simulate initialization + mixed responses
        init_responses = [b'\r'] * 7
        responses = [
            b't1232AABB\r',       # Response to send 1 (ID=0x123, DLC=2, Data=AABB)
            b't79928877\r',       # Passive receive 1 (ID=0x799, DLC=2, Data=8877)
            b't2344455\r',        # Response to send 2 (ID=0x234, DLC=2, Data=4455)
            b't78821122\r',       # Passive receive 2 (ID=0x788, DLC=2, Data=1122)
        ]
        mock_serial.read.side_effect = init_responses + responses
        mock_serial_class.return_value = mock_serial

        # Create and connect adapter
        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()

        # Send message 1
        msg1 = CANMessage(arbitration_id=0x123, data=b'\xAA\xBB')
        response1 = adapter.send_frame(msg1, timeout=1.0)
        assert response1.arbitration_id == 0x123

        # Receive passive frame 1
        frame1 = adapter.receive_frame(timeout=1.0)
        assert frame1.arbitration_id == 0x799

        # Send message 2
        msg2 = CANMessage(arbitration_id=0x234, data=b'\x44\x55')
        response2 = adapter.send_frame(msg2, timeout=1.0)
        assert response2.arbitration_id == 0x234

        # Receive passive frame 2
        frame2 = adapter.receive_frame(timeout=1.0)
        assert frame2.arbitration_id == 0x788

        # Verify operations completed without interference
        assert response1.data == b'\xAA\xBB'
        assert frame1.data == b'\x88\x77'
        assert response2.data == b'\x44\x55'
        assert frame2.data == b'\x11\x22'
