"""Dashboard screen for displaying heat pump status.

Shows current temperatures, operating mode, and system status.
"""

import curses
from dataclasses import dataclass, field
from typing import Any, Optional

from buderus_wps_cli.tui.screens.base import Screen
from buderus_wps_cli.tui.state import ConnectionState
from buderus_wps_cli.tui.keyboard import get_action
from buderus_wps_cli.tui.widgets import StatusBar, HelpBar, HelpAction


@dataclass
class DashboardModel:
    """Data model for dashboard display.

    All fields are optional since values may not be available
    if not connected or during initial load.
    """

    outdoor_temp: Optional[float] = None
    supply_temp: Optional[float] = None
    return_temp: Optional[float] = None
    dhw_temp: Optional[float] = None
    room_temp: Optional[float] = None
    operating_mode: Optional[str] = None
    compressor_running: Optional[bool] = None
    aux_heater_active: Optional[bool] = None
    defrost_active: Optional[bool] = None
    error_active: bool = False


class DashboardScreen(Screen):
    """Status dashboard screen.

    Shows current temperatures, operating mode, and system status.
    This is the default screen shown on application startup.
    """

    def __init__(self, stdscr: Any, connection: ConnectionState) -> None:
        """Initialize the dashboard screen.

        Args:
            stdscr: The curses standard screen
            connection: Current connection state
        """
        super().__init__(stdscr)
        self.connection = connection
        self.model = DashboardModel()
        self.error_message: Optional[str] = None

        # Widgets
        self.status_bar = StatusBar(stdscr, self.width)
        self.help_bar = HelpBar(stdscr, self.width)
        self.help_bar.set_actions([
            HelpAction("Enter", "Menu"),
            HelpAction("r", "Refresh"),
            HelpAction("q", "Quit"),
        ])

    def update_model(self, model: DashboardModel) -> None:
        """Update the dashboard data model.

        Args:
            model: New dashboard model with updated values
        """
        self.model = model

    def update_connection(self, connection: ConnectionState) -> None:
        """Update the connection state.

        Args:
            connection: New connection state
        """
        self.connection = connection

    def set_error(self, message: str) -> None:
        """Set an error message to display.

        Args:
            message: Error message to show
        """
        self.error_message = message

    def clear_error(self) -> None:
        """Clear any error message."""
        self.error_message = None

    def render(self) -> None:
        """Render the dashboard screen."""
        self.clear()

        # Header
        self.status_bar.render(0, self.connection)

        # Separator
        self.draw_hline(1, 0, self.width)

        # Content area
        if self.connection == ConnectionState.ERROR and self.error_message:
            self._render_error()
        elif self.connection == ConnectionState.DISCONNECTED:
            self._render_disconnected()
        elif self.connection == ConnectionState.CONNECTING:
            self._render_connecting()
        else:
            self._render_status()

        # Separator
        self.draw_hline(self.height - 2, 0, self.width)

        # Help bar
        self.help_bar.render(self.height - 1)

        self.refresh()

    def _render_status(self) -> None:
        """Render the status values."""
        row = 3

        self.draw_text(row, 2, "Current Status:", curses.A_BOLD)
        row += 1
        self.draw_hline(row, 2, 60, ord("-"))
        row += 2

        # Temperature values
        self._draw_value(row, "Outdoor Temperature", self.model.outdoor_temp, "°C")
        row += 1
        self._draw_value(row, "Supply Temperature", self.model.supply_temp, "°C")
        row += 1
        if self.model.return_temp is not None:
            self._draw_value(row, "Return Temperature", self.model.return_temp, "°C")
            row += 1
        self._draw_value(row, "Hot Water Temperature", self.model.dhw_temp, "°C")
        row += 1
        if self.model.room_temp is not None:
            self._draw_value(row, "Room Temperature", self.model.room_temp, "°C")
            row += 1

        row += 1

        # Operating status
        self._draw_value(row, "Operating Mode", self.model.operating_mode, "")
        row += 1

        if self.model.compressor_running is not None:
            status = "Running" if self.model.compressor_running else "Stopped"
            self._draw_value(row, "Compressor", status, "")
            row += 1

        if self.model.aux_heater_active is not None:
            status = "Active" if self.model.aux_heater_active else "Off"
            self._draw_value(row, "Auxiliary Heater", status, "")
            row += 1

        if self.model.defrost_active:
            self.draw_text(row, 2, "DEFROST CYCLE ACTIVE", curses.A_BOLD)
            row += 1

        if self.model.error_active:
            row += 1
            self.draw_text(row, 2, "! ALARM ACTIVE - Check Alarms menu", curses.A_BOLD)

    def _draw_value(
        self, row: int, label: str, value: Any, unit: str
    ) -> None:
        """Draw a labeled value.

        Args:
            row: Row position
            label: Label text
            value: Value to display
            unit: Unit suffix
        """
        label_width = 24
        if value is None:
            display = "---"
        elif isinstance(value, float):
            display = f"{value:.1f}{unit}"
        else:
            display = f"{value}{unit}"

        text = f"{label}:{' ' * (label_width - len(label))}{display}"
        self.draw_text(row, 2, text)

    def _render_disconnected(self) -> None:
        """Render disconnected state."""
        row = 5
        self.draw_text(row, 2, "Not connected to heat pump", curses.A_BOLD)
        row += 2
        self.draw_text(row, 2, "Troubleshooting:")
        row += 1
        self.draw_text(row, 4, "- Check USB adapter is connected")
        row += 1
        self.draw_text(row, 4, "- Verify device path is correct")
        row += 1
        self.draw_text(row, 4, "- Check CAN bus connections to heat pump")
        row += 2
        self.draw_text(row, 2, "Press 'r' to retry connection")

    def _render_connecting(self) -> None:
        """Render connecting state."""
        self.draw_centered_text(10, "Connecting to heat pump...")

    def _render_error(self) -> None:
        """Render error state."""
        row = 5
        self.draw_text(row, 2, "Error:", curses.A_BOLD)
        row += 2
        if self.error_message:
            # Word wrap the error message
            words = self.error_message.split()
            line = ""
            for word in words:
                if len(line) + len(word) + 1 > self.width - 6:
                    self.draw_text(row, 4, line)
                    row += 1
                    line = word
                else:
                    line = line + " " + word if line else word
            if line:
                self.draw_text(row, 4, line)
                row += 1

        row += 2
        self.draw_text(row, 2, "Press 'r' to retry")

    def handle_key(self, key: int) -> Optional[str]:
        """Handle a key press.

        Args:
            key: The curses key code

        Returns:
            Action string or None
        """
        action = get_action(key)

        if action == "quit":
            return "quit"
        elif action == "refresh":
            return "refresh"
        elif action == "select":  # Enter key
            return "menu"

        return None

    def handle_resize(self) -> None:
        """Handle terminal resize."""
        super().handle_resize()
        self.status_bar.update_width(self.width)
        self.help_bar.update_width(self.width)
