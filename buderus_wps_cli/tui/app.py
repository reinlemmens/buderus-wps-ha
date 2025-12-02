"""Main TUI application entry point.

Provides the run_tui function that starts the curses-based
terminal interface.
"""

import argparse
import curses
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from buderus_wps.config import get_default_sensor_map
from buderus_wps_cli.tui.keyboard import setup_keypad, get_action
from buderus_wps_cli.tui.state import AppState, ConnectionState, ScreenType

from typing import List


@dataclass
class MenuItem:
    """A menu item for display."""
    name: str
    item_type: str  # "submenu" or "parameter"
    value: Optional[str] = None
    children: List["MenuItem"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass
class BroadcastTemperatures:
    """Temperature readings from CAN broadcast monitoring.

    These are actual sensor values captured from broadcast traffic,
    which are more reliable than RTR request/response readings.
    """
    outdoor: Optional[float] = None      # GT2 - Outdoor
    supply: Optional[float] = None       # GT8 - Supply line
    return_temp: Optional[float] = None  # GT9 - Return line
    dhw: Optional[float] = None          # GT3 - DHW tank
    brine_in: Optional[float] = None     # GT1 - Brine inlet
    timestamp: float = 0.0


# Known broadcast temperature mappings
# Format: (base, idx) -> sensor name (attribute name)
# Mappings are loaded from shared config module (buderus_wps.config)
# These are derived from actual CAN bus broadcast observations (2024-12-02)
TEMP_BROADCAST_MAP = get_default_sensor_map()


class TUIApp:
    """Main TUI application class.

    Manages the application lifecycle, screen transitions,
    and connection to the Menu API. Uses broadcast monitoring
    for reliable temperature readings.
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
        self.adapter: Any = None
        self.monitor: Any = None
        self.stdscr: Any = None
        self.temps = BroadcastTemperatures()
        self._last_refresh = 0.0
        # Menu navigation state
        self._in_menu = False
        self._menu_items: List[MenuItem] = []
        self._menu_selected = 0
        self._menu_path: List[str] = []  # Breadcrumb path

    def connect(self) -> bool:
        """Connect to the heat pump via Menu API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            from buderus_wps import USBtinAdapter, HeatPumpClient, ParameterRegistry, BroadcastMonitor
            from buderus_wps.menu_api import MenuAPI

            self.state.connection = ConnectionState.CONNECTING

            self.adapter = USBtinAdapter(self.device_path)
            self.adapter.connect()

            registry = ParameterRegistry()
            client = HeatPumpClient(self.adapter, registry)
            self.api = MenuAPI(client)

            # Create broadcast monitor for reliable temperature readings
            self.monitor = BroadcastMonitor(self.adapter)

            self.state.connection = ConnectionState.CONNECTED
            return True

        except Exception as e:
            self.state.connection = ConnectionState.ERROR
            return False

    def disconnect(self) -> None:
        """Disconnect from the heat pump."""
        if self.adapter is not None:
            try:
                self.adapter.disconnect()
            except Exception:
                pass
        self.api = None
        self.monitor = None
        self.adapter = None
        self.state.connection = ConnectionState.DISCONNECTED

    def refresh_temperatures(self, duration: float = 10.0) -> None:
        """Refresh temperature readings from CAN broadcast traffic.

        Args:
            duration: How long to monitor for broadcasts (seconds).
                      Needs ~10s to capture all temperature broadcasts.
        """
        if self.monitor is None:
            return

        try:
            # Collect all broadcast readings (some temps broadcast infrequently)
            cache = self.monitor.collect(duration=duration)

            # Update temperatures from broadcast data
            for can_id, reading in cache.readings.items():
                key = (reading.base, reading.idx)
                if key in TEMP_BROADCAST_MAP:
                    attr = TEMP_BROADCAST_MAP[key]
                    if reading.temperature is not None:
                        setattr(self.temps, attr, reading.temperature)

            self.temps.timestamp = time.time()
            self._last_refresh = time.time()

        except Exception:
            pass  # Keep existing values on error

    def _load_menu_items(self) -> None:
        """Load menu items from the API's menu navigator."""
        if not self.api:
            return

        try:
            # Get current menu items from API
            items = self.api.menu.items()
            self._menu_items = []
            for item in items:
                menu_item = MenuItem(
                    name=item.name,
                    item_type="submenu" if item.children else "parameter",
                    value=None,
                    children=[],
                )
                # Try to read value for parameter items
                if item.parameter and not item.children:
                    try:
                        self.api.menu.navigate("/".join(self._menu_path + [item.name]))
                        val = self.api.menu.get_value()
                        menu_item.value = str(val) if val is not None else "---"
                        self.api.menu.navigate("/".join(self._menu_path) if self._menu_path else "")
                    except Exception:
                        menu_item.value = "---"
                self._menu_items.append(menu_item)
            self._menu_selected = min(self._menu_selected, max(0, len(self._menu_items) - 1))
        except Exception:
            self._menu_items = []

    def _enter_menu(self) -> None:
        """Enter menu mode."""
        self._in_menu = True
        self._menu_path = []
        self._menu_selected = 0
        if self.api:
            self.api.menu.navigate("")  # Go to root
        self._load_menu_items()

    def _exit_menu(self) -> None:
        """Exit menu mode back to dashboard."""
        self._in_menu = False
        self._menu_path = []
        self._menu_selected = 0

    def _menu_back(self) -> None:
        """Go back one level in menu."""
        if not self._menu_path:
            # At root, exit to dashboard
            self._exit_menu()
            return

        self._menu_path.pop()
        self._menu_selected = 0
        if self.api:
            path = "/".join(self._menu_path) if self._menu_path else ""
            self.api.menu.navigate(path)
        self._load_menu_items()

    def _menu_select(self) -> None:
        """Select current menu item."""
        if not self._menu_items:
            return

        item = self._menu_items[self._menu_selected]
        if item.item_type == "submenu":
            # Enter submenu
            self._menu_path.append(item.name)
            self._menu_selected = 0
            if self.api:
                self.api.menu.navigate("/".join(self._menu_path))
            self._load_menu_items()
        # For parameter items, we'd open an editor (not implemented yet)

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

        # Initial temperature refresh
        if self.state.connection == ConnectionState.CONNECTED:
            self._show_loading("Loading temperatures...")
            self.refresh_temperatures(duration=3.0)

        while self.running:
            # Auto-refresh temperatures every 30 seconds
            if (self.state.connection == ConnectionState.CONNECTED
                    and time.time() - self._last_refresh > 30.0):
                self.refresh_temperatures(duration=2.0)

            # Render current screen
            self._render()

            # Handle input
            try:
                key = stdscr.getch()
                if key != -1:
                    self._handle_key(key)
            except KeyboardInterrupt:
                self.running = False

    def _show_loading(self, message: str) -> None:
        """Show a loading message."""
        if self.stdscr is None:
            return
        try:
            self.stdscr.clear()
            self.stdscr.addstr(10, 30, message)
            self.stdscr.refresh()
        except curses.error:
            pass

    def _render(self) -> None:
        """Render the current screen."""
        if self.stdscr is None:
            return

        self.stdscr.clear()

        height, width = self.stdscr.getmaxyx()

        # Check minimum size
        if height < 24 or width < 80:
            self._render_size_warning()
        elif self._in_menu:
            self._render_menu()
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
            help_text = "Enter Menu  r Refresh  q Quit"
            self.stdscr.addstr(23, 2, help_text)

        except curses.error:
            pass

    def _render_menu(self) -> None:
        """Render the menu screen."""
        if self.stdscr is None:
            return

        try:
            # Header
            title = "BUDERUS WPS HEAT PUMP"
            status = "[MENU]"
            self.stdscr.addstr(0, 0, title, curses.A_BOLD)
            self.stdscr.addstr(0, 60, status)

            # Separator
            self.stdscr.hline(1, 0, curses.ACS_HLINE, 80)

            # Breadcrumb
            if self._menu_path:
                breadcrumb = " > ".join(["Root"] + self._menu_path)
            else:
                breadcrumb = "Root"
            self.stdscr.addstr(2, 2, breadcrumb, curses.A_DIM)

            # Menu title
            menu_title = self._menu_path[-1] if self._menu_path else "Main Menu"
            self.stdscr.addstr(4, 2, menu_title, curses.A_BOLD)
            self.stdscr.hline(5, 2, ord("-"), 60)

            # Menu items
            start_row = 7
            for i, item in enumerate(self._menu_items):
                row = start_row + i
                if row >= 21:  # Leave room for help bar
                    break

                # Format item
                if item.item_type == "submenu":
                    prefix = "> "
                    suffix = " ..."
                else:
                    prefix = "  "
                    suffix = ""

                label = f"{prefix}{item.name}{suffix}"
                if item.value is not None:
                    label = label.ljust(40) + item.value

                # Highlight selected item
                attr = curses.A_REVERSE if i == self._menu_selected else curses.A_NORMAL
                self.stdscr.addstr(row, 2, label[:76], attr)

            # Help bar
            self.stdscr.hline(22, 0, curses.ACS_HLINE, 80)
            help_text = "↑↓ Navigate  Enter Select  Esc Back  q Quit"
            self.stdscr.addstr(23, 2, help_text)

        except curses.error:
            pass

    def _render_status_values(self) -> None:
        """Render status values from broadcast monitoring."""
        if self.stdscr is None:
            return

        def fmt_temp(val: Optional[float]) -> str:
            """Format temperature value or show ---."""
            return f"{val:.1f}" if val is not None else "---"

        try:
            # Temperature readings from broadcast monitoring
            self.stdscr.addstr(3, 2, f"Outdoor Temperature:    {fmt_temp(self.temps.outdoor)}°C")
            self.stdscr.addstr(4, 2, f"Supply Temperature:     {fmt_temp(self.temps.supply)}°C")
            self.stdscr.addstr(5, 2, f"Return Temperature:     {fmt_temp(self.temps.return_temp)}°C")
            self.stdscr.addstr(6, 2, f"Hot Water Temperature:  {fmt_temp(self.temps.dhw)}°C")

            # Operating mode from API (if available)
            mode_str = "---"
            compressor_str = "---"
            compressor_mode = "---"
            compressor_freq = 0
            if self.api:
                try:
                    mode = self.api.status.operating_mode
                    mode_str = mode.name if mode else "---"
                except Exception:
                    pass
                try:
                    running = self.api.status.compressor_running
                    compressor_freq = self.api.status.compressor_frequency
                    compressor_mode = self.api.status.compressor_mode
                    if running:
                        compressor_str = f"Running ({compressor_freq} Hz)"
                    else:
                        compressor_str = "Stopped"
                except Exception:
                    pass

            self.stdscr.addstr(8, 2, f"Operating Mode:         {mode_str}")
            self.stdscr.addstr(9, 2, f"Compressor:             {compressor_str}")
            self.stdscr.addstr(10, 2, f"Compressor Mode:        {compressor_mode}")

            # Show last refresh time
            if self.temps.timestamp > 0:
                age = int(time.time() - self.temps.timestamp)
                self.stdscr.addstr(12, 2, f"Last update: {age}s ago", curses.A_DIM)

        except Exception as e:
            self.stdscr.addstr(3, 2, f"Error: {e}")

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
            if self._in_menu:
                self._exit_menu()
            else:
                self.running = False
        elif action == "back":
            if self._in_menu:
                self._menu_back()
        elif action == "select":
            if self._in_menu:
                self._menu_select()
            elif self.state.connection == ConnectionState.CONNECTED:
                # Enter menu from dashboard
                self._enter_menu()
        elif action == "move_up":
            if self._in_menu and self._menu_items:
                self._menu_selected = (self._menu_selected - 1) % len(self._menu_items)
        elif action == "move_down":
            if self._in_menu and self._menu_items:
                self._menu_selected = (self._menu_selected + 1) % len(self._menu_items)
        elif action == "refresh":
            # Manual refresh - show loading and collect new temps
            if self.state.connection == ConnectionState.CONNECTED:
                self._show_loading("Refreshing...")
                if self._in_menu:
                    self._load_menu_items()
                else:
                    self.refresh_temperatures(duration=3.0)


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
