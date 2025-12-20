"""Acceptance tests for User Story 3: Graceful Connection Management.

Tests cover:
- T058: AS1 - Explicit connection closure releases resources
- T059: AS2 - USB disconnection error detection
- T060: AS3 - Transient error recovery (future: not implemented)
"""

from unittest.mock import MagicMock, patch

import pytest

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage
from buderus_wps.exceptions import DeviceCommunicationError


class TestAS1ExplicitConnectionClosure:
    """AS1: Explicit connection closure releases all resources."""

    @patch("serial.Serial")
    def test_disconnect_releases_serial_port(self, mock_serial_class):
        """T058: disconnect() releases the serial port resource."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()
        assert adapter.is_open is True

        # Explicit disconnect
        adapter.disconnect()

        # Verify serial port was closed
        mock_serial.close.assert_called()
        assert adapter.is_open is False

    @patch("serial.Serial")
    def test_context_manager_releases_resources(self, mock_serial_class):
        """T058: Context manager releases resources on exit."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        with USBtinAdapter("/dev/ttyACM0") as adapter:
            assert adapter.is_open is True

        # After context exit, resources should be released
        mock_serial.close.assert_called()

    @patch("serial.Serial")
    def test_disconnect_is_idempotent(self, mock_serial_class):
        """T058: Calling disconnect() multiple times is safe."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Multiple disconnects should not raise
        adapter.disconnect()
        adapter.disconnect()
        adapter.disconnect()

        assert adapter.is_open is False

    @patch("serial.Serial")
    def test_disconnect_sends_close_command(self, mock_serial_class):
        """T058: disconnect() sends 'C' command to close CAN channel."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Clear write calls from connect
        mock_serial.write.reset_mock()

        adapter.disconnect()

        # Should have sent 'C\r' to close CAN channel
        write_calls = [call[0][0] for call in mock_serial.write.call_args_list]
        assert b"C\r" in write_calls


class TestAS2USBDisconnectionDetection:
    """AS2: USB disconnection is detected and reported appropriately."""

    @patch("serial.Serial")
    def test_disconnection_detected_on_send(self, mock_serial_class):
        """T059: USB disconnection detected during send operation."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Simulate USB disconnection during write
        mock_serial.write.side_effect = OSError("USB device disconnected")

        # Error should be raised with appropriate message
        request = CANMessage(arbitration_id=0x123, data=b"\x00")
        with pytest.raises(DeviceCommunicationError) as exc_info:
            adapter.send_frame(request)

        assert "communication failed" in str(exc_info.value).lower()

    @patch("serial.Serial")
    def test_disconnection_detected_on_receive(self, mock_serial_class):
        """T059: USB disconnection detected during receive operation."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 10
        mock_serial_class.return_value = mock_serial

        # Successful init, then disconnect on receive
        init_responses = [b"\r"] * 7
        mock_serial.read.side_effect = init_responses + [OSError("Device removed")]

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        with pytest.raises(DeviceCommunicationError) as exc_info:
            adapter.receive_frame(timeout=1.0)

        # Error message should indicate the device issue
        error_msg = str(exc_info.value).lower()
        assert "device removed" in error_msg or "communication" in error_msg

    @patch("serial.Serial")
    def test_error_includes_diagnostic_context(self, mock_serial_class):
        """T059: Error includes diagnostic context for troubleshooting."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Simulate disconnection
        mock_serial.write.side_effect = OSError("I/O error")

        request = CANMessage(arbitration_id=0x123, data=b"\x00")
        with pytest.raises(DeviceCommunicationError) as exc_info:
            adapter.send_frame(request)

        # Error should include context for troubleshooting
        error = exc_info.value
        assert hasattr(error, "context") or "port" in str(error).lower()

    @patch("serial.Serial")
    def test_state_reflects_disconnection(self, mock_serial_class):
        """T059: Adapter state reflects disconnection."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()
        assert adapter.is_open is True
        assert adapter.status == "connected"

        # Simulate serial port closed (USB disconnection)
        mock_serial.is_open = False

        # State should reflect disconnection
        assert adapter.is_open is False
        assert adapter.status == "closed"


class TestAS3TransientErrorRecovery:
    """AS3: Transient error recovery (future enhancement - not implemented).

    Note: This test documents expected future behavior for transient error
    recovery. Currently, all errors are treated as permanent failures.
    """

    @patch("serial.Serial")
    def test_transient_recovery_not_implemented(self, mock_serial_class):
        """T060: Document that transient recovery is not yet implemented."""
        # This test documents that automatic retry is NOT implemented
        # All communication errors are currently treated as permanent failures
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Simulate a transient error (could be recoverable)
        mock_serial.write.side_effect = OSError("Temporary I/O error")

        request = CANMessage(arbitration_id=0x123, data=b"\x00")

        # Current behavior: error is raised immediately (no retry)
        with pytest.raises(DeviceCommunicationError):
            adapter.send_frame(request)

        # Document: In future, this could implement retry logic

    @patch("serial.Serial")
    def test_manual_reconnection_works(self, mock_serial_class):
        """T060: Manual reconnection after error works."""
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()
        assert adapter.is_open is True

        # Disconnect (cleanup) - must be done while is_open is True
        adapter.disconnect()
        assert adapter.is_open is False

        # Reset mock for reconnection
        mock_serial.read.return_value = b"\r"

        # Manual reconnection should work
        adapter.connect()
        assert adapter.is_open is True
