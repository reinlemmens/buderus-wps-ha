"""Unit tests for TUI menu screen and models - T026, T027, T028.

Tests menu navigation, item models, and rendering.
"""

import pytest
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock


class TestMenuItemModel:
    """Unit tests for MenuItemModel - T026."""

    def test_menu_item_basic_attributes(self) -> None:
        """MenuItemModel has id, label, and item_type."""
        from buderus_wps_cli.tui.screens.menu import MenuItemModel

        item = MenuItemModel(
            id="hot_water",
            label="Hot Water",
            item_type="submenu",
        )
        assert item.id == "hot_water"
        assert item.label == "Hot Water"
        assert item.item_type == "submenu"

    def test_menu_item_with_value(self) -> None:
        """MenuItemModel can hold a current value."""
        from buderus_wps_cli.tui.screens.menu import MenuItemModel

        item = MenuItemModel(
            id="dhw_temp",
            label="DHW Temperature",
            item_type="parameter",
            value="48.0°C",
        )
        assert item.value == "48.0°C"

    def test_menu_item_with_read_only_flag(self) -> None:
        """MenuItemModel can indicate read-only parameters."""
        from buderus_wps_cli.tui.screens.menu import MenuItemModel

        item = MenuItemModel(
            id="outdoor_temp",
            label="Outdoor Temperature",
            item_type="parameter",
            value="8.5°C",
            read_only=True,
        )
        assert item.read_only is True

    def test_menu_item_defaults(self) -> None:
        """MenuItemModel has sensible defaults."""
        from buderus_wps_cli.tui.screens.menu import MenuItemModel

        item = MenuItemModel(
            id="test",
            label="Test",
            item_type="submenu",
        )
        assert item.value is None
        assert item.read_only is False


class TestMenuModel:
    """Unit tests for MenuModel - T026."""

    def test_menu_model_has_title_and_items(self) -> None:
        """MenuModel holds menu title and items list."""
        from buderus_wps_cli.tui.screens.menu import MenuModel, MenuItemModel

        items = [
            MenuItemModel(id="item1", label="Item 1", item_type="submenu"),
            MenuItemModel(id="item2", label="Item 2", item_type="submenu"),
        ]
        model = MenuModel(title="Main Menu", items=items)

        assert model.title == "Main Menu"
        assert len(model.items) == 2
        assert model.items[0].label == "Item 1"

    def test_menu_model_selected_index(self) -> None:
        """MenuModel tracks selected item index."""
        from buderus_wps_cli.tui.screens.menu import MenuModel, MenuItemModel

        items = [
            MenuItemModel(id="item1", label="Item 1", item_type="submenu"),
            MenuItemModel(id="item2", label="Item 2", item_type="submenu"),
        ]
        model = MenuModel(title="Menu", items=items, selected_index=1)

        assert model.selected_index == 1

    def test_menu_model_selected_index_defaults_to_zero(self) -> None:
        """MenuModel defaults to first item selected."""
        from buderus_wps_cli.tui.screens.menu import MenuModel, MenuItemModel

        items = [MenuItemModel(id="item1", label="Item 1", item_type="submenu")]
        model = MenuModel(title="Menu", items=items)

        assert model.selected_index == 0

    def test_menu_model_empty_items(self) -> None:
        """MenuModel handles empty items list."""
        from buderus_wps_cli.tui.screens.menu import MenuModel

        model = MenuModel(title="Empty Menu", items=[])
        assert len(model.items) == 0


class TestNavigationState:
    """Unit tests for NavigationState - T027."""

    def test_navigation_state_initial_path(self) -> None:
        """NavigationState starts with empty path."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()
        assert nav.path == []
        assert nav.current_menu_id is None

    def test_navigation_state_push_path(self) -> None:
        """NavigationState can push path segments."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()
        nav.push("Hot Water")

        assert nav.path == ["Hot Water"]

    def test_navigation_state_push_multiple(self) -> None:
        """NavigationState can push multiple path segments."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()
        nav.push("Hot Water")
        nav.push("Temperature")

        assert nav.path == ["Hot Water", "Temperature"]

    def test_navigation_state_pop_path(self) -> None:
        """NavigationState can pop path segments."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()
        nav.push("Hot Water")
        nav.push("Temperature")
        popped = nav.pop()

        assert popped == "Temperature"
        assert nav.path == ["Hot Water"]

    def test_navigation_state_pop_empty_returns_none(self) -> None:
        """NavigationState pop on empty path returns None."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()
        result = nav.pop()

        assert result is None
        assert nav.path == []

    def test_navigation_state_clear(self) -> None:
        """NavigationState can clear entire path."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()
        nav.push("Hot Water")
        nav.push("Temperature")
        nav.clear()

        assert nav.path == []

    def test_navigation_state_current_menu_id(self) -> None:
        """NavigationState tracks current menu ID."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()
        nav.current_menu_id = "hot_water"

        assert nav.current_menu_id == "hot_water"

    def test_navigation_state_is_at_root(self) -> None:
        """NavigationState can check if at root level."""
        from buderus_wps_cli.tui.state import NavigationState

        nav = NavigationState()
        assert nav.is_at_root() is True

        nav.push("Hot Water")
        assert nav.is_at_root() is False


class TestMenuScreen:
    """Unit tests for MenuScreen - T028."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    def test_menu_screen_creation(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen can be created with stdscr."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        assert screen is not None

    def test_menu_screen_update_model(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen can update its model."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Main Menu",
            items=[MenuItemModel(id="item1", label="Item 1", item_type="submenu")],
        )
        screen.update_model(model)

        assert screen.model.title == "Main Menu"

    def test_menu_screen_render_calls_addstr(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen render draws menu items."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Main Menu",
            items=[
                MenuItemModel(id="hw", label="Hot Water", item_type="submenu"),
                MenuItemModel(id="heat", label="Heating", item_type="submenu"),
            ],
        )
        screen.update_model(model)
        screen.render()

        # Verify addstr was called with menu items
        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "Hot Water" in call_str
        assert "Heating" in call_str

    def test_menu_screen_move_down(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen moves selection down on down key."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[
                MenuItemModel(id="item1", label="Item 1", item_type="submenu"),
                MenuItemModel(id="item2", label="Item 2", item_type="submenu"),
            ],
        )
        screen.update_model(model)

        # Move down
        screen.handle_key(curses.KEY_DOWN)

        assert screen.model.selected_index == 1

    def test_menu_screen_move_up(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen moves selection up on up key."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[
                MenuItemModel(id="item1", label="Item 1", item_type="submenu"),
                MenuItemModel(id="item2", label="Item 2", item_type="submenu"),
            ],
            selected_index=1,
        )
        screen.update_model(model)

        # Move up
        screen.handle_key(curses.KEY_UP)

        assert screen.model.selected_index == 0

    def test_menu_screen_wraps_at_bottom(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen wraps to top when moving down past last item."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[
                MenuItemModel(id="item1", label="Item 1", item_type="submenu"),
                MenuItemModel(id="item2", label="Item 2", item_type="submenu"),
            ],
            selected_index=1,  # At last item
        )
        screen.update_model(model)

        # Move down - should wrap to top
        screen.handle_key(curses.KEY_DOWN)

        assert screen.model.selected_index == 0

    def test_menu_screen_wraps_at_top(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen wraps to bottom when moving up past first item."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[
                MenuItemModel(id="item1", label="Item 1", item_type="submenu"),
                MenuItemModel(id="item2", label="Item 2", item_type="submenu"),
            ],
            selected_index=0,  # At first item
        )
        screen.update_model(model)

        # Move up - should wrap to bottom
        screen.handle_key(curses.KEY_UP)

        assert screen.model.selected_index == 1

    def test_menu_screen_enter_returns_select_action(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen returns select action on Enter key."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[MenuItemModel(id="hw", label="Hot Water", item_type="submenu")],
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter key

        assert result == ("select", "hw")

    def test_menu_screen_escape_returns_back(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen returns back action on Escape key."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[MenuItemModel(id="item1", label="Item 1", item_type="submenu")],
        )
        screen.update_model(model)

        result = screen.handle_key(27)  # Escape key

        assert result == "back"

    def test_menu_screen_quit_returns_quit(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen returns quit action on 'q' key."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[MenuItemModel(id="item1", label="Item 1", item_type="submenu")],
        )
        screen.update_model(model)

        result = screen.handle_key(ord("q"))

        assert result == "quit"

    def test_menu_screen_displays_values_for_parameters(
        self, mock_stdscr: MagicMock
    ) -> None:
        """MenuScreen displays values for parameter items."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Hot Water",
            items=[
                MenuItemModel(
                    id="dhw_temp",
                    label="DHW Temperature",
                    item_type="parameter",
                    value="48.0°C",
                ),
            ],
        )
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "DHW Temperature" in call_str
        assert "48.0" in call_str

    def test_menu_screen_displays_breadcrumb(self, mock_stdscr: MagicMock) -> None:
        """MenuScreen displays breadcrumb path."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Temperature",
            items=[MenuItemModel(id="item1", label="Setpoint", item_type="parameter")],
        )
        screen.update_model(model)
        screen.set_path(["Hot Water", "Temperature"])
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        # Breadcrumb should show path
        assert "Hot Water" in call_str

    def test_menu_screen_highlights_selected_item(
        self, mock_stdscr: MagicMock
    ) -> None:
        """MenuScreen highlights the selected item with reverse video."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[
                MenuItemModel(id="item1", label="Item 1", item_type="submenu"),
                MenuItemModel(id="item2", label="Item 2", item_type="submenu"),
            ],
            selected_index=0,
        )
        screen.update_model(model)
        screen.render()

        # Check that A_REVERSE was used in at least one call
        calls = mock_stdscr.addstr.call_args_list
        has_reverse = any(curses.A_REVERSE in (c.args + tuple(c.kwargs.values()))
                         for c in calls if len(c.args) > 2 or c.kwargs)
        assert has_reverse

    def test_menu_screen_refresh_returns_refresh(
        self, mock_stdscr: MagicMock
    ) -> None:
        """MenuScreen returns refresh action on 'r' key."""
        from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
        from buderus_wps_cli.tui.state import ConnectionState

        screen = MenuScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = MenuModel(
            title="Menu",
            items=[MenuItemModel(id="item1", label="Item 1", item_type="submenu")],
        )
        screen.update_model(model)

        result = screen.handle_key(ord("r"))

        assert result == "refresh"
