"""Status bar widget for the TUI header.

Displays application title, connection status, and clock.
"""

import curses
from datetime import datetime
from typing import Any

from buderus_wps_cli.tui.state import ConnectionState


class StatusBar:
    """Header status bar widget.

    Displays:
    - Application title (left)
    - Connection status indicator (right)
    - Current time (far right)
    """

    TITLE = "BUDERUS WPS HEAT PUMP"

    # Status display strings
    STATUS_STRINGS = {
        ConnectionState.CONNECTING: "[Connecting...]",
        ConnectionState.CONNECTED: "[Connected]",
        ConnectionState.DISCONNECTED: "[Disconnected]",
        ConnectionState.TIMEOUT: "[Timeout]",
        ConnectionState.ERROR: "[Error]",
    }

    # Status colors (if colors available)
    STATUS_COLORS = {
        ConnectionState.CONNECTING: curses.A_NORMAL,
        ConnectionState.CONNECTED: curses.A_BOLD,
        ConnectionState.DISCONNECTED: curses.A_DIM,
        ConnectionState.TIMEOUT: curses.A_BOLD,
        ConnectionState.ERROR: curses.A_BOLD,
    }

    def __init__(self, stdscr: Any, width: int) -> None:
        """Initialize the status bar.

        Args:
            stdscr: The curses standard screen
            width: Available width for the status bar
        """
        self.stdscr = stdscr
        self.width = width

    def render(self, row: int, connection: ConnectionState) -> None:
        """Render the status bar.

        Args:
            row: Row position to render at
            connection: Current connection state
        """
        try:
            # Title (left aligned, bold)
            self.stdscr.addstr(row, 0, self.TITLE, curses.A_BOLD)

            # Time (far right)
            time_str = datetime.now().strftime("%H:%M")
            time_col = self.width - len(time_str) - 1
            if time_col > 0:
                self.stdscr.addstr(row, time_col, time_str)

            # Status (before time)
            status_str = self.STATUS_STRINGS.get(connection, "[Unknown]")
            status_attr = self.STATUS_COLORS.get(connection, curses.A_NORMAL)
            status_col = time_col - len(status_str) - 2
            if status_col > len(self.TITLE):
                self.stdscr.addstr(row, status_col, status_str, status_attr)

        except curses.error:
            pass

    def update_width(self, width: int) -> None:
        """Update the available width.

        Args:
            width: New width value
        """
        self.width = width
