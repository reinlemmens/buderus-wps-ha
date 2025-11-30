"""Unit tests for TUI state management - T005.

Tests for AppState, ConnectionState, ScreenType, ErrorInfo, and ErrorType.
"""

import pytest
from datetime import datetime


class TestConnectionState:
    """Tests for ConnectionState enum."""

    def test_connection_states_exist(self) -> None:
        """Verify all expected connection states exist."""
        from buderus_wps_cli.tui.state import ConnectionState

        assert hasattr(ConnectionState, "CONNECTING")
        assert hasattr(ConnectionState, "CONNECTED")
        assert hasattr(ConnectionState, "DISCONNECTED")
        assert hasattr(ConnectionState, "TIMEOUT")
        assert hasattr(ConnectionState, "ERROR")

    def test_connection_state_values_unique(self) -> None:
        """Each connection state should have a unique value."""
        from buderus_wps_cli.tui.state import ConnectionState

        states = [s for s in ConnectionState]
        values = [s.value for s in states]
        assert len(values) == len(set(values))


class TestScreenType:
    """Tests for ScreenType enum."""

    def test_screen_types_exist(self) -> None:
        """Verify all expected screen types exist."""
        from buderus_wps_cli.tui.state import ScreenType

        assert hasattr(ScreenType, "DASHBOARD")
        assert hasattr(ScreenType, "MENU")
        assert hasattr(ScreenType, "EDITOR")
        assert hasattr(ScreenType, "SCHEDULE")
        assert hasattr(ScreenType, "ERROR")


class TestErrorType:
    """Tests for ErrorType enum."""

    def test_error_types_exist(self) -> None:
        """Verify all expected error types exist."""
        from buderus_wps_cli.tui.state import ErrorType

        assert hasattr(ErrorType, "CONNECTION")
        assert hasattr(ErrorType, "TIMEOUT")
        assert hasattr(ErrorType, "VALIDATION")
        assert hasattr(ErrorType, "WRITE_FAILED")
        assert hasattr(ErrorType, "UNKNOWN")


class TestErrorInfo:
    """Tests for ErrorInfo dataclass."""

    def test_error_info_creation(self) -> None:
        """Can create ErrorInfo with all required fields."""
        from buderus_wps_cli.tui.state import ErrorInfo, ErrorType

        error = ErrorInfo(
            error_type=ErrorType.CONNECTION,
            message="Connection failed",
            recoverable=True,
        )
        assert error.error_type == ErrorType.CONNECTION
        assert error.message == "Connection failed"
        assert error.recoverable is True
        assert error.details is None

    def test_error_info_with_details(self) -> None:
        """ErrorInfo can have optional details."""
        from buderus_wps_cli.tui.state import ErrorInfo, ErrorType

        error = ErrorInfo(
            error_type=ErrorType.TIMEOUT,
            message="Timeout",
            details="No response from device",
            recoverable=True,
        )
        assert error.details == "No response from device"

    def test_error_info_has_timestamp(self) -> None:
        """ErrorInfo should have a timestamp field."""
        from buderus_wps_cli.tui.state import ErrorInfo, ErrorType

        before = datetime.now()
        error = ErrorInfo(
            error_type=ErrorType.UNKNOWN,
            message="Test",
            recoverable=False,
        )
        after = datetime.now()

        assert before <= error.timestamp <= after


class TestAppState:
    """Tests for AppState dataclass."""

    def test_app_state_creation(self) -> None:
        """Can create AppState with required fields."""
        from buderus_wps_cli.tui.state import AppState, ConnectionState, ScreenType

        state = AppState(
            connection=ConnectionState.DISCONNECTED,
            screen=ScreenType.DASHBOARD,
        )
        assert state.connection == ConnectionState.DISCONNECTED
        assert state.screen == ScreenType.DASHBOARD
        assert state.error is None

    def test_app_state_with_error(self) -> None:
        """AppState can hold an error."""
        from buderus_wps_cli.tui.state import (
            AppState,
            ConnectionState,
            ScreenType,
            ErrorInfo,
            ErrorType,
        )

        error = ErrorInfo(
            error_type=ErrorType.CONNECTION,
            message="Failed",
            recoverable=True,
        )
        state = AppState(
            connection=ConnectionState.ERROR,
            screen=ScreenType.ERROR,
            error=error,
        )
        assert state.error is not None
        assert state.error.message == "Failed"

    def test_app_state_has_last_refresh(self) -> None:
        """AppState should track last refresh timestamp."""
        from buderus_wps_cli.tui.state import AppState, ConnectionState, ScreenType

        state = AppState(
            connection=ConnectionState.CONNECTED,
            screen=ScreenType.DASHBOARD,
        )
        # last_refresh should be set to now by default
        assert state.last_refresh is not None
        assert isinstance(state.last_refresh, datetime)
