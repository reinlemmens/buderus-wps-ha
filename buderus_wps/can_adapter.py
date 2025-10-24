"""USBtin CAN adapter using SLCAN protocol over serial port.

This module implements the USBtinAdapter class for communicating with USBtin
CAN bus adapters via USB serial connection using the SLCAN (Lawicel) ASCII protocol.

Protocol References:
- SLCAN: Lawicel AB ASCII protocol
- USBtin: fischl.de/usbtin hardware adapter
"""

import atexit
import time
from typing import Optional

try:
    import serial
except ImportError:
    raise ImportError(
        "pyserial is required for USBtin adapter. "
        "Install with: pip install pyserial"
    )

from .can_message import CANMessage
from .exceptions import (
    DeviceNotFoundError,
    DevicePermissionError,
    DeviceInitializationError,
    DeviceDisconnectedError,
    DeviceCommunicationError,
    TimeoutError
)


class USBtinAdapter:
    """USBtin CAN adapter with SLCAN protocol support.

    Provides connection management, message transmission/reception, and
    resource cleanup for USBtin hardware adapters.

    Attributes:
        port: Serial port path (e.g., '/dev/ttyACM0', 'COM3')
        baudrate: Serial communication speed (default: 115200)
        timeout: Operation timeout in seconds (default: 5.0)
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 5.0) -> None:
        """Initialize USBtin adapter (does not open connection).

        Args:
            port: Serial port device path
            baudrate: Serial baud rate (default: 115200 for USBtin)
            timeout: Operation timeout in seconds (0.1-60.0, default: 5.0)

        Raises:
            ValueError: Invalid port, baudrate, or timeout parameters
        """
        # Validate parameters
        if not port or not isinstance(port, str):
            raise ValueError("Port path cannot be empty")

        if baudrate <= 0:
            raise ValueError(f"Baudrate must be positive, got {baudrate}")

        if timeout <= 0:
            raise ValueError(f"Timeout must be positive, got {timeout}")

        if timeout < 0.1:
            raise ValueError(
                f"Timeout must be at least 0.1 seconds, got {timeout}"
            )

        if timeout > 60.0:
            raise ValueError(
                f"Timeout must not exceed 60 seconds, got {timeout}"
            )

        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        # Internal state
        self._serial: Optional[serial.Serial] = None
        self._in_operation = False

        # Register cleanup handler
        atexit.register(self._atexit_cleanup)

    @property
    def is_open(self) -> bool:
        """Check if connection is open.

        Returns:
            True if serial port is open and ready for communication
        """
        return self._serial is not None and self._serial.is_open

    def connect(self) -> 'USBtinAdapter':
        """Open serial connection and initialize USBtin adapter.

        Initialization sequence (from research.md):
        1. Open serial port (115200 baud, 8N1, 1s timeout)
        2. Wait 2 seconds for device stabilization
        3. Send initialization commands:
           - C (close channel) x2
           - V (hardware version) x2
           - v (firmware version)
           - S4 (set bitrate to 125 kbps)
           - O (open channel)

        Returns:
            Self for method chaining

        Raises:
            DeviceNotFoundError: Serial port not found or permission denied
            DeviceInitializationError: Device initialization failed
            RuntimeError: Already connected
        """
        if self.is_open:
            raise RuntimeError(
                f"Already connected to {self.port}. "
                "Call disconnect() first or use a new adapter instance."
            )

        try:
            # Open serial port
            self._serial = serial.Serial(
                self.port,
                baudrate=self.baudrate,
                timeout=1.0,  # Internal timeout for read operations
                write_timeout=1.0
            )
        except FileNotFoundError:
            raise DeviceNotFoundError(
                f"Serial port {self.port} not found. "
                "Check USB connection and port path.",
                context={"port": self.port}
            )
        except PermissionError:
            raise DevicePermissionError(
                f"Permission denied accessing {self.port}. "
                "Add user to dialout group: sudo usermod -a -G dialout $USER",
                context={"port": self.port}
            )
        except serial.SerialException as e:
            raise DeviceNotFoundError(
                f"Failed to open serial port {self.port}: {e}",
                context={"port": self.port, "error": str(e)}
            )

        try:
            # Wait for device stabilization
            time.sleep(2.0)

            # Initialization sequence
            init_commands = [
                b'C\r',  # Close channel (1st)
                b'C\r',  # Close channel (2nd, safety)
                b'V\r',  # Hardware version (1st)
                b'V\r',  # Hardware version (2nd)
                b'v\r',  # Firmware version
                b'S4\r', # Set bitrate to 125 kbps (Buderus standard)
                b'O\r'   # Open channel
            ]

            for cmd in init_commands:
                self._write_command(cmd)
                response = self._read_response(timeout=2.0)

                # Check for error response
                if response == b'\a':  # Bell = NAK/Error
                    raise DeviceInitializationError(
                        f"Device returned error during initialization (command: {cmd.decode('utf-8', 'ignore').strip()})",
                        context={
                            "port": self.port,
                            "command": cmd.decode('utf-8', 'ignore'),
                            "response": "NAK"
                        }
                    )

            return self

        except Exception as e:
            # Cleanup on failure
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except:
                    pass
            self._serial = None

            if isinstance(e, (DeviceNotFoundError, DeviceInitializationError)):
                raise
            else:
                raise DeviceInitializationError(
                    f"Unexpected error during initialization: {e}",
                    context={"port": self.port, "error": str(e)}
                )

    def disconnect(self) -> None:
        """Close serial connection and release resources.

        This method handles errors gracefully and never raises exceptions.
        It can be called multiple times safely (idempotent).
        """
        if not self.is_open:
            return

        try:
            # Send close command to adapter
            if self._serial and self._serial.is_open:
                try:
                    self._serial.write(b'C\r')
                    time.sleep(0.1)  # Brief wait for command processing
                except:
                    pass  # Ignore errors during shutdown

            # Close serial port
            if self._serial:
                try:
                    self._serial.close()
                except:
                    pass  # Ignore errors during cleanup

        finally:
            self._serial = None
            self._in_operation = False

    def __enter__(self) -> 'USBtinAdapter':
        """Enter context manager (connect if not already connected).

        Returns:
            Self for use in with statement
        """
        if not self.is_open:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager (disconnect).

        Args:
            exc_type: Exception type (if any)
            exc_val: Exception value (if any)
            exc_tb: Exception traceback (if any)

        Returns:
            False to propagate exceptions
        """
        self.disconnect()
        return False  # Don't suppress exceptions

    def __del__(self) -> None:
        """Destructor - cleanup resources if not already done.

        This is a fallback cleanup mechanism. Explicit disconnect() or
        context manager usage is preferred.
        """
        try:
            self.disconnect()
        except:
            pass  # Ignore all errors in destructor

    def _atexit_cleanup(self) -> None:
        """Cleanup handler registered with atexit module."""
        try:
            self.disconnect()
        except:
            pass  # Ignore all errors during exit

    def _write_command(self, command: bytes) -> None:
        """Write command to serial port.

        Args:
            command: Command bytes to write

        Raises:
            DeviceDisconnectedError: Serial port not open
        """
        if not self.is_open or not self._serial:
            raise DeviceDisconnectedError(
                "Cannot write: serial port not open",
                context={"port": self.port}
            )

        try:
            self._serial.write(command)
        except serial.SerialTimeoutException:
            raise DeviceDisconnectedError(
                "Write timeout - device may be disconnected",
                context={"port": self.port, "command": command.decode('utf-8', 'ignore')}
            )
        except serial.SerialException as e:
            raise DeviceDisconnectedError(
                f"Serial write error: {e}",
                context={"port": self.port, "error": str(e)}
            )

    def _read_response(self, timeout: float = 1.0) -> bytes:
        """Read response from serial port with timeout.

        Uses polling to read until \\r terminator or timeout.

        Args:
            timeout: Maximum time to wait for response (seconds)

        Returns:
            Response bytes (may be empty if timeout)

        Raises:
            DeviceDisconnectedError: Serial port not open
        """
        if not self.is_open or not self._serial:
            raise DeviceDisconnectedError(
                "Cannot read: serial port not open",
                context={"port": self.port}
            )

        start_time = time.time()
        response = b''

        try:
            while time.time() - start_time < timeout:
                # Check for available data
                if self._serial.in_waiting > 0:
                    chunk = self._serial.read(self._serial.in_waiting)
                    response += chunk

                    # Check for terminator
                    if b'\r' in response or b'\a' in response:
                        break

                time.sleep(0.01)  # 10ms poll interval

            return response

        except serial.SerialException as e:
            raise DeviceDisconnectedError(
                f"Serial read error: {e}",
                context={"port": self.port, "error": str(e)}
            )

    def _read_frame(self, timeout: float = 5.0) -> Optional[CANMessage]:
        """Read a single CAN frame from the serial port with timeout (T041).

        Uses polling to read until a complete SLCAN frame (terminated by \\r)
        is received or timeout occurs.

        Args:
            timeout: Maximum time to wait for frame (seconds)

        Returns:
            CANMessage if frame received, None if timeout

        Raises:
            DeviceCommunicationError: Device not connected
        """
        if not self.is_open or not self._serial:
            raise DeviceCommunicationError(
                "Device not connected",
                context={"port": self.port}
            )

        start_time = time.time()
        buffer = b''

        try:
            while time.time() - start_time < timeout:
                # Check for available data
                if self._serial.in_waiting > 0:
                    chunk = self._serial.read(self._serial.in_waiting)
                    buffer += chunk

                    # Check for complete frame (terminated by \r)
                    if b'\r' in buffer:
                        # Extract frame up to terminator
                        frame_bytes, remaining = buffer.split(b'\r', 1)
                        buffer = remaining  # Keep remaining data for next read

                        # Parse and return frame
                        frame_str = frame_bytes.decode('ascii', errors='ignore').strip()
                        if frame_str:
                            return CANMessage.from_usbtin_format(frame_str)

                # Poll every 10ms for real-time CAN
                time.sleep(0.01)

            # Timeout - no complete frame received
            return None

        except serial.SerialException as e:
            raise DeviceCommunicationError(
                f"Serial read error: {e}",
                context={"port": self.port, "error": str(e)}
            )
        except Exception as e:
            raise DeviceCommunicationError(
                f"Frame parsing error: {e}",
                context={"port": self.port, "buffer": buffer.decode('ascii', errors='ignore')}
            )

    def send_frame(self, message: CANMessage, timeout: float = 5.0) -> CANMessage:
        """Send CAN frame and wait for response (T042).

        Transmits a CAN message via SLCAN protocol and waits for a response
        frame within the timeout period.

        Args:
            message: CANMessage to send
            timeout: Maximum time to wait for response (seconds)

        Returns:
            Response CANMessage

        Raises:
            DeviceCommunicationError: Device not connected
            TimeoutError: No response received within timeout
        """
        if not self.is_open or not self._serial:
            raise DeviceCommunicationError(
                "Device not connected",
                context={"port": self.port}
            )

        # Guard against concurrent operations
        if self._in_operation:
            raise RuntimeError("Operation already in progress")

        try:
            self._in_operation = True

            # Flush input buffer before sending
            self.flush_input_buffer()

            # Convert message to SLCAN format and send
            slcan_frame = message.to_usbtin_format()
            self._write_command(slcan_frame.encode('ascii'))

            # Wait for response
            response = self._read_frame(timeout=timeout)

            if response is None:
                raise TimeoutError(
                    "No response received within timeout",
                    context={
                        "port": self.port,
                        "timeout": timeout,
                        "request_id": f"0x{message.arbitration_id:X}",
                        "extended": message.is_extended_id
                    }
                )

            return response

        finally:
            self._in_operation = False

    def receive_frame(self, timeout: float = 5.0) -> CANMessage:
        """Receive CAN frame passively (T043).

        Waits for a CAN frame to arrive on the bus without sending a request.
        Used for passive monitoring or receiving unsolicited messages.

        Args:
            timeout: Maximum time to wait for frame (seconds)

        Returns:
            Received CANMessage

        Raises:
            DeviceCommunicationError: Device not connected
            TimeoutError: No frame received within timeout
        """
        if not self.is_open or not self._serial:
            raise DeviceCommunicationError(
                "Device not connected",
                context={"port": self.port}
            )

        # Guard against concurrent operations
        if self._in_operation:
            raise RuntimeError("Operation already in progress")

        try:
            self._in_operation = True

            # Wait for frame
            frame = self._read_frame(timeout=timeout)

            if frame is None:
                raise TimeoutError(
                    "No frame received within timeout",
                    context={
                        "port": self.port,
                        "timeout": timeout
                    }
                )

            return frame

        finally:
            self._in_operation = False

    def flush_input_buffer(self) -> None:
        """Flush serial input buffer to clear old data (T044).

        Discards any pending data in the serial input buffer. Useful before
        sending a new request to ensure old responses don't interfere.

        Raises:
            DeviceCommunicationError: Device not connected
        """
        if not self.is_open or not self._serial:
            raise DeviceCommunicationError(
                "Device not connected",
                context={"port": self.port}
            )

        try:
            self._serial.reset_input_buffer()
        except serial.SerialException as e:
            raise DeviceCommunicationError(
                f"Failed to flush buffer: {e}",
                context={"port": self.port, "error": str(e)}
            )
