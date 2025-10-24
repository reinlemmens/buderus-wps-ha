"""Integration tests for USBtinAdapter with mocked serial port.

Tests cover:
- T022: USBtinAdapter.connect() with mocked serial
- T023: USBtinAdapter.disconnect() with mocked serial
- T024: USBtinAdapter.is_open property
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from buderus_wps.can_adapter import USBtinAdapter
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
