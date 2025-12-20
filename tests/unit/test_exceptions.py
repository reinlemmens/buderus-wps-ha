"""Unit tests for exception hierarchy."""


from buderus_wps.exceptions import (
    BuderusCANException,
    CANBitrateError,
    CANBusOffError,
    CANError,
    CANFrameError,
    ConcurrencyError,
    ConnectionError,
    DeviceDisconnectedError,
    DeviceInitializationError,
    DeviceNotFoundError,
    DevicePermissionError,
    ReadTimeoutError,
    TimeoutError,
    WriteTimeoutError,
)


class TestBuderusCANException:
    """Test base exception class."""

    def test_init_with_message_only(self) -> None:
        """Test creating exception with message only."""
        exc = BuderusCANException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.context == {}

    def test_init_with_context(self) -> None:
        """Test creating exception with context."""
        exc = BuderusCANException(
            "Test error", context={"port": "/dev/ttyACM0", "timeout": 5.0}
        )
        assert "Test error" in str(exc)
        assert "port=/dev/ttyACM0" in str(exc)
        assert "timeout=5.0" in str(exc)
        assert exc.context["port"] == "/dev/ttyACM0"
        assert exc.context["timeout"] == 5.0

    def test_str_without_context(self) -> None:
        """Test string representation without context."""
        exc = BuderusCANException("Error message")
        assert str(exc) == "Error message"

    def test_str_with_context(self) -> None:
        """Test string representation with context."""
        exc = BuderusCANException("Error", context={"key": "value"})
        result = str(exc)
        assert "Error" in result
        assert "key=value" in result


class TestConnectionExceptions:
    """Test connection-related exceptions."""

    def test_connection_error_inherits_from_base(self) -> None:
        """Test ConnectionError inherits from BuderusCANException."""
        exc = ConnectionError("test")
        assert isinstance(exc, BuderusCANException)

    def test_device_not_found_error(self) -> None:
        """Test DeviceNotFoundError."""
        exc = DeviceNotFoundError("Port not found")
        assert isinstance(exc, ConnectionError)
        assert isinstance(exc, BuderusCANException)
        assert str(exc) == "Port not found"

    def test_device_permission_error(self) -> None:
        """Test DevicePermissionError."""
        exc = DevicePermissionError("Permission denied")
        assert isinstance(exc, ConnectionError)
        assert str(exc) == "Permission denied"

    def test_device_disconnected_error(self) -> None:
        """Test DeviceDisconnectedError."""
        exc = DeviceDisconnectedError("Device unplugged")
        assert isinstance(exc, ConnectionError)

    def test_device_initialization_error(self) -> None:
        """Test DeviceInitializationError."""
        exc = DeviceInitializationError("Init failed")
        assert isinstance(exc, ConnectionError)


class TestTimeoutExceptions:
    """Test timeout-related exceptions."""

    def test_timeout_error_inherits_from_base(self) -> None:
        """Test TimeoutError inherits from BuderusCANException."""
        exc = TimeoutError("test")
        assert isinstance(exc, BuderusCANException)

    def test_read_timeout_error(self) -> None:
        """Test ReadTimeoutError."""
        exc = ReadTimeoutError("No response", context={"timeout": 5.0})
        assert isinstance(exc, TimeoutError)
        assert isinstance(exc, BuderusCANException)
        assert "No response" in str(exc)
        assert "timeout=5.0" in str(exc)

    def test_write_timeout_error(self) -> None:
        """Test WriteTimeoutError."""
        exc = WriteTimeoutError("Write failed")
        assert isinstance(exc, TimeoutError)


class TestCANExceptions:
    """Test CAN bus protocol exceptions."""

    def test_can_error_inherits_from_base(self) -> None:
        """Test CANError inherits from BuderusCANException."""
        exc = CANError("test")
        assert isinstance(exc, BuderusCANException)

    def test_can_bus_off_error(self) -> None:
        """Test CANBusOffError."""
        exc = CANBusOffError("Bus off detected")
        assert isinstance(exc, CANError)
        assert isinstance(exc, BuderusCANException)

    def test_can_bitrate_error(self) -> None:
        """Test CANBitrateError."""
        exc = CANBitrateError("Bitrate mismatch")
        assert isinstance(exc, CANError)

    def test_can_frame_error(self) -> None:
        """Test CANFrameError."""
        exc = CANFrameError("Invalid frame", context={"received": "t12G4"})
        assert isinstance(exc, CANError)
        assert "Invalid frame" in str(exc)
        assert "received=t12G4" in str(exc)


class TestConcurrencyException:
    """Test concurrency exception."""

    def test_concurrency_error_inherits_from_base(self) -> None:
        """Test ConcurrencyError inherits from BuderusCANException."""
        exc = ConcurrencyError("Concurrent operation")
        assert isinstance(exc, BuderusCANException)
        assert "Concurrent operation" in str(exc)


class TestExceptionHierarchy:
    """Test exception hierarchy relationships."""

    def test_all_exceptions_inherit_from_base(self) -> None:
        """Test all custom exceptions inherit from BuderusCANException."""
        exceptions = [
            ConnectionError,
            DeviceNotFoundError,
            DevicePermissionError,
            DeviceDisconnectedError,
            DeviceInitializationError,
            TimeoutError,
            ReadTimeoutError,
            WriteTimeoutError,
            CANError,
            CANBusOffError,
            CANBitrateError,
            CANFrameError,
            ConcurrencyError,
        ]

        for exc_class in exceptions:
            exc = exc_class("test")
            assert isinstance(exc, BuderusCANException)

    def test_broad_exception_catching(self) -> None:
        """Test catching all exceptions with base class."""
        exceptions = [
            DeviceNotFoundError("test"),
            ReadTimeoutError("test"),
            CANBusOffError("test"),
            ConcurrencyError("test"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except BuderusCANException as e:
                assert isinstance(e, BuderusCANException)
