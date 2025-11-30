"""Unit tests for TUI editor screen and models - T037, T038, T039.

Tests value editing with validation and input handling.
"""

import pytest
from enum import Enum
from unittest.mock import MagicMock


class TestEditorModel:
    """Unit tests for EditorModel - T037."""

    def test_editor_model_basic_attributes(self) -> None:
        """EditorModel has label, value, and value_type."""
        from buderus_wps_cli.tui.screens.editor import EditorModel, ValueType

        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
        )
        assert model.label == "DHW Temperature"
        assert model.value == "48.0"
        assert model.value_type == ValueType.TEMPERATURE

    def test_editor_model_with_unit(self) -> None:
        """EditorModel can specify unit string."""
        from buderus_wps_cli.tui.screens.editor import EditorModel, ValueType

        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
            unit="°C",
        )
        assert model.unit == "°C"

    def test_editor_model_with_range(self) -> None:
        """EditorModel can specify min/max range."""
        from buderus_wps_cli.tui.screens.editor import EditorModel, ValueType

        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        assert model.min_value == 20.0
        assert model.max_value == 65.0

    def test_editor_model_original_value(self) -> None:
        """EditorModel tracks original value for cancel."""
        from buderus_wps_cli.tui.screens.editor import EditorModel, ValueType

        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
            original_value="48.0",
        )
        assert model.original_value == "48.0"


class TestValueType:
    """Unit tests for ValueType enum - T037."""

    def test_value_type_has_temperature(self) -> None:
        """ValueType includes TEMPERATURE."""
        from buderus_wps_cli.tui.screens.editor import ValueType

        assert hasattr(ValueType, "TEMPERATURE")

    def test_value_type_has_integer(self) -> None:
        """ValueType includes INTEGER."""
        from buderus_wps_cli.tui.screens.editor import ValueType

        assert hasattr(ValueType, "INTEGER")

    def test_value_type_has_enum(self) -> None:
        """ValueType includes ENUM for list selection."""
        from buderus_wps_cli.tui.screens.editor import ValueType

        assert hasattr(ValueType, "ENUM")

    def test_value_type_has_time(self) -> None:
        """ValueType includes TIME for HH:MM format."""
        from buderus_wps_cli.tui.screens.editor import ValueType

        assert hasattr(ValueType, "TIME")


class TestEditorScreen:
    """Unit tests for EditorScreen - T038."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    def test_editor_screen_creation(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen can be created with stdscr."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        assert screen is not None

    def test_editor_screen_update_model(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen can update its model."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
        )
        screen.update_model(model)

        assert screen.model.label == "DHW Temperature"

    def test_editor_screen_render_shows_label(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen render displays the label."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
        )
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "DHW Temperature" in call_str

    def test_editor_screen_render_shows_value(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen render displays the current value."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
        )
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "48.0" in call_str

    def test_editor_screen_render_shows_range(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen render displays valid range."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        assert "20" in call_str
        assert "65" in call_str

    def test_editor_screen_number_input(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen accepts number key input."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="",
            value_type=ValueType.TEMPERATURE,
            original_value="48.0",
        )
        screen.update_model(model)

        # Type "5"
        screen.handle_key(ord("5"))
        assert screen.model.value == "5"

        # Type "0"
        screen.handle_key(ord("0"))
        assert screen.model.value == "50"

    def test_editor_screen_decimal_input(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen accepts decimal point input."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="50",
            value_type=ValueType.TEMPERATURE,
        )
        screen.update_model(model)

        screen.handle_key(ord("."))
        screen.handle_key(ord("5"))
        assert screen.model.value == "50.5"

    def test_editor_screen_backspace(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen handles backspace to delete characters."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState
        import curses

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="48.0",
            value_type=ValueType.TEMPERATURE,
        )
        screen.update_model(model)

        # Backspace
        screen.handle_key(curses.KEY_BACKSPACE)
        assert screen.model.value == "48."

    def test_editor_screen_escape_returns_cancel(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen returns cancel on Escape."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="Test",
            value="42",
            value_type=ValueType.INTEGER,
        )
        screen.update_model(model)

        result = screen.handle_key(27)  # Escape
        assert result == "cancel"

    def test_editor_screen_enter_returns_save(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen returns save on Enter with valid value."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="50.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter
        assert result == ("save", 50.0)

    def test_editor_screen_quit_returns_quit(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen returns quit on 'q' key."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="Test",
            value="42",
            value_type=ValueType.INTEGER,
        )
        screen.update_model(model)

        result = screen.handle_key(ord("q"))
        assert result == "quit"


class TestEditorValidation:
    """Unit tests for EditorScreen validation - T039."""

    @pytest.fixture
    def mock_stdscr(self) -> MagicMock:
        """Create a mock curses stdscr."""
        mock = MagicMock()
        mock.getmaxyx.return_value = (24, 80)
        return mock

    def test_validation_rejects_value_below_min(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen rejects values below minimum."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="15.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter
        assert result == "validation_error"
        assert screen.validation_error is not None

    def test_validation_rejects_value_above_max(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen rejects values above maximum."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="70.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter
        assert result == "validation_error"

    def test_validation_accepts_value_at_min(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen accepts value at minimum boundary."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="20.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter
        assert result == ("save", 20.0)

    def test_validation_accepts_value_at_max(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen accepts value at maximum boundary."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="65.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter
        assert result == ("save", 65.0)

    def test_validation_rejects_non_numeric(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen rejects non-numeric values for temperature."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="abc",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter
        assert result == "validation_error"

    def test_validation_rejects_empty_value(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen rejects empty value."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter
        assert result == "validation_error"

    def test_validation_error_cleared_on_input(self, mock_stdscr: MagicMock) -> None:
        """Validation error is cleared when user types."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="15.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        # Trigger validation error
        screen.handle_key(10)
        assert screen.validation_error is not None

        # Type new value
        screen.handle_key(ord("2"))
        assert screen.validation_error is None

    def test_integer_validation(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen validates integers without decimals."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="Count",
            value="42",
            value_type=ValueType.INTEGER,
            min_value=0.0,
            max_value=100.0,
        )
        screen.update_model(model)

        result = screen.handle_key(10)  # Enter
        assert result == ("save", 42)

    def test_validation_displays_error_message(self, mock_stdscr: MagicMock) -> None:
        """EditorScreen displays validation error message."""
        from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
        from buderus_wps_cli.tui.state import ConnectionState

        screen = EditorScreen(mock_stdscr, ConnectionState.CONNECTED)
        model = EditorModel(
            label="DHW Temperature",
            value="70.0",
            value_type=ValueType.TEMPERATURE,
            min_value=20.0,
            max_value=65.0,
        )
        screen.update_model(model)

        screen.handle_key(10)  # Enter - triggers validation
        screen.render()

        calls = [str(c) for c in mock_stdscr.addstr.call_args_list]
        call_str = " ".join(calls)

        # Should show error about max value
        assert "65" in call_str or "max" in call_str.lower() or "error" in call_str.lower()
