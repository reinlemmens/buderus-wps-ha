"""Unit tests for USBtinAdapter parameter validation and basic functionality.

Tests cover:
- T021: USBtinAdapter.__init__() parameter validation
- T036: USBtinAdapter.send_frame() with successful response
- T037: USBtinAdapter.send_frame() timeout handling
- T038: USBtinAdapter.receive_frame()
"""

from unittest.mock import Mock, patch

import pytest

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage
from buderus_wps.exceptions import DeviceCommunicationError, TimeoutError


class TestUSBtinAdapterInitialization:
    """Test USBtinAdapter initialization and parameter validation."""

    def test_init_with_port_only(self):
        """Initialize adapter with port path only (defaults for other params)."""
        adapter = USBtinAdapter("/dev/ttyACM0")
        assert adapter.port == "/dev/ttyACM0"
        assert adapter.baudrate == 115200  # Default
        assert adapter.timeout == 5.0  # Default

    def test_init_with_custom_baudrate(self):
        """Initialize adapter with custom baud rate."""
        adapter = USBtinAdapter("/dev/ttyACM0", baudrate=57600)
        assert adapter.baudrate == 57600

    def test_init_with_custom_timeout(self):
        """Initialize adapter with custom timeout."""
        adapter = USBtinAdapter("/dev/ttyACM0", timeout=10.0)
        assert adapter.timeout == 10.0

    def test_init_with_all_parameters(self):
        """Initialize adapter with all parameters specified."""
        adapter = USBtinAdapter("/dev/ttyUSB0", baudrate=9600, timeout=2.5)
        assert adapter.port == "/dev/ttyUSB0"
        assert adapter.baudrate == 9600
        assert adapter.timeout == 2.5

    def test_init_empty_port_path(self):
        """Initialize adapter with empty port path (invalid)."""
        with pytest.raises(ValueError, match="Port path cannot be empty"):
            USBtinAdapter("")

    def test_init_invalid_baudrate_zero(self):
        """Initialize adapter with zero baud rate (invalid)."""
        with pytest.raises(ValueError, match="Baudrate must be positive"):
            USBtinAdapter("/dev/ttyACM0", baudrate=0)

    def test_init_invalid_baudrate_negative(self):
        """Initialize adapter with negative baud rate (invalid)."""
        with pytest.raises(ValueError, match="Baudrate must be positive"):
            USBtinAdapter("/dev/ttyACM0", baudrate=-115200)

    def test_init_invalid_timeout_zero(self):
        """Initialize adapter with zero timeout (invalid)."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            USBtinAdapter("/dev/ttyACM0", timeout=0.0)

    def test_init_invalid_timeout_negative(self):
        """Initialize adapter with negative timeout (invalid)."""
        with pytest.raises(ValueError, match="Timeout must be positive"):
            USBtinAdapter("/dev/ttyACM0", timeout=-5.0)

    def test_init_timeout_too_small(self):
        """Initialize adapter with timeout below minimum (0.1s)."""
        with pytest.raises(ValueError, match="Timeout must be at least 0.1 seconds"):
            USBtinAdapter("/dev/ttyACM0", timeout=0.05)

    def test_init_timeout_too_large(self):
        """Initialize adapter with timeout above maximum (60s)."""
        with pytest.raises(ValueError, match="Timeout must not exceed 60 seconds"):
            USBtinAdapter("/dev/ttyACM0", timeout=61.0)

    def test_init_state_is_closed(self):
        """Adapter should be in closed state after initialization."""
        adapter = USBtinAdapter("/dev/ttyACM0")
        assert adapter.is_open is False

    def test_init_read_only_flag(self):
        """Adapter supports read-only mode flag."""
        adapter = USBtinAdapter("/dev/ttyACM0", read_only=True)
        assert adapter.read_only is True
        assert adapter.status == "closed"

    def test_init_does_not_auto_connect(self):
        """Initialization should not automatically open connection."""
        adapter = USBtinAdapter("/dev/ttyACM0")
        assert adapter.is_open is False
        # This test just verifies state - actual serial port not opened


class TestUSBtinAdapterSendFrame:
    """Test USBtinAdapter.send_frame() method (T036, T037)."""

    @patch("serial.Serial")
    def test_send_frame_successful_response(self, mock_serial_class):
        """T036: Send frame and receive successful response."""
        # Setup mock serial port with response buffer
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        mock_serial.is_open = True

        # Create a buffer to simulate serial responses
        response_buffer = []

        # Add init responses
        response_buffer.extend([b"\r"] * 7)  # 7 init commands

        # Add message response (ID=0x123, DLC=1, Data=00)
        response_buffer.append(b"t123100\r")  # Response frame

        # Track read position
        read_index = [0]

        def mock_read(size):
            if read_index[0] < len(response_buffer):
                data = response_buffer[read_index[0]]
                read_index[0] += 1
                return data
            return b""

        def mock_in_waiting():
            return 10 if read_index[0] < len(response_buffer) else 0

        mock_serial.read.side_effect = mock_read
        type(mock_serial).in_waiting = property(lambda self: mock_in_waiting())

        # Create and connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Create test message
        request = CANMessage(arbitration_id=0x123, data=b"\x00", is_extended_id=False)

        # Send frame and expect response
        response = adapter.send_frame(request, timeout=1.0)

        # Verify response received
        assert response is not None
        assert isinstance(response, CANMessage)
        assert response.arbitration_id == 0x123
        assert response.data == b"\x00"

        # Verify write was called with correct SLCAN format
        calls = [call[0][0] for call in mock_serial.write.call_args_list]
        assert (
            b"t123100\r" in calls
        )  # Request frame in SLCAN format (ID=0x123, DLC=1, Data=00)

    @patch("serial.Serial")
    def test_send_frame_timeout(self, mock_serial_class):
        """T037: Send frame and timeout when no response received."""
        # Setup mock serial port
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        mock_serial.is_open = True
        mock_serial.in_waiting = 0

        # Simulate successful initialization
        init_responses = [
            b"\r",
            b"\r",
            b"V1234\r",
            b"V5678\r",
            b"v1020\r",
            b"\r",
            b"\r",
        ]
        mock_serial.read.side_effect = init_responses + [
            b"",  # No response - empty reads
            b"",
            b"",
        ]

        # Create and connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Create test message
        request = CANMessage(arbitration_id=0x123, data=b"\x00", is_extended_id=False)

        # Send frame and expect timeout
        with pytest.raises(TimeoutError, match="No response received"):
            adapter.send_frame(request, timeout=0.1)

    @patch("serial.Serial")
    def test_send_frame_not_connected(self, mock_serial_class):
        """Send frame when adapter not connected should raise error."""
        adapter = USBtinAdapter("/dev/ttyACM0")

        # Create test message
        request = CANMessage(arbitration_id=0x123, data=b"\x00")

        # Attempt to send without connecting
        with pytest.raises(DeviceCommunicationError, match="not connected"):
            adapter.send_frame(request)

    @patch("serial.Serial")
    def test_send_frame_read_only_mode(self, mock_serial_class):
        """Sending in read-only mode is blocked."""
        adapter = USBtinAdapter("/dev/ttyACM0", read_only=True)
        adapter._serial = Mock()
        adapter._serial.is_open = True
        request = CANMessage(arbitration_id=0x123, data=b"\x00")
        with pytest.raises(PermissionError, match="read-only"):
            adapter.send_frame(request)

    @patch("serial.Serial")
    def test_send_frame_extended_id(self, mock_serial_class):
        """Send frame with extended CAN ID."""
        # Setup mock serial port with response buffer
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        mock_serial.is_open = True

        # Create response buffer
        response_buffer = [b"\r"] * 7  # Init
        response_buffer.append(
            b"T31D011E9100\r"
        )  # Extended frame response (ID, DLC=1, Data=00)

        read_index = [0]

        def mock_read(size):
            if read_index[0] < len(response_buffer):
                data = response_buffer[read_index[0]]
                read_index[0] += 1
                return data
            return b""

        def mock_in_waiting():
            return 10 if read_index[0] < len(response_buffer) else 0

        mock_serial.read.side_effect = mock_read
        type(mock_serial).in_waiting = property(lambda self: mock_in_waiting())

        # Create and connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Create extended ID message (Buderus heat pump ID)
        request = CANMessage(
            arbitration_id=0x31D011E9, data=b"\x00", is_extended_id=True
        )

        # Send frame
        response = adapter.send_frame(request, timeout=1.0)

        # Verify extended ID preserved
        assert response.is_extended_id is True
        assert response.arbitration_id == 0x31D011E9


class TestUSBtinAdapterReceiveFrame:
    """Test USBtinAdapter.receive_frame() method (T038)."""

    @patch("serial.Serial")
    def test_receive_frame_standard_id(self, mock_serial_class):
        """T038: Receive standard CAN frame passively."""
        # Setup mock serial port with response buffer
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        mock_serial.is_open = True

        # Create response buffer
        response_buffer = [b"\r"] * 7  # Init
        response_buffer.append(
            b"t1233010203\r"
        )  # Standard frame (ID=0x123, DLC=3, Data=010203)

        read_index = [0]

        def mock_read(size):
            if read_index[0] < len(response_buffer):
                data = response_buffer[read_index[0]]
                read_index[0] += 1
                return data
            return b""

        def mock_in_waiting():
            return 10 if read_index[0] < len(response_buffer) else 0

        mock_serial.read.side_effect = mock_read
        type(mock_serial).in_waiting = property(lambda self: mock_in_waiting())

        # Create and connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Receive frame
        frame = adapter.receive_frame(timeout=1.0)

        # Verify frame received
        assert frame is not None
        assert frame.arbitration_id == 0x123
        assert frame.data == b"\x01\x02\x03"
        assert frame.is_extended_id is False

    @patch("serial.Serial")
    def test_receive_frame_extended_id(self, mock_serial_class):
        """Receive extended CAN frame passively."""
        # Setup mock serial port with response buffer
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        mock_serial.is_open = True

        # Create response buffer
        response_buffer = [b"\r"] * 7  # Init
        response_buffer.append(
            b"T31D011E93123445\r"
        )  # Extended frame (ID=0x31D011E9, DLC=3, Data=123445)

        read_index = [0]

        def mock_read(size):
            if read_index[0] < len(response_buffer):
                data = response_buffer[read_index[0]]
                read_index[0] += 1
                return data
            return b""

        def mock_in_waiting():
            return 10 if read_index[0] < len(response_buffer) else 0

        mock_serial.read.side_effect = mock_read
        type(mock_serial).in_waiting = property(lambda self: mock_in_waiting())

        # Create and connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Receive frame
        frame = adapter.receive_frame(timeout=1.0)

        # Verify extended frame
        assert frame.is_extended_id is True
        assert frame.arbitration_id == 0x31D011E9
        assert frame.data == b"\x12\x34\x45"

    @patch("serial.Serial")
    def test_receive_frame_timeout(self, mock_serial_class):
        """Receive frame times out when no data available."""
        # Setup mock serial port
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        mock_serial.is_open = True
        mock_serial.in_waiting = 0  # No data available

        # Simulate successful initialization
        init_responses = [
            b"\r",
            b"\r",
            b"V1234\r",
            b"V5678\r",
            b"v1020\r",
            b"\r",
            b"\r",
        ]
        mock_serial.read.side_effect = init_responses + [
            b"",  # Empty reads - no data
            b"",
            b"",
        ]

        # Create and connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Receive should timeout
        with pytest.raises(TimeoutError, match="No frame received"):
            adapter.receive_frame(timeout=0.1)

    @patch("serial.Serial")
    def test_receive_frame_not_connected(self, mock_serial_class):
        """Receive frame when not connected should raise error."""
        adapter = USBtinAdapter("/dev/ttyACM0")

        # Attempt to receive without connecting
        with pytest.raises(DeviceCommunicationError, match="not connected"):
            adapter.receive_frame()

    @patch("serial.Serial")
    def test_receive_frame_remote_frame(self, mock_serial_class):
        """Receive remote frame (RTR)."""
        # Setup mock serial port
        mock_serial = Mock()
        mock_serial_class.return_value = mock_serial
        mock_serial.is_open = True
        mock_serial.in_waiting = 10

        # Simulate successful initialization
        init_responses = [
            b"\r",
            b"\r",
            b"V1234\r",
            b"V5678\r",
            b"v1020\r",
            b"\r",
            b"\r",
        ]
        mock_serial.read.side_effect = init_responses + [
            b"r1234\r"  # Remote frame with DLC 4
        ]

        # Create and connect adapter
        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Receive remote frame
        frame = adapter.receive_frame(timeout=1.0)

        # Verify remote frame
        assert frame.is_remote_frame is True
        assert frame.arbitration_id == 0x123
        assert frame.dlc == 4


class TestConnectionStateDetection:
    """Test connection state detection (T049).

    Tests cover:
    - Detection of serial port disconnection
    - Status property reflects actual connection state
    - Operations detect stale connections
    """

    @patch("serial.Serial")
    def test_connection_state_after_serial_close(self, mock_serial_class):
        """T049: Detect when serial port is closed externally."""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()
        assert adapter.is_open is True

        # Simulate serial port being closed (USB disconnection)
        mock_serial.is_open = False

        # is_open should now report false
        assert adapter.is_open is False

    @patch("serial.Serial")
    def test_status_reflects_connection_state(self, mock_serial_class):
        """T049: Status property reports connection state accurately."""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")

        # Before connect
        assert adapter.status == "closed"

        # After connect
        adapter.connect()
        assert adapter.status == "connected"

        # After external disconnection
        mock_serial.is_open = False
        assert adapter.status == "closed"

    @patch("serial.Serial")
    def test_send_frame_detects_disconnection(self, mock_serial_class):
        """T049: send_frame detects when connection is lost."""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Simulate disconnection
        mock_serial.is_open = False

        # send_frame should detect and raise error
        request = CANMessage(arbitration_id=0x123, data=b"\x00")
        with pytest.raises(DeviceCommunicationError, match="not connected"):
            adapter.send_frame(request)

    @patch("serial.Serial")
    def test_receive_frame_detects_disconnection(self, mock_serial_class):
        """T049: receive_frame detects when connection is lost."""
        mock_serial = Mock()
        mock_serial.is_open = True
        mock_serial.in_waiting = 0
        mock_serial.read.return_value = b"\r"
        mock_serial_class.return_value = mock_serial

        adapter = USBtinAdapter("/dev/ttyACM0")
        adapter.connect()

        # Simulate disconnection
        mock_serial.is_open = False

        # receive_frame should detect and raise error
        with pytest.raises(DeviceCommunicationError, match="not connected"):
            adapter.receive_frame()
