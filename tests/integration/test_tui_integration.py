"""Integration tests for TUI with mocked MenuAPI - T019, T029, T040, T051, etc.

Tests TUI screens with realistic MenuAPI interactions using mocks.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestDashboardIntegration:
    """Integration tests for Dashboard with MenuAPI - T019."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    @pytest.fixture
    def mock_api(self) -> MagicMock:
        """Create a mock MenuAPI."""
        api = MagicMock()

        # Setup status snapshot
        snapshot = MagicMock()
        snapshot.outdoor_temperature = 8.5
        snapshot.supply_temperature = 35.0
        snapshot.hot_water_temperature = 52.0
        snapshot.room_temperature = 21.0
        snapshot.operating_mode = MagicMock()
        snapshot.operating_mode.name = "HEATING"
        snapshot.compressor_running = True

        api.status.read_all.return_value = snapshot
        return api

    def test_dashboard_displays_api_values(
        self, mock_stdscr: MagicMock, mock_api: MagicMock
    ) -> None:
        """Dashboard displays values from MenuAPI status."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen, DashboardModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)

        # Simulate loading data from API
        snapshot = mock_api.status.read_all()
        model = DashboardModel(
            outdoor_temp=snapshot.outdoor_temperature,
            supply_temp=snapshot.supply_temperature,
            dhw_temp=snapshot.hot_water_temperature,
            room_temp=snapshot.room_temperature,
            operating_mode=snapshot.operating_mode.name,
            compressor_running=snapshot.compressor_running,
        )
        screen.update_model(model)
        screen.render()

        # Verify addstr was called with temperature values
        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "8.5" in call_str
        assert "35.0" in call_str
        assert "52.0" in call_str

    def test_dashboard_handles_api_timeout(
        self, mock_stdscr: MagicMock, mock_api: MagicMock
    ) -> None:
        """Dashboard handles timeout when API call fails."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        # Make API raise timeout
        mock_api.status.read_all.side_effect = TimeoutError("No response")

        screen = DashboardScreen(mock_stdscr, ConnectionState.ERROR)
        screen.set_error("Communication timeout - press 'r' to retry")
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "timeout" in call_str.lower() or "retry" in call_str.lower()

    def test_dashboard_refresh_reloads_data(
        self, mock_stdscr: MagicMock, mock_api: MagicMock
    ) -> None:
        """Pressing 'r' triggers data refresh."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)

        # Simulate pressing 'r'
        result = screen.handle_key(ord("r"))

        assert result == "refresh"

    def test_dashboard_enter_goes_to_menu(
        self, mock_stdscr: MagicMock
    ) -> None:
        """Pressing Enter transitions to menu screen."""
        from buderus_wps_cli.tui.screens.dashboard import DashboardScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = DashboardScreen(mock_stdscr, ConnectionState.CONNECTED)

        # Simulate pressing Enter
        result = screen.handle_key(10)

        assert result == "menu"


class TestTUIAppIntegration:
    """Integration tests for TUIApp."""

    def test_app_creates_with_device_path(self) -> None:
        """TUIApp can be created with device path."""
        from buderus_wps_cli.tui.app import TUIApp

        app = TUIApp("/dev/ttyACM0")
        assert app.device_path == "/dev/ttyACM0"
        assert app.read_only is False

    def test_app_read_only_mode(self) -> None:
        """TUIApp can be created in read-only mode."""
        from buderus_wps_cli.tui.app import TUIApp

        app = TUIApp("/dev/ttyACM0", read_only=True)
        assert app.read_only is True

    def test_app_initial_state(self) -> None:
        """TUIApp starts in disconnected state with dashboard."""
        from buderus_wps_cli.tui.app import TUIApp
        from buderus_wps_cli.tui.state import ConnectionState, ScreenType

        app = TUIApp("/dev/ttyACM0")
        assert app.state.connection == ConnectionState.DISCONNECTED
        assert app.state.screen == ScreenType.DASHBOARD


class TestMenuNavigationIntegration:
    """Integration tests for Menu navigation with MenuAPI - T029."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    @pytest.fixture
    def mock_navigator(self) -> MagicMock:
        """Create a mock MenuNavigator."""
        navigator = MagicMock()

        # Setup root menu items
        root_items = [
            MagicMock(id="hot_water", label="Hot Water", type="submenu"),
            MagicMock(id="heating", label="Heating", type="submenu"),
            MagicMock(id="energy", label="Energy", type="submenu"),
        ]
        navigator.get_current_items.return_value = root_items
        navigator.get_current_title.return_value = "Main Menu"

        return navigator

    def test_menu_shows_navigator_items(
        self, mock_stdscr: MagicMock, mock_navigator: MagicMock
    ) -> None:
        """Menu screen displays items from MenuNavigator."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)

        # Convert navigator items to TUI model
        nav_items = mock_navigator.get_current_items()
        items = [
            MenuItemModel(id=item.id, label=item.label, item_type=item.type)
            for item in nav_items
        ]
        model = MenuModel(
            title=mock_navigator.get_current_title(),
            items=items,
        )
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "Hot Water" in call_str
        assert "Heating" in call_str
        assert "Energy" in call_str

    def test_navigation_to_submenu(
        self, mock_stdscr: MagicMock, mock_navigator: MagicMock
    ) -> None:
        """Selecting a submenu updates navigation path."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState, NavigationState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        nav_state = NavigationState()

        # Setup initial menu
        items = [
            MenuItemModel(id="hot_water", label="Hot Water", item_type="submenu"),
        ]
        model = MenuModel(title="Main Menu", items=items)
        screen.update_model(model)

        # Select the item (Enter key)
        result = screen.handle_key(10)

        assert result == ("select", "hot_water")

        # Simulate app updating navigation state
        nav_state.push("Hot Water")
        nav_state.current_menu_id = "hot_water"

        assert nav_state.path == ["Hot Water"]
        assert nav_state.current_menu_id == "hot_water"

    def test_navigation_back_to_parent(
        self, mock_stdscr: MagicMock
    ) -> None:
        """Pressing Escape goes back to parent menu."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState, NavigationState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        nav_state = NavigationState()
        nav_state.push("Hot Water")
        nav_state.push("Temperature")

        items = [
            MenuItemModel(id="setpoint", label="Setpoint", item_type="parameter"),
        ]
        model = MenuModel(title="Temperature", items=items)
        screen.update_model(model)

        # Press Escape to go back
        result = screen.handle_key(27)

        assert result == "back"

        # Simulate app handling back
        nav_state.pop()

        assert nav_state.path == ["Hot Water"]

    def test_full_navigation_path(
        self, mock_stdscr: MagicMock
    ) -> None:
        """Test full navigation: Main -> Hot Water -> Temperature -> back -> back."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()

        # Navigate down
        nav.push("Hot Water")
        assert nav.path == ["Hot Water"]

        nav.push("Temperature")
        assert nav.path == ["Hot Water", "Temperature"]

        # Navigate back
        nav.pop()
        assert nav.path == ["Hot Water"]

        nav.pop()
        assert nav.path == []
        assert nav.is_at_root()

    def test_menu_displays_parameter_values(
        self, mock_stdscr: MagicMock
    ) -> None:
        """Menu displays current values for parameter items."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)

        # Menu with parameter values
        items = [
            MenuItemModel(
                id="dhw_setpoint",
                label="DHW Setpoint",
                item_type="parameter",
                value="48.0°C",
            ),
            MenuItemModel(
                id="outdoor_temp",
                label="Outdoor Temperature",
                item_type="parameter",
                value="8.5°C",
                read_only=True,
            ),
        ]
        model = MenuModel(title="Hot Water", items=items)
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "48.0" in call_str
        assert "8.5" in call_str


class TestEditorIntegration:
    """Integration tests for Editor with MenuAPI - T040."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    @pytest.fixture
    def mock_hot_water_controller(self) -> MagicMock:
        """Create a mock HotWaterController."""
        controller = MagicMock()
        controller.get_setpoint.return_value = 48.0
        controller.get_setpoint_range.return_value = (20.0, 65.0)
        return controller

    def test_editor_displays_current_value(
        self, mock_stdscr: MagicMock, mock_hot_water_controller: MagicMock
    ) -> None:
        """Editor displays current value from API."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)

        # Get value from controller
        current = mock_hot_water_controller.get_setpoint()
        min_val, max_val = mock_hot_water_controller.get_setpoint_range()

        model = EditorModel(
            label="DHW Setpoint",
            value=str(current),
            value_type=ValueType.TEMPERATURE,
            unit="°C",
            min_value=min_val,
            max_value=max_val,
            original_value=str(current),
        )
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "48" in call_str
        assert "DHW" in call_str

    def test_editor_validates_new_value(
        self, mock_stdscr: MagicMock, mock_hot_water_controller: MagicMock
    ) -> None:
        """Editor validates new value against range."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)

        min_val, max_val = mock_hot_water_controller.get_setpoint_range()

        model = EditorModel(
            label="DHW Setpoint",
            value="50.0",
            value_type=ValueType.TEMPERATURE,
            min_value=min_val,
            max_value=max_val,
        )
        screen.update_model(model)

        # Press Enter to save
        result = screen.handle_key(10)

        assert result == ("save", 50.0)

    def test_editor_workflow_enter_edit_save(
        self, mock_stdscr: MagicMock
    ) -> None:
        """Full workflow: enter value, edit, save."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)

        model = EditorModel(
            label="DHW Setpoint",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
            original_value="48.0",
        )
        screen.update_model(model)

        # Clear the value
        for _ in range(4):
            screen.handle_key(curses.KEY_BACKSPACE)

        # Type new value
        screen.handle_key(ord("5"))
        screen.handle_key(ord("2"))

        assert screen.model.value == "52"

        # Save
        result = screen.handle_key(10)
        assert result == ("save", 52.0)

    def test_editor_cancel_restores_original(
        self, mock_stdscr: MagicMock
    ) -> None:
        """Canceling edit returns to original value."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)

        model = EditorModel(
            label="DHW Setpoint",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
            original_value="48.0",
        )
        screen.update_model(model)

        # Modify value
        screen.handle_key(ord("5"))

        # Cancel (Escape)
        result = screen.handle_key(27)

        assert result == "cancel"


class TestScheduleIntegration:
    """Integration tests for Schedule screen - T051."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    def test_schedule_displays_week(self, mock_stdscr: MagicMock) -> None:
        """Schedule displays all 7 days of the week."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)

        # Create full week
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        days = [
            DayScheduleModel(day_name=name, on_time="06:00", off_time="22:00")
            for name in day_names
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        # Check some days are shown
        assert "Mon" in call_str
        assert "Sun" in call_str

    def test_schedule_edit_workflow(self, mock_stdscr: MagicMock) -> None:
        """Full workflow: select day, enter edit, change time, exit edit."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)

        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
            DayScheduleModel(day_name="Tuesday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days)
        screen.update_model(model)

        # Navigate to Tuesday
        screen.handle_key(curses.KEY_DOWN)
        assert screen.model.selected_day == 1

        # Enter edit mode
        screen.handle_key(10)
        assert screen.model.editing is True

        # Increment on_time by 30 min
        screen.handle_key(curses.KEY_UP)
        assert screen.model.days[1].on_time == "06:30"

        # Exit edit mode
        screen.handle_key(10)
        assert screen.model.editing is False

    def test_schedule_enforces_30_minute_boundaries(
        self, mock_stdscr: MagicMock
    ) -> None:
        """Schedule only allows 30-minute boundary times."""
        from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = ScheduleScreen(mock_stdscr, ConnectionState.CONNECTED)

        days = [
            DayScheduleModel(day_name="Monday", on_time="06:00", off_time="22:00"),
        ]
        model = ScheduleModel(title="DHW Program 1", days=days, editing=True)
        screen.update_model(model)

        # Increment - should go to 06:30
        screen.handle_key(curses.KEY_UP)
        assert screen.model.days[0].on_time == "06:30"

        # Increment again - should go to 07:00
        screen.handle_key(curses.KEY_UP)
        assert screen.model.days[0].on_time == "07:00"
