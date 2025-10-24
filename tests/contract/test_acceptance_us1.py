"""Acceptance tests for User Story 1: Establish Connection.

Tests validate acceptance scenarios from spec.md:
- AS1: Open connection with valid port path
- AS2: Query connection status when open
- AS3: Error handling for invalid port path

These tests use mocked serial ports to verify end-to-end behavior
without requiring physical hardware.
"""

import pytest
from unittest.mock import patch, MagicMock
from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.exceptions import DeviceNotFoundError


class TestAS1OpenConnection:
    """AS1: Developer opens connection to USBtin with valid port path."""

    @patch('serial.Serial')
    def test_open_connection_succeeds(self, mock_serial_class):
        """
        GIVEN a valid serial port path
        WHEN developer calls connect()
        THEN connection is established and adapter reports as open
        """
        # Arrange: Mock successful serial connection
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'  # ACK responses
        mock_serial_class.return_value = mock_serial

        # Act: Open connection
        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()

        # Assert: Connection established
        assert adapter.is_open is True, "Adapter should report as open after connect()"

        # Assert: Initialization sequence sent
        assert mock_serial.write.call_count >= 7, "Should send 7 init commands"

        # Cleanup
        adapter.disconnect()

    @patch('serial.Serial')
    def test_open_connection_with_context_manager(self, mock_serial_class):
        """
        GIVEN a valid serial port path
        WHEN developer uses context manager (with statement)
        THEN connection opens automatically and closes on exit
        """
        # Arrange
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        # Act & Assert: Connection in context
        with USBtinAdapter('/dev/ttyACM0') as adapter:
            assert adapter.is_open is True

        # Assert: Connection closed after context exit
        mock_serial.close.assert_called()

    @patch('serial.Serial')
    def test_connection_establishes_within_time_limit(self, mock_serial_class):
        """
        GIVEN a valid serial port
        WHEN developer calls connect()
        THEN connection completes within 2 seconds (SC-001)
        """
        import time

        # Arrange
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        # Act: Measure connection time
        adapter = USBtinAdapter('/dev/ttyACM0')
        start_time = time.time()
        adapter.connect()
        elapsed = time.time() - start_time

        # Assert: Connection time meets success criteria
        assert elapsed < 2.0, f"Connection should complete < 2s, took {elapsed:.2f}s"
        assert adapter.is_open is True

        # Cleanup
        adapter.disconnect()


class TestAS2QueryConnectionStatus:
    """AS2: Developer queries connection status."""

    @patch('serial.Serial')
    def test_query_status_when_open(self, mock_serial_class):
        """
        GIVEN an open connection
        WHEN developer checks is_open property
        THEN returns True
        """
        # Arrange
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        # Act
        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()

        # Assert
        assert adapter.is_open is True

        # Cleanup
        adapter.disconnect()

    def test_query_status_when_closed(self):
        """
        GIVEN a closed connection
        WHEN developer checks is_open property
        THEN returns False
        """
        # Arrange: Create adapter without connecting
        adapter = USBtinAdapter('/dev/ttyACM0')

        # Act & Assert
        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_query_status_after_disconnect(self, mock_serial_class):
        """
        GIVEN a previously open connection that was disconnected
        WHEN developer checks is_open property
        THEN returns False
        """
        # Arrange
        mock_serial = MagicMock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b'\r'
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()

        # Act: Disconnect
        adapter.disconnect()

        # Assert: Status reflects disconnection
        assert adapter.is_open is False


class TestAS3ErrorHandlingInvalidPort:
    """AS3: Error handling for invalid port path."""

    @patch('serial.Serial')
    def test_invalid_port_raises_error(self, mock_serial_class):
        """
        GIVEN an invalid/non-existent port path
        WHEN developer calls connect()
        THEN raises DeviceNotFoundError with diagnostic message
        """
        # Arrange: Mock port not found
        mock_serial_class.side_effect = FileNotFoundError("Port not found")

        # Act & Assert: Connection fails with clear error
        adapter = USBtinAdapter('/dev/ttyNONEXISTENT')
        with pytest.raises(DeviceNotFoundError) as exc_info:
            adapter.connect()

        # Assert: Error message is diagnostic
        error_msg = str(exc_info.value)
        assert "not found" in error_msg.lower()
        assert "/dev/ttyNONEXISTENT" in error_msg or "port" in error_msg.lower()

        # Assert: Adapter remains closed
        assert adapter.is_open is False

    @patch('serial.Serial')
    def test_permission_denied_raises_error(self, mock_serial_class):
        """
        GIVEN a port path without permissions
        WHEN developer calls connect()
        THEN raises DeviceNotFoundError with troubleshooting hint
        """
        # Arrange: Mock permission error
        mock_serial_class.side_effect = PermissionError("Permission denied")

        # Act & Assert
        adapter = USBtinAdapter('/dev/ttyACM0')
        with pytest.raises(DeviceNotFoundError) as exc_info:
            adapter.connect()

        # Assert: Error includes troubleshooting hint
        error_msg = str(exc_info.value)
        assert "permission" in error_msg.lower() or "dialout" in error_msg.lower()

    def test_empty_port_path_raises_error(self):
        """
        GIVEN an empty port path
        WHEN developer creates adapter
        THEN raises ValueError immediately
        """
        # Act & Assert: Validation at construction
        with pytest.raises(ValueError, match="Port path cannot be empty"):
            USBtinAdapter('')

    @patch('serial.Serial')
    def test_error_provides_diagnostic_context(self, mock_serial_class):
        """
        GIVEN a connection failure
        WHEN error is raised
        THEN error includes diagnostic context (port path, error details)
        """
        # Arrange
        mock_serial_class.side_effect = FileNotFoundError("Port not found")

        # Act
        adapter = USBtinAdapter('/dev/ttyUSB0')
        with pytest.raises(DeviceNotFoundError) as exc_info:
            adapter.connect()

        # Assert: Exception has context attribute
        exception = exc_info.value
        assert hasattr(exception, 'context'), "Exception should include diagnostic context"
        assert 'port' in exception.context, "Context should include port path"
        assert exception.context['port'] == '/dev/ttyUSB0'
