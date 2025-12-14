"""Breadcrumb navigation widget.

Displays the current navigation path in the menu hierarchy.
"""

import curses
from typing import Any


class Breadcrumb:
    """Breadcrumb navigation display widget.

    Shows the current path like: Home > Hot Water > Temperature
    """

    SEPARATOR = " > "

    def __init__(self, stdscr: Any, width: int) -> None:
        """Initialize the breadcrumb widget.

        Args:
            stdscr: The curses standard screen
            width: Available width for the breadcrumb
        """
        self.stdscr = stdscr
        self.width = width

    def render(self, row: int, path: list[str]) -> None:
        """Render the breadcrumb path.

        Args:
            row: Row position to render at
            path: List of path segments
        """
        if not path:
            display = "Home"
        else:
            # Build path string
            segments = ["Home"] + path
            display = self.SEPARATOR.join(segments)

            # Truncate if too long
            if len(display) > self.width - 2:
                # Show ellipsis and last segments
                display = self._truncate_path(segments)

        try:
            self.stdscr.addstr(row, 0, display, curses.A_DIM)
        except curses.error:
            pass

    def _truncate_path(self, segments: list[str]) -> str:
        """Truncate path to fit width.

        Args:
            segments: Path segments

        Returns:
            Truncated path string
        """
        max_len = self.width - 5  # Leave room for "... >"

        # Always show at least the last segment
        if len(segments) == 0:
            return "Home"

        # Build from the end
        result = segments[-1]
        for seg in reversed(segments[:-1]):
            candidate = seg + self.SEPARATOR + result
            if len(candidate) > max_len:
                return "..." + self.SEPARATOR + result
            result = candidate

        return result

    def update_width(self, width: int) -> None:
        """Update the available width.

        Args:
            width: New width value
        """
        self.width = width
