"""Base screen class for TUI screens.

Provides common functionality for all screens including
rendering helpers and resize handling.
"""

import curses
from typing import Any, Optional

# Minimum terminal size
MIN_WIDTH = 80
MIN_HEIGHT = 24


class Screen:
    """Base class for TUI screens.

    Provides common functionality for terminal rendering,
    dimension management, and input handling.

    Attributes:
        stdscr: The curses standard screen
        height: Current terminal height
        width: Current terminal width
    """

    def __init__(self, stdscr: Any) -> None:
        """Initialize the screen.

        Args:
            stdscr: The curses standard screen
        """
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()

    def render(self) -> None:
        """Render the screen content.

        Override in subclasses to implement specific rendering.
        """
        pass

    def handle_key(self, key: int) -> Optional[str]:
        """Handle a key press.

        Override in subclasses to implement specific key handling.

        Args:
            key: The curses key code

        Returns:
            Optional action result string
        """
        return None

    def handle_resize(self) -> None:
        """Handle terminal resize event.

        Updates stored dimensions from the terminal.
        """
        self.height, self.width = self.stdscr.getmaxyx()

    def clear(self) -> None:
        """Clear the screen."""
        self.stdscr.clear()

    def refresh(self) -> None:
        """Refresh the screen to show changes."""
        self.stdscr.refresh()

    def is_too_small(self) -> bool:
        """Check if terminal is below minimum size.

        Returns:
            True if terminal is too small (< 80x24)
        """
        return self.width < MIN_WIDTH or self.height < MIN_HEIGHT

    def draw_text(
        self, row: int, col: int, text: str, attr: int = 0
    ) -> None:
        """Draw text at a position.

        Text is truncated if it would exceed the terminal width.

        Args:
            row: Row position (0-based)
            col: Column position (0-based)
            text: Text to draw
            attr: Curses attribute (default: none)
        """
        # Truncate to fit within terminal width
        max_len = self.width - col
        if max_len <= 0:
            return
        truncated = text[:max_len]
        try:
            self.stdscr.addstr(row, col, truncated, attr)
        except curses.error:
            # Ignore errors from writing to bottom-right corner
            pass

    def draw_hline(self, row: int, col: int, width: int, char: int = 0) -> None:
        """Draw a horizontal line.

        Args:
            row: Row position
            col: Starting column
            width: Line width
            char: Character to use (default: ACS_HLINE or '-')
        """
        try:
            if char == 0:
                # ACS_HLINE only available after initscr, fallback to '-'
                hline_char = getattr(curses, "ACS_HLINE", ord("-"))
                self.stdscr.hline(row, col, hline_char, width)
            else:
                self.stdscr.hline(row, col, char, width)
        except (curses.error, AttributeError):
            pass

    def draw_centered_text(self, row: int, text: str, attr: int = 0) -> None:
        """Draw text centered horizontally.

        Args:
            row: Row position
            text: Text to draw
            attr: Curses attribute
        """
        col = max(0, (self.width - len(text)) // 2)
        self.draw_text(row, col, text, attr)
