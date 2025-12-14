"""Terminal User Interface for Buderus WPS heat pump control.

This module provides a curses-based interactive terminal interface
for monitoring and controlling the heat pump via the Menu API.
"""

from buderus_wps_cli.tui.app import run_tui

__all__ = ["run_tui"]
