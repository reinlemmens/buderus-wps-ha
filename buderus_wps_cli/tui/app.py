"""Main TUI application entry point.

Provides the run_tui function that starts the curses-based
terminal interface.
"""

import argparse
import curses
import sys
from typing import Any, Optional

from buderus_wps_cli.tui.keyboard import setup_keypad, get_action
from buderus_wps_cli.tui.state import AppState, ConnectionState, ScreenType


class TUIApp:
    """Main TUI application class.

    Manages the application lifecycle, screen transitions,
    and connection to the Menu API.
    """

    def __init__(self, device_path: str, read_only: bool = False) -> None:
        """Initialize the TUI application.

        Args:
            device_path: Path to USB serial device
            read_only: If True, disable all write operations
        """
        self.device_path = device_path
        self.read_only = read_only
        self.state = AppState(
            connection=ConnectionState.DISCONNECTED,
            screen=ScreenType.DASHBOARD,
        )
        self.running = False
        self.api: Any = None
        self.stdscr: Any = None

    def connect(self) -> bool:
        """Connect to the heat pump via Menu API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            from buderus_wps import USBtinAdapter, HeatPumpClient, ParameterRegistry
            from buderus_wps.menu_api import MenuAPI

            self.state.connection = ConnectionState.CONNECTING

            adapter = USBtinAdapter(self.device_path)
            adapter.connect()

            registry = ParameterRegistry()
            client = HeatPumpClient(adapter, registry)
            self.api = MenuAPI(client)

            self.state.connection = ConnectionState.CONNECTED
            return True

        except Exception as e:
            self.state.connection = ConnectionState.ERROR
            return False

    def disconnect(self) -> None:
        """Disconnect from the heat pump."""
        if self.api is not None:
            try:
                # The adapter is accessible through the client
                pass  # API cleanup if needed
            except Exception:
                pass
        self.state.connection = ConnectionState.DISCONNECTED

    def run(self, stdscr: Any) -> None:
        """Main application loop.

        Args:
            stdscr: The curses standard screen
        """
        self.stdscr = stdscr
        self.running = True

        # Configure curses
        curses.curs_set(0)  # Hide cursor
        setup_keypad(stdscr)

        # Set up non-blocking input
        stdscr.nodelay(False)
        stdscr.timeout(100)  # 100ms timeout for getch

        while self.running:
            # Render current screen
            self._render()

            # Handle input
            try:
                key = stdscr.getch()
                if key != -1:
                    self._handle_key(key)
            except KeyboardInterrupt:
                self.running = False

    def _render(self) -> None:
        """Render the current screen."""
        if self.stdscr is None:
            return

        self.stdscr.clear()

        height, width = self.stdscr.getmaxyx()

        # Check minimum size
        if height < 24 or width < 80:
            self._render_size_warning()
        else:
            self._render_dashboard()

        self.stdscr.refresh()

    def _render_size_warning(self) -> None:
        """Render terminal too small warning."""
        if self.stdscr is None:
            return
        try:
            self.stdscr.addstr(0, 0, "Terminal too small!")
            self.stdscr.addstr(1, 0, "Minimum: 80x24")
        except curses.error:
            pass

    def _render_dashboard(self) -> None:
        """Render the status dashboard."""
        if self.stdscr is None:
            return

        try:
            # Header
            title = "BUDERUS WPS HEAT PUMP"
            status = "[" + self.state.connection.name + "]"
            self.stdscr.addstr(0, 0, title, curses.A_BOLD)
            self.stdscr.addstr(0, 60, status)

            # Separator
            self.stdscr.hline(1, 0, curses.ACS_HLINE, 80)

            # Status values (placeholder until connected)
            if self.state.connection == ConnectionState.CONNECTED and self.api:
                self._render_status_values()
            else:
                self.stdscr.addstr(3, 2, "Not connected")
                self.stdscr.addstr(4, 2, f"Device: {self.device_path}")

            # Help bar
            self.stdscr.hline(22, 0, curses.ACS_HLINE, 80)
            help_text = "r Refresh  q Quit"
            self.stdscr.addstr(23, 2, help_text)

        except curses.error:
            pass

    def _render_status_values(self) -> None:
        """Render status values from the API."""
        if self.stdscr is None or self.api is None:
            return

        try:
            snapshot = self.api.status.read_all()

            self.stdscr.addstr(3, 2, f"Outdoor Temperature:    {snapshot.outdoor_temperature or '---'}°C")
            self.stdscr.addstr(4, 2, f"Supply Temperature:     {snapshot.supply_temperature or '---'}°C")
            self.stdscr.addstr(5, 2, f"Hot Water Temperature:  {snapshot.hot_water_temperature or '---'}°C")
            self.stdscr.addstr(6, 2, f"Operating Mode:         {snapshot.operating_mode.name if snapshot.operating_mode else '---'}")
            self.stdscr.addstr(7, 2, f"Compressor:             {'Running' if snapshot.compressor_running else 'Stopped'}")

        except Exception as e:
            self.stdscr.addstr(3, 2, f"Error reading status: {e}")

    def _handle_key(self, key: int) -> None:
        """Handle a key press.

        Args:
            key: The curses key code
        """
        # Handle resize
        if key == curses.KEY_RESIZE:
            # Curses handles resize automatically, just re-render
            return

        action = get_action(key)

        if action == "quit":
            self.running = False
        elif action == "refresh":
            # Will re-render on next loop
            pass


def run_tui() -> None:
    """Entry point for the buderus-tui command."""
    parser = argparse.ArgumentParser(
        description="Terminal UI for Buderus WPS heat pump control"
    )
    parser.add_argument(
        "device",
        nargs="?",
        default="/dev/ttyACM0",
        help="USB serial device path (default: /dev/ttyACM0)",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Disable all write operations",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    app = TUIApp(args.device, read_only=args.read_only)

    # Try to connect
    if not app.connect():
        print(f"Warning: Could not connect to {args.device}", file=sys.stderr)

    try:
        curses.wrapper(app.run)
    finally:
        app.disconnect()


if __name__ == "__main__":
    run_tui()
