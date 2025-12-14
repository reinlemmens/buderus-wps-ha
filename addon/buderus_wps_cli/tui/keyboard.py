"""Keyboard input handling for the TUI.

Maps curses key codes to action names and provides helpers
for keypad mode setup.
"""

import curses
from typing import Any, Optional

# Key to action mapping
KEY_ACTIONS: dict[int, str] = {
    # Arrow keys
    curses.KEY_UP: "move_up",
    curses.KEY_DOWN: "move_down",
    curses.KEY_LEFT: "move_left",
    curses.KEY_RIGHT: "move_right",
    # Enter/select
    curses.KEY_ENTER: "select",
    10: "select",  # Newline
    13: "select",  # Carriage return
    # Back/escape
    27: "back",  # Escape
    curses.KEY_BACKSPACE: "back",
    127: "back",  # ASCII DEL
    # Actions
    ord("q"): "quit",
    ord("Q"): "quit",
    ord("r"): "refresh",
    ord("R"): "refresh",
}


def get_action(key: int, editing: bool = False) -> Optional[str]:
    """Get the action name for a key code.

    Args:
        key: The curses key code
        editing: Whether currently in edit mode

    Returns:
        Action name string, or None if key is not mapped
    """
    # Check mapped actions first
    if key in KEY_ACTIONS:
        return KEY_ACTIONS[key]

    # In edit mode, printable chars are 'char' action
    if editing:
        if 32 <= key <= 126:  # Printable ASCII
            return "char"

    return None


def setup_keypad(stdscr: Any) -> None:
    """Configure the terminal for keypad input.

    Enables keypad mode so that arrow keys, function keys,
    and other special keys are properly recognized.

    Args:
        stdscr: The curses standard screen
    """
    stdscr.keypad(True)
