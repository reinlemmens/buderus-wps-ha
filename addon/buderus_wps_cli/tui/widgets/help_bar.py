"""Help bar widget for displaying keyboard shortcuts.

Shows available actions at the bottom of the screen.
"""

import curses
from dataclasses import dataclass
from typing import Any


@dataclass
class HelpAction:
    """A help action to display."""

    key: str
    description: str


class HelpBar:
    """Bottom help bar widget.

    Displays available keyboard shortcuts for the current screen.
    """

    # Default actions shown on most screens
    DEFAULT_ACTIONS = [
        HelpAction("↑↓", "Navigate"),
        HelpAction("Enter", "Select"),
        HelpAction("Esc", "Back"),
        HelpAction("r", "Refresh"),
        HelpAction("q", "Quit"),
    ]

    def __init__(self, stdscr: Any, width: int) -> None:
        """Initialize the help bar.

        Args:
            stdscr: The curses standard screen
            width: Available width for the help bar
        """
        self.stdscr = stdscr
        self.width = width
        self.actions: list[HelpAction] = list(self.DEFAULT_ACTIONS)

    def render(self, row: int) -> None:
        """Render the help bar.

        Args:
            row: Row position to render at
        """
        # Build help string
        parts = []
        for action in self.actions:
            parts.append(f"{action.key} {action.description}")

        help_text = "  ".join(parts)

        # Truncate if needed
        if len(help_text) > self.width - 2:
            help_text = help_text[: self.width - 5] + "..."

        try:
            self.stdscr.addstr(row, 2, help_text, curses.A_DIM)
        except curses.error:
            pass

    def set_actions(self, actions: list[HelpAction]) -> None:
        """Set the actions to display.

        Args:
            actions: List of HelpAction to show
        """
        self.actions = actions

    def reset_actions(self) -> None:
        """Reset to default actions."""
        self.actions = list(self.DEFAULT_ACTIONS)

    def update_width(self, width: int) -> None:
        """Update the available width.

        Args:
            width: New width value
        """
        self.width = width
