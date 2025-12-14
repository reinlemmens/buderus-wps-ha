"""Schedule screen for viewing and editing weekly schedules.

Displays a weekly grid with on/off times and supports editing with
30-minute boundary validation.
"""

import curses
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from buderus_wps_cli.tui.screens.base import Screen
from buderus_wps_cli.tui.state import ConnectionState
from buderus_wps_cli.tui.keyboard import get_action
from buderus_wps_cli.tui.widgets import StatusBar, HelpBar, HelpAction


@dataclass
class DayScheduleModel:
    """Data model for a single day's schedule.

    Attributes:
        day_name: Full day name (e.g., "Monday")
        day_short: Short day name (e.g., "Mon")
        on_time: Start time (HH:MM format)
        off_time: End time (HH:MM format)
    """

    day_name: str
    on_time: str
    off_time: str
    day_short: str = ""

    def __post_init__(self) -> None:
        """Set default short name if not provided."""
        if not self.day_short:
            self.day_short = self.day_name[:3]


@dataclass
class ScheduleModel:
    """Data model for schedule screen.

    Attributes:
        title: Schedule title
        days: List of day schedules
        selected_day: Currently selected day index
        selected_field: Currently selected field ("on_time" or "off_time")
        editing: Whether in edit mode
    """

    title: str
    days: list[DayScheduleModel] = field(default_factory=list)
    selected_day: int = 0
    selected_field: str = "on_time"
    editing: bool = False


class ScheduleScreen(Screen):
    """Weekly schedule display and editing screen.

    Shows a grid of days with on/off times. Supports navigation
    with arrow keys and time editing with 30-minute increments.
    """

    TIME_PATTERN = re.compile(r"^([01][0-9]|2[0-3]):([0-5][0-9])$")

    def __init__(self, stdscr: Any, connection: ConnectionState) -> None:
        """Initialize the schedule screen.

        Args:
            stdscr: The curses standard screen
            connection: Current connection state
        """
        super().__init__(stdscr)
        self.connection = connection
        self.model = ScheduleModel(title="Schedule", days=[])

        # Widgets
        self.status_bar = StatusBar(stdscr, self.width)
        self.help_bar = HelpBar(stdscr, self.width)
        self._update_help_bar()

    def _update_help_bar(self) -> None:
        """Update help bar based on edit mode."""
        if self.model.editing:
            self.help_bar.set_actions([
                HelpAction("Up/Down", "+/-30min"),
                HelpAction("Enter", "Done"),
                HelpAction("Esc", "Cancel"),
            ])
        else:
            self.help_bar.set_actions([
                HelpAction("Arrows", "Navigate"),
                HelpAction("Enter", "Edit"),
                HelpAction("Esc", "Back"),
                HelpAction("q", "Quit"),
            ])

    def update_model(self, model: ScheduleModel) -> None:
        """Update the schedule data model.

        Args:
            model: New schedule model
        """
        self.model = model
        self._update_help_bar()

    def validate_time(self, time_str: str) -> bool:
        """Validate a time string for 30-minute boundaries.

        Args:
            time_str: Time in HH:MM format

        Returns:
            True if valid time on 30-minute boundary
        """
        match = self.TIME_PATTERN.match(time_str)
        if not match:
            return False

        minutes = int(match.group(2))
        return minutes in (0, 30)

    def render(self) -> None:
        """Render the schedule screen."""
        self.clear()

        # Header
        self.status_bar.render(0, self.connection)

        # Separator
        self.draw_hline(1, 0, self.width)

        # Title
        self.draw_text(3, 2, self.model.title, curses.A_BOLD)
        self.draw_hline(4, 2, 60, ord("-"))

        # Column headers
        self.draw_text(6, 2, "Day")
        self.draw_text(6, 15, "On")
        self.draw_text(6, 28, "Off")

        # Schedule grid
        start_row = 8
        for i, day in enumerate(self.model.days):
            row = start_row + i
            self._render_day_row(row, i, day)

        # Edit mode indicator
        if self.model.editing:
            edit_row = self.height - 4
            self.draw_text(edit_row, 2, "EDITING - Use Up/Down to change time", curses.A_BOLD)

        # Separator
        self.draw_hline(self.height - 2, 0, self.width)

        # Help bar
        self.help_bar.render(self.height - 1)

        self.refresh()

    def _render_day_row(self, row: int, index: int, day: DayScheduleModel) -> None:
        """Render a single day row.

        Args:
            row: Row position
            index: Day index
            day: Day schedule data
        """
        is_selected = index == self.model.selected_day

        # Day name
        day_attr = curses.A_BOLD if is_selected else curses.A_NORMAL
        self.draw_text(row, 2, day.day_short, day_attr)

        # On time
        on_selected = is_selected and self.model.selected_field == "on_time"
        on_attr = curses.A_REVERSE if on_selected else curses.A_NORMAL
        self.draw_text(row, 15, day.on_time, on_attr)

        # Off time
        off_selected = is_selected and self.model.selected_field == "off_time"
        off_attr = curses.A_REVERSE if off_selected else curses.A_NORMAL
        self.draw_text(row, 28, day.off_time, off_attr)

    def handle_key(self, key: int) -> Optional[str]:
        """Handle a key press.

        Args:
            key: The curses key code

        Returns:
            Action string or None
        """
        if self.model.editing:
            return self._handle_edit_key(key)
        else:
            return self._handle_navigate_key(key)

    def _handle_navigate_key(self, key: int) -> Optional[str]:
        """Handle key in navigation mode.

        Args:
            key: The key code

        Returns:
            Action string or None
        """
        action = get_action(key)

        if action == "quit":
            return "quit"
        elif action == "back":
            return "back"
        elif action == "move_down":
            self._move_day(1)
        elif action == "move_up":
            self._move_day(-1)
        elif action == "move_right":
            self._toggle_field()
        elif action == "move_left":
            self._toggle_field()
        elif action == "select":  # Enter
            self.model.editing = True
            self._update_help_bar()

        return None

    def _handle_edit_key(self, key: int) -> Optional[str]:
        """Handle key in edit mode.

        Args:
            key: The key code

        Returns:
            Action string or None
        """
        action = get_action(key)

        if action == "back":
            # Cancel - exit edit mode
            self.model.editing = False
            self._update_help_bar()
        elif action == "select":  # Enter
            # Confirm - exit edit mode
            self.model.editing = False
            self._update_help_bar()
        elif action == "move_up":
            self._increment_time(30)
        elif action == "move_down":
            self._increment_time(-30)

        return None

    def _move_day(self, delta: int) -> None:
        """Move day selection with wrapping.

        Args:
            delta: Direction (+1 down, -1 up)
        """
        if not self.model.days:
            return

        new_day = self.model.selected_day + delta
        day_count = len(self.model.days)

        if new_day < 0:
            new_day = day_count - 1
        elif new_day >= day_count:
            new_day = 0

        self.model.selected_day = new_day

    def _toggle_field(self) -> None:
        """Toggle between on_time and off_time fields."""
        if self.model.selected_field == "on_time":
            self.model.selected_field = "off_time"
        else:
            self.model.selected_field = "on_time"

    def _increment_time(self, minutes: int) -> None:
        """Increment the selected time by given minutes.

        Args:
            minutes: Minutes to add (can be negative)
        """
        if not self.model.days:
            return

        day = self.model.days[self.model.selected_day]
        current_time = getattr(day, self.model.selected_field)

        # Parse current time
        match = self.TIME_PATTERN.match(current_time)
        if not match:
            return

        hours = int(match.group(1))
        mins = int(match.group(2))

        # Convert to total minutes
        total = hours * 60 + mins + minutes

        # Wrap at day boundaries
        if total < 0:
            total = 24 * 60 + total
        elif total >= 24 * 60:
            total = total - 24 * 60

        # Convert back to HH:MM
        new_hours = total // 60
        new_mins = total % 60
        new_time = f"{new_hours:02d}:{new_mins:02d}"

        # Update the model
        setattr(day, self.model.selected_field, new_time)

    def handle_resize(self) -> None:
        """Handle terminal resize."""
        super().handle_resize()
        self.status_bar.update_width(self.width)
        self.help_bar.update_width(self.width)
