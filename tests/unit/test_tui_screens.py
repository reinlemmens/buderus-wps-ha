"""Unit tests for TUI base screen class - T007.

Tests for Screen base class with curses wrapper.
"""

import curses
import pytest
from unittest.mock import MagicMock, patch


class TestScreenBase:
    """Tests for Screen base class."""

    def test_screen_requires_stdscr(self) -> None:
        """Screen should require a curses stdscr on init."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        assert screen.stdscr is mock_stdscr

    def test_screen_stores_dimensions(self) -> None:
        """Screen should store terminal dimensions."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        assert screen.height == 24
        assert screen.width == 80

    def test_screen_has_render_method(self) -> None:
        """Screen should have a render method."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        assert hasattr(screen, "render")
        assert callable(screen.render)

    def test_screen_has_handle_key_method(self) -> None:
        """Screen should have a handle_key method."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        assert hasattr(screen, "handle_key")
        assert callable(screen.handle_key)

    def test_screen_clear_calls_stdscr_clear(self) -> None:
        """Screen.clear should call stdscr.clear."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        screen.clear()

        mock_stdscr.clear.assert_called_once()

    def test_screen_refresh_calls_stdscr_refresh(self) -> None:
        """Screen.refresh should call stdscr.refresh."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        screen.refresh()

        mock_stdscr.refresh.assert_called_once()

    def test_screen_update_dimensions_on_resize(self) -> None:
        """Screen should update dimensions when resize is called."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        assert screen.height == 24
        assert screen.width == 80

        # Simulate resize
        mock_stdscr.getmaxyx.return_value = (40, 120)
        screen.handle_resize()

        assert screen.height == 40
        assert screen.width == 120


class TestScreenDrawing:
    """Tests for Screen drawing helpers."""

    def test_draw_text_at_position(self) -> None:
        """Screen should be able to draw text at a position."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        screen.draw_text(5, 10, "Hello")

        mock_stdscr.addstr.assert_called_with(5, 10, "Hello", 0)

    def test_draw_text_with_attribute(self) -> None:
        """Screen should support text attributes."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        screen.draw_text(0, 0, "Bold", curses.A_BOLD)

        mock_stdscr.addstr.assert_called_with(0, 0, "Bold", curses.A_BOLD)

    def test_draw_text_truncates_at_width(self) -> None:
        """Screen should truncate text that exceeds width."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 10)  # Narrow terminal

        screen = Screen(mock_stdscr)
        screen.draw_text(0, 0, "This is a very long string")

        # Should truncate to width-1 to avoid curses error
        call_args = mock_stdscr.addstr.call_args
        drawn_text = call_args[0][2]
        assert len(drawn_text) <= 10

    def test_draw_horizontal_line(self) -> None:
        """Screen should be able to draw horizontal lines."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        screen.draw_hline(5, 0, 80)

        mock_stdscr.hline.assert_called()


class TestMinimumSizeCheck:
    """Tests for minimum terminal size handling."""

    def test_screen_checks_minimum_size(self) -> None:
        """Screen should report if terminal is too small."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (20, 60)  # Too small

        screen = Screen(mock_stdscr)
        assert screen.is_too_small() is True

    def test_screen_minimum_80x24(self) -> None:
        """Screen minimum should be 80x24."""
        from buderus_wps_cli.tui.screens.base import Screen

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = Screen(mock_stdscr)
        assert screen.is_too_small() is False

        # Just under minimum
        mock_stdscr.getmaxyx.return_value = (23, 80)
        screen.handle_resize()
        assert screen.is_too_small() is True


class TestEnergyDisplay:
    """Tests for energy statistics display - T059."""

    def test_menu_displays_energy_values(self) -> None:
        """Menu can display energy kWh values."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)

        items = [
            MenuItemModel(
                id="heat_generated",
                label="Heat Generated",
                item_type="parameter",
                value="12,345 kWh",
                read_only=True,
            ),
            MenuItemModel(
                id="aux_heater",
                label="Aux Heater Consumption",
                item_type="parameter",
                value="456 kWh",
                read_only=True,
            ),
        ]
        model = MenuModel(title="Energy Statistics", items=items)
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "12,345" in call_str or "12345" in call_str
        assert "kWh" in call_str


class TestAlarmDisplay:
    """Tests for alarm list display - T064, T065."""

    def test_menu_displays_alarm_list(self) -> None:
        """Menu can display alarm items."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)

        items = [
            MenuItemModel(
                id="alarm_1",
                label="E01: Pressure Too Low",
                item_type="alarm",
                value="2024-01-15 10:30",
            ),
            MenuItemModel(
                id="alarm_2",
                label="E05: Sensor Fault",
                item_type="alarm",
                value="2024-01-14 08:15",
            ),
        ]
        model = MenuModel(title="Active Alarms", items=items)
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "E01" in call_str
        assert "Pressure" in call_str

    def test_menu_shows_no_alarms_message(self) -> None:
        """Menu shows message when no alarms."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)

        items = [
            MenuItemModel(
                id="no_alarms",
                label="No active alarms",
                item_type="info",
            ),
        ]
        model = MenuModel(title="Active Alarms", items=items)
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "No active" in call_str or "no active" in call_str.lower()

    def test_alarm_acknowledge_action(self) -> None:
        """Menu returns acknowledge action for alarm items."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)

        items = [
            MenuItemModel(
                id="alarm_1",
                label="E01: Pressure Too Low",
                item_type="alarm",
            ),
        ]
        model = MenuModel(title="Active Alarms", items=items)
        screen.update_model(model)

        # Press Enter on alarm
        result = screen.handle_key(10)

        # Should return select with alarm id
        assert result == ("select", "alarm_1")


class TestDateEditing:
    """Tests for date input in editor - T071, T072."""

    def test_editor_date_type_exists(self) -> None:
        """EditorScreen ValueType includes DATE."""
        from buderus_wps_cli.tui.screens.editor import ValueType

        assert hasattr(ValueType, "DATE")

    def test_editor_displays_date_value(self) -> None:
        """EditorScreen can display date values."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)

        model = EditorModel(
            label="Vacation Start",
            value="2024-06-15",
            value_type=ValueType.DATE,
        )
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "2024" in call_str
        assert "Vacation" in call_str

    def test_editor_validates_date_format(self) -> None:
        """EditorScreen validates date format."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)

        # Invalid date format
        model = EditorModel(
            label="Vacation Start",
            value="invalid",
            value_type=ValueType.DATE,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter

        assert result == "validation_error"

    def test_editor_accepts_valid_date(self) -> None:
        """EditorScreen accepts valid date."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        mock_stdscr = MagicMock()
        mock_stdscr.getmaxyx.return_value = (24, 80)

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)

        model = EditorModel(
            label="Vacation Start",
            value="2024-06-15",
            value_type=ValueType.DATE,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter

        assert result == ("save", "2024-06-15")
