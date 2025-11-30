"""Unit tests for TUI keyboard handling - T006.

Tests for key mapping and action dispatch.
"""

import curses
import pytest


class TestKeyMapping:
    """Tests for keyboard key mapping."""

    def test_arrow_keys_mapped(self) -> None:
        """Arrow keys should map to navigation actions."""
        from buderus_wps_cli.tui.keyboard import KEY_ACTIONS

        assert KEY_ACTIONS.get(curses.KEY_UP) == "move_up"
        assert KEY_ACTIONS.get(curses.KEY_DOWN) == "move_down"
        assert KEY_ACTIONS.get(curses.KEY_LEFT) == "move_left"
        assert KEY_ACTIONS.get(curses.KEY_RIGHT) == "move_right"

    def test_enter_key_mapped(self) -> None:
        """Enter key should map to select action."""
        from buderus_wps_cli.tui.keyboard import KEY_ACTIONS

        # Both newline (10) and carriage return (13) should work
        assert KEY_ACTIONS.get(curses.KEY_ENTER) == "select"
        assert KEY_ACTIONS.get(10) == "select"
        assert KEY_ACTIONS.get(13) == "select"

    def test_escape_key_mapped(self) -> None:
        """Escape key should map to back action."""
        from buderus_wps_cli.tui.keyboard import KEY_ACTIONS

        assert KEY_ACTIONS.get(27) == "back"

    def test_quit_key_mapped(self) -> None:
        """Q key should map to quit action."""
        from buderus_wps_cli.tui.keyboard import KEY_ACTIONS

        assert KEY_ACTIONS.get(ord("q")) == "quit"

    def test_refresh_key_mapped(self) -> None:
        """R key should map to refresh action."""
        from buderus_wps_cli.tui.keyboard import KEY_ACTIONS

        assert KEY_ACTIONS.get(ord("r")) == "refresh"

    def test_backspace_key_mapped(self) -> None:
        """Backspace key should map to back action."""
        from buderus_wps_cli.tui.keyboard import KEY_ACTIONS

        assert KEY_ACTIONS.get(curses.KEY_BACKSPACE) == "back"
        assert KEY_ACTIONS.get(127) == "back"  # ASCII DEL


class TestActionDispatch:
    """Tests for action dispatch from key input."""

    def test_get_action_returns_mapped_action(self) -> None:
        """get_action returns the mapped action for known keys."""
        from buderus_wps_cli.tui.keyboard import get_action

        assert get_action(curses.KEY_UP) == "move_up"
        assert get_action(ord("q")) == "quit"
        assert get_action(27) == "back"

    def test_get_action_returns_none_for_unknown(self) -> None:
        """get_action returns None for unmapped keys."""
        from buderus_wps_cli.tui.keyboard import get_action

        assert get_action(999) is None
        assert get_action(ord("z")) is None

    def test_get_action_returns_char_for_printable(self) -> None:
        """get_action returns 'char' action for printable chars during edit."""
        from buderus_wps_cli.tui.keyboard import get_action

        # Digits for numeric input
        assert get_action(ord("0"), editing=True) == "char"
        assert get_action(ord("5"), editing=True) == "char"
        assert get_action(ord("9"), editing=True) == "char"

        # But not for special chars when not editing
        assert get_action(ord("5"), editing=False) is None


class TestKeypadMode:
    """Tests for keypad mode helper."""

    def test_setup_keypad_mode(self) -> None:
        """setup_keypad should configure stdscr for keypad input."""
        from buderus_wps_cli.tui.keyboard import setup_keypad
        from unittest.mock import MagicMock

        mock_stdscr = MagicMock()
        setup_keypad(mock_stdscr)

        mock_stdscr.keypad.assert_called_once_with(True)
