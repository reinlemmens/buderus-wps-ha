"""Unit tests for TUI schedule screen and models - T048, T049, T050.

Tests schedule display and time editing with 30-minute boundary validation.
"""

import pytest
from unittest.mock import MagicMock


class TestDayScheduleModel:
    """Unit tests for DayScheduleModel - T048."""

    def test_day_schedule_basic_attributes(self) -> None:
        """DayScheduleModel has day name and time slots."""
        from buderus_wps_cli.tui.screens.schedule import DayScheduleModel

        day = DayScheduleModel(
            day_name="Monday",
            on_time="06:00",
            off_time="22:00",
        )
        assert day.day_name == "Monday"
        assert day.on_time == "06:00"
        assert day.off_time == "22:00"

    def test_day_schedule_short_name(self) -> None:
        """DayScheduleModel has short day name."""
        from buderus_wps_cli.tui.screens.schedule import DayScheduleModel

        day = DayScheduleModel(
            day_name="Monday",
            day_short="Mon",
            on_time="06:00",
            off_time="22:00",
        )
        assert day.day_short == "Mon"

    def test_day_schedule_defaults(self) -> None:
        """DayScheduleModel defaults for short name."""
        from buderus_wps_cli.tui.screens.schedule import DayScheduleModel

        day = DayScheduleModel(
            day_name="Monday",
            on_time="06:00",
            off_time="22:00",
        )
        # Day short defaults to first 3 chars of day_name
        assert day.day_short == "Mon"


class TestScheduleModel:
    """Unit tests for ScheduleModel - T048."""

    def test_schedule_model_has_title_and_days(self) -> None:
        """ScheduleModel holds title and list of days."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleModel, DayScheduleModel

        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
            DayScheduleModel(day_name="Tuesday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)

        assert model.title == "DHW Program 1"
        assert len(model.days) == 2

    def test_schedule_model_selected_day(self) -> None:
        """ScheduleModel tracks selected day index."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleModel, DayScheduleModel

        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
            DayScheduleModel(day_name="Tuesday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days, selected_day=1)

        assert model.selected_day == 1

    def test_schedule_model_selected_field(self) -> None:
        """ScheduleModel tracks selected field (on_time/off_time)."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleModel, DayScheduleModel

        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days, selected_field="off_time")

        assert model.selected_field == "off_time"

    def test_schedule_model_edit_mode(self) -> None:
        """ScheduleModel tracks edit mode state."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleModel, DayScheduleModel

        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days, editing=True)

        assert model.editing is True


class TestScheduleScreen:
    """Unit tests for ScheduleScreen - T049."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    def test_schedule_screen_creation(self, mock_stdscr: MagicMock) -> None:
        """ScheduleScreen can be created with stdscr."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        assert screen is not None

    def test_schedule_screen_update_model(self, mock_stdscr: MagicMock) -> None:
        """ScheduleScreen can update its model."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)
        screen.update_model(model)

        assert screen.model.title == "DHW Program 1"

    def test_schedule_screen_render_shows_days(self, mock_stdscr: MagicMock) -> None:
        """ScheduleScreen render displays day names."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
            DayScheduleModel(day_name="Tuesday", on_time="07:00", off_time="21:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "Mon" in call_str
        assert "Tue" in call_str

    def test_schedule_screen_render_shows_times(self, mock_stdscr: MagicMock) -> None:
        """ScheduleScreen render displays on/off times."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "06:00" in call_str
        assert "22:00" in call_str

    def test_schedule_screen_navigate_days(self, mock_stdscr: MagicMock) -> None:
        """ScheduleScreen navigates days with up/down keys."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
            DayScheduleModel(day_name="Tuesday", on_time="07:00", off_time="21:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)
        screen.update_model(model)

        # Move down
        screen.handle_key(curses.KEY_DOWN)
        assert screen.model.selected_day == 1

    def test_schedule_screen_navigate_fields(self, mock_stdscr: MagicMock) -> None:
        """ScheduleScreen navigates fields with left/right keys."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days, selected_field="on_time")
        screen.update_model(model)

        # Move right to off_time
        screen.handle_key(curses.KEY_RIGHT)
        assert screen.model.selected_field == "off_time"

    def test_schedule_screen_enter_edit_mode(self, mock_stdscr: MagicMock) -> None:
        """ScheduleScreen enters edit mode on Enter."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)
        screen.update_model(model)

        screen.handle_key(10)  # Enter
        assert screen.model.editing is True

    def test_schedule_screen_escape_returns_back(self, mock_stdscr: MagicMock) -> None:
        """ScheduleScreen returns back on Escape when not editing."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)
        screen.update_model(model)

        result = screen.handle_key(27)  # Escape
        assert result == "back"


class TestTimeValidation:
    """Unit tests for 30-minute boundary validation - T050."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    def test_valid_30_minute_boundary(self, mock_stdscr: MagicMock) -> None:
        """Valid times on 30-minute boundaries are accepted."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)

        assert screen.validate_time("06:00") is True
        assert screen.validate_time("06:30") is True
        assert screen.validate_time("12:00") is True
        assert screen.validate_time("23:30") is True

    def test_invalid_non_30_minute_boundary(self, mock_stdscr: MagicMock) -> None:
        """Times not on 30-minute boundaries are rejected."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)

        assert screen.validate_time("06:15") is False
        assert screen.validate_time("06:45") is False
        assert screen.validate_time("12:10") is False
        assert screen.validate_time("23:59") is False

    def test_invalid_time_format(self, mock_stdscr: MagicMock) -> None:
        """Invalid time formats are rejected."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)

        assert screen.validate_time("6:00") is False  # Missing leading zero
        assert screen.validate_time("25:00") is False  # Invalid hour
        assert screen.validate_time("12:60") is False  # Invalid minute

    def test_time_edit_increments_by_30_minutes(self, mock_stdscr: MagicMock) -> None:
        """Time editing increments/decrements by 30 minutes."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW", days=days, editing=True, selected_field="on_time")
        screen.update_model(model)

        # Increment by 30 min
        screen.handle_key(curses.KEY_UP)
        assert screen.model.days[0].on_time == "06:30"

    def test_time_edit_wraps_at_midnight(self, mock_stdscr: MagicMock) -> None:
        """Time editing wraps at midnight boundaries."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="23:30", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW", days=days, editing=True, selected_field="on_time")
        screen.update_model(model)

        # Increment past midnight
        screen.handle_key(curses.KEY_UP)
        assert screen.model.days[0].on_time == "00:00"

    def test_time_edit_wraps_at_zero(self, mock_stdscr: MagicMock) -> None:
        """Time editing wraps at zero boundary."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)
        days = [
            DayScheduleModel(day_name="Monday", on_time="00:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW", days=days, editing=True, selected_field="on_time")
        screen.update_model(model)

        # Decrement past zero
        screen.handle_key(curses.KEY_DOWN)
        assert screen.model.days[0].on_time == "23:30"
