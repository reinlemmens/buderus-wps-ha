"""Editor screen for modifying parameter values.

Provides numeric input with validation against min/max ranges.
"""

import curses
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Optional, Union

from buderus_wps_cli.tui.screens.base import Screen
from buderus_wps_cli.tui.state import ConnectionState
from buderus_wps_cli.tui.keyboard import get_action
from buderus_wps_cli.tui.widgets import StatusBar, HelpBar, HelpAction


class ValueType(Enum):
    """Types of values that can be edited."""

    TEMPERATURE = auto()
    INTEGER = auto()
    ENUM = auto()
    TIME = auto()
    DATE = auto()


@dataclass
class EditorModel:
    """Data model for editor screen.

    Attributes:
        label: Display label for the value
        value: Current value being edited (as string)
        value_type: Type of value for validation
        unit: Unit string to display
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        original_value: Original value for cancel
    """

    label: str
    value: str
    value_type: ValueType
    unit: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    original_value: Optional[str] = None


class EditorScreen(Screen):
    """Value editor screen.

    Provides numeric input with live validation feedback.
    """

    def __init__(self, stdscr: Any, connection: ConnectionState) -> None:
        """Initialize the editor screen.

        Args:
            stdscr: The curses standard screen
            connection: Current connection state
        """
        super().__init__(stdscr)
        self.connection = connection
        self.model = EditorModel(label="", value="", value_type=ValueType.TEMPERATURE)
        self.validation_error: Optional[str] = None

        # Widgets
        self.status_bar = StatusBar(stdscr, self.width)
        self.help_bar = HelpBar(stdscr, self.width)
        self.help_bar.set_actions([
            HelpAction("Enter", "Save"),
            HelpAction("Esc", "Cancel"),
            HelpAction("q", "Quit"),
        ])

    def update_model(self, model: EditorModel) -> None:
        """Update the editor data model.

        Args:
            model: New editor model
        """
        self.model = model
        self.validation_error = None

    def render(self) -> None:
        """Render the editor screen."""
        self.clear()

        # Header
        self.status_bar.render(0, self.connection)

        # Separator
        self.draw_hline(1, 0, self.width)

        # Title
        self.draw_text(3, 2, "Edit Value", curses.A_BOLD)
        self.draw_hline(4, 2, 60, ord("-"))

        # Label
        self.draw_text(6, 2, self.model.label)

        # Current value with box
        value_row = 8
        self.draw_text(value_row, 2, "Value:")
        value_display = self.model.value or "_"
        if self.model.unit:
            value_display += f" {self.model.unit}"
        self.draw_text(value_row, 10, f"[ {value_display} ]", curses.A_REVERSE)

        # Range info
        if self.model.min_value is not None and self.model.max_value is not None:
            range_text = f"Range: {self.model.min_value} - {self.model.max_value}"
            if self.model.unit:
                range_text += f" {self.model.unit}"
            self.draw_text(value_row + 2, 2, range_text, curses.A_DIM)

        # Validation error
        if self.validation_error:
            self.draw_text(value_row + 4, 2, f"Error: {self.validation_error}", curses.A_BOLD)

        # Separator
        self.draw_hline(self.height - 2, 0, self.width)

        # Help bar
        self.help_bar.render(self.height - 1)

        self.refresh()

    def handle_key(self, key: int) -> Optional[Union[str, tuple[str, Any]]]:
        """Handle a key press.

        Args:
            key: The curses key code

        Returns:
            Action string, tuple of (action, value), or None
        """
        # Handle backspace first (before any other processing)
        if key in (curses.KEY_BACKSPACE, 127, 8):
            if self.model.value:
                self.model.value = self.model.value[:-1]
            return None

        action = get_action(key)

        if action == "quit":
            return "quit"
        elif action == "back":
            return "cancel"
        elif action == "select":  # Enter key
            return self._try_save()

        # Handle numeric input
        if self._is_valid_input_key(key):
            self._handle_input(key)
            return None

        return None

    def _is_valid_input_key(self, key: int) -> bool:
        """Check if key is valid for current value type.

        Args:
            key: The key code

        Returns:
            True if key is valid input
        """
        char = chr(key) if 0 <= key < 256 else ""

        if self.model.value_type in (ValueType.TEMPERATURE,):
            # Allow digits and one decimal point
            if char.isdigit():
                return True
            if char == "." and "." not in self.model.value:
                return True
            if char == "-" and not self.model.value:
                return True

        elif self.model.value_type == ValueType.INTEGER:
            # Allow digits only
            if char.isdigit():
                return True
            if char == "-" and not self.model.value:
                return True

        elif self.model.value_type == ValueType.DATE:
            # Allow digits and hyphens for YYYY-MM-DD
            if char.isdigit():
                return True
            if char == "-":
                return True

        return False

    def _handle_input(self, key: int) -> None:
        """Handle character input.

        Args:
            key: The key code
        """
        char = chr(key)
        self.model.value += char
        # Clear validation error on new input
        self.validation_error = None

    def _try_save(self) -> Union[str, tuple[str, Any]]:
        """Attempt to save the current value.

        Returns:
            ("save", value) on success, "validation_error" on failure
        """
        # Validate
        error = self._validate()
        if error:
            self.validation_error = error
            return "validation_error"

        # Parse and return value
        try:
            if self.model.value_type == ValueType.INTEGER:
                return ("save", int(float(self.model.value)))
            elif self.model.value_type == ValueType.DATE:
                return ("save", self.model.value)  # Return as string
            else:
                return ("save", float(self.model.value))
        except ValueError:
            self.validation_error = "Invalid number format"
            return "validation_error"

    def _validate(self) -> Optional[str]:
        """Validate the current value.

        Returns:
            Error message or None if valid
        """
        # Check for empty value
        if not self.model.value or not self.model.value.strip():
            return "Value cannot be empty"

        # DATE validation
        if self.model.value_type == ValueType.DATE:
            return self._validate_date()

        # Try to parse as number
        try:
            value = float(self.model.value)
        except ValueError:
            return "Invalid number format"

        # Check range
        if self.model.min_value is not None and value < self.model.min_value:
            return f"Value must be at least {self.model.min_value}"

        if self.model.max_value is not None and value > self.model.max_value:
            return f"Value must be at most {self.model.max_value}"

        return None

    def _validate_date(self) -> Optional[str]:
        """Validate date format YYYY-MM-DD.

        Returns:
            Error message or None if valid
        """
        import re
        pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        if not pattern.match(self.model.value):
            return "Invalid date format (use YYYY-MM-DD)"

        # Check date is valid
        try:
            from datetime import datetime
            datetime.strptime(self.model.value, "%Y-%m-%d")
        except ValueError:
            return "Invalid date"

        return None

    def handle_resize(self) -> None:
        """Handle terminal resize."""
        super().handle_resize()
        self.status_bar.update_width(self.width)
        self.help_bar.update_width(self.width)
