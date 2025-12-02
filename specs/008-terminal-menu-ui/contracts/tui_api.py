"""TUI Internal API Contract.

This module defines the interfaces between TUI components:
- Screen protocol for rendering and event handling
- Data models for screen state
- Key action mappings
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Protocol


# =============================================================================
# Enumerations
# =============================================================================

class ScreenType(Enum):
    """Available screen types."""
    DASHBOARD = auto()
    MENU = auto()
    EDITOR = auto()
    SCHEDULE = auto()
    ERROR = auto()


class ConnectionState(Enum):
    """Connection states."""
    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    TIMEOUT = auto()
    ERROR = auto()


class KeyAction(Enum):
    """Mapped keyboard actions."""
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    SELECT = auto()
    BACK = auto()
    REFRESH = auto()
    QUIT = auto()
    CHAR = auto()  # Printable character in edit mode


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class CircuitTempModel:
    """Temperature data for a single heating circuit."""
    circuit_number: int
    circuit_name: str
    room_temp: Optional[float] = None
    setpoint: Optional[float] = None
    program_mode: Optional[str] = None


@dataclass
class DashboardModel:
    """Status dashboard display data."""
    outdoor_temp: Optional[float] = None
    supply_temp: Optional[float] = None
    return_temp: Optional[float] = None
    dhw_temp: Optional[float] = None
    brine_in_temp: Optional[float] = None
    circuit_temps: list[CircuitTempModel] = field(default_factory=list)
    operating_mode: Optional[str] = None
    compressor_running: bool = False
    compressor_frequency: int = 0
    compressor_mode: str = "Idle"
    error_active: bool = False


@dataclass
class MenuItemModel:
    """Single menu item display data."""
    id: str
    label: str
    item_type: str  # "submenu", "parameter", "action"
    value: Optional[str] = None
    read_only: bool = False


@dataclass
class MenuModel:
    """Menu screen display data."""
    title: str
    items: list[MenuItemModel] = field(default_factory=list)
    selected_index: int = 0


@dataclass
class EditorModel:
    """Parameter editor display data."""
    parameter_name: str
    current_value: str
    edit_buffer: str
    cursor_position: int = 0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    unit: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ScheduleDay:
    """Schedule for a single day."""
    day_name: str
    start_time: Optional[str] = None  # HH:MM format
    end_time: Optional[str] = None


@dataclass
class ScheduleModel:
    """Schedule editor display data."""
    program_name: str
    days: list[ScheduleDay] = field(default_factory=list)
    selected_day: int = 0
    editing: bool = False


# =============================================================================
# Screen Protocol
# =============================================================================

class Screen(Protocol):
    """Protocol for all TUI screens."""

    def render(self) -> None:
        """Render the screen to the terminal."""
        ...

    def handle_key(self, key: int) -> Optional[str]:
        """Handle a key press.

        Args:
            key: curses key code

        Returns:
            Action string (e.g., "quit", "back") or None to continue
        """
        ...

    def handle_resize(self) -> None:
        """Handle terminal resize event."""
        ...


# =============================================================================
# Widget Protocol
# =============================================================================

class Widget(Protocol):
    """Protocol for reusable UI widgets."""

    def render(self, row: int) -> None:
        """Render the widget at the given row.

        Args:
            row: Starting row for rendering
        """
        ...

    def update_width(self, width: int) -> None:
        """Update widget width after terminal resize.

        Args:
            width: New terminal width
        """
        ...


# =============================================================================
# Application Protocol
# =============================================================================

class TUIApplication(Protocol):
    """Protocol for the main TUI application."""

    def connect(self) -> bool:
        """Connect to heat pump.

        Returns:
            True if connected successfully
        """
        ...

    def disconnect(self) -> None:
        """Disconnect from heat pump."""
        ...

    def refresh_temperatures(self, duration: float = 3.0) -> None:
        """Refresh temperature readings via broadcast monitoring.

        Args:
            duration: Collection window in seconds
        """
        ...

    def run(self, stdscr: Any) -> None:
        """Main application loop.

        Args:
            stdscr: curses standard screen
        """
        ...


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class CircuitConfig:
    """Configuration for a single heating circuit."""
    number: int
    name: str
    room_temp_sensor: str = ""
    setpoint_param: str = ""
    program_param: str = ""


@dataclass
class TUIConfig:
    """TUI application configuration."""
    device_path: str
    circuits: list[CircuitConfig] = field(default_factory=list)
    read_only: bool = False
    verbose: bool = False
