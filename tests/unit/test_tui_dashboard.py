"""Unit tests for TUI Dashboard - T017, T018.

Tests for DashboardModel and DashboardScreen.
"""

import curses
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch


class TestDashboardModel:
    """Tests for DashboardModel dataclass - T017."""

    def test_dashboard_model_creation(self) -> None:
        """Can create DashboardModel with all fields."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardModel

        model = DashboardModel(
            outdoor_temp=8.5,
            supply_temp=35.0,
            dhw_temp=52.0,
            operating_mode="HEATING",
            compressor_running=True,
        )
        assert model.outdoor_temp == 8.5
        assert model.supply_temp == 35.0
        assert model.dhw_temp == 52.0
        assert model.operating_mode == "HEATING"
        assert model.compressor_running is True

    def test_dashboard_model_optional_fields(self) -> None:
        """DashboardModel can have None values."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardModel

        model = DashboardModel()
        assert model.outdoor_temp is None
        assert model.supply_temp is None
        assert model.dhw_temp is None
        assert model.operating_mode is None
        assert model.compressor_running is None

    def test_dashboard_model_return_temp(self) -> None:
        """DashboardModel can include return temperature."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardModel

        model = DashboardModel(return_temp=28.5)
        assert model.return_temp == 28.5

    def test_dashboard_model_room_temp(self) -> None:
        """DashboardModel can include room temperature."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardModel

        model = DashboardModel(room_temp=21.0)
        assert model.room_temp == 21.0

    def test_dashboard_model_aux_heater(self) -> None:
        """DashboardModel can include auxiliary heater status."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardModel

        model = DashboardModel(aux_heater_active=True)
        assert model.aux_heater_active is True

    def test_dashboard_model_error_active(self) -> None:
        """DashboardModel includes error indicator."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardModel

        model = DashboardModel(error_active=True)
        assert model.error_active is True


class TestDashboardScreen:
    """Tests for DashboardScreen rendering - T018."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    def test_dashboard_screen_creation(self, mock_stdscr: MagicMock) -> None:
        """Can create DashboardScreen."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.DISCONNECTED)
        assert screen.stdscr is mock_stdscr

    def test_dashboard_screen_has_render(self, mock_stdscr: MagicMock) -> None:
        """DashboardScreen has render method."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)
        assert hasattr(screen, "render")
        assert callable(screen.render)

    def test_dashboard_screen_renders_title(self, mock_stdscr: MagicMock) -> None:
        """DashboardScreen renders the title."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)
        screen.render()

        # Should have called addstr at least once
        assert mock_stdscr.addstr.called

    def test_dashboard_screen_update_model(self, mock_stdscr: MagicMock) -> None:
        """DashboardScreen can update its model."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen, DashboardModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = DashboardModel(outdoor_temp=10.0)
        screen.update_model(model)

        assert screen.model.outdoor_temp == 10.0

    def test_dashboard_screen_shows_temperatures(self, mock_stdscr: MagicMock) -> None:
        """DashboardScreen displays temperature values."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen, DashboardModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)
        screen.update_model(DashboardModel(
            outdoor_temp=8.5,
            supply_temp=35.0,
            dhw_temp=52.0,
        ))
        screen.render()

        # Check that addstr was called with temperature-related strings
        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)
        assert "8.5" in call_str or "Outdoor" in call_str

    def test_dashboard_screen_handle_refresh_key(self, mock_stdscr: MagicMock) -> None:
        """DashboardScreen handles 'r' key for refresh."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)
        result = screen.handle_key(ord("r"))

        assert result == "refresh"

    def test_dashboard_screen_handle_quit_key(self, mock_stdscr: MagicMock) -> None:
        """DashboardScreen handles 'q' key for quit."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)
        result = screen.handle_key(ord("q"))

        assert result == "quit"

    def test_dashboard_screen_handle_enter_key(self, mock_stdscr: MagicMock) -> None:
        """DashboardScreen handles Enter key to go to menu."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)
        result = screen.handle_key(10)  # Enter key

        assert result == "menu"


class TestDashboardConnectionState:
    """Tests for dashboard connection state display."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    def test_dashboard_shows_disconnected_state(self, mock_stdscr: MagicMock) -> None:
        """Dashboard shows disconnected message when not connected."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.DISCONNECTED)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)
        # Should show disconnected or not connected
        assert "Disconnected" in call_str or "Not connected" in call_str or "DISCONNECTED" in call_str

    def test_dashboard_shows_error_message(self, mock_stdscr: MagicMock) -> None:
        """Dashboard can display error message."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.ERROR)
        screen.set_error("Connection failed: device not found")
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)
        assert "Connection failed" in call_str or "Error" in call_str or "ERROR" in call_str
