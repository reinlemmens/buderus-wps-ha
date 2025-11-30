"""Application state models for the TUI.

Contains enums for connection state, screen type, error type,
and dataclasses for AppState and ErrorInfo.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class ConnectionState(Enum):
    """Current connection state to the heat pump."""

    CONNECTING = auto()
    CONNECTED = auto()
    DISCONNECTED = auto()
    TIMEOUT = auto()
    ERROR = auto()


class ScreenType(Enum):
    """Types of screens in the application."""

    DASHBOARD = auto()
    MENU = auto()
    EDITOR = auto()
    SCHEDULE = auto()
    ERROR = auto()


class ErrorType(Enum):
    """Categories of errors."""

    CONNECTION = auto()
    TIMEOUT = auto()
    VALIDATION = auto()
    WRITE_FAILED = auto()
    UNKNOWN = auto()


@dataclass
class ErrorInfo:
    """Information about an error condition.

    Attributes:
        error_type: Category of the error
        message: User-friendly error message
        details: Optional technical details
        recoverable: Whether retry is possible
        timestamp: When the error occurred
    """

    error_type: ErrorType
    message: str
    recoverable: bool
    details: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class NavigationEntry:
    """Single entry in navigation history."""

    path: list[str]
    selected_index: int
    scroll_offset: int


class NavigationState:
    """Tracks position in the menu hierarchy.

    Provides methods to navigate through the menu tree:
    - push: Enter a submenu
    - pop: Go back to parent menu
    - clear: Return to root
    - is_at_root: Check if at top level
    """

    def __init__(self) -> None:
        """Initialize navigation at root level."""
        self.path: list[str] = []
        self.current_menu_id: Optional[str] = None
        self._history: list[NavigationEntry] = []

    def push(self, label: str) -> None:
        """Enter a submenu.

        Args:
            label: Display label of the submenu
        """
        self.path.append(label)

    def pop(self) -> Optional[str]:
        """Go back to parent menu.

        Returns:
            The label of the exited menu, or None if at root
        """
        if self.path:
            return self.path.pop()
        return None

    def clear(self) -> None:
        """Return to root menu."""
        self.path.clear()
        self.current_menu_id = None

    def is_at_root(self) -> bool:
        """Check if at root level.

        Returns:
            True if at root (path is empty)
        """
        return len(self.path) == 0


@dataclass
class AppState:
    """Root state container for the application.

    Attributes:
        connection: Current connection status
        screen: Active screen being displayed
        error: Current error (if any)
        last_refresh: Timestamp of last data refresh
        navigation: Menu navigation state
    """

    connection: ConnectionState
    screen: ScreenType
    error: Optional[ErrorInfo] = None
    last_refresh: datetime = field(default_factory=datetime.now)
    navigation: NavigationState = field(default_factory=NavigationState)
