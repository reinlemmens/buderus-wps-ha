"""Reusable UI widgets for the TUI application.

Widgets are small, self-contained UI components that can be
composed into larger screens:
- StatusBar: Header with title, connection status, and clock
- Breadcrumb: Navigation path display
- HelpBar: Bottom help text with available actions
- InputField: Text input for value editing
"""

from buderus_wps_cli.tui.widgets.status_bar import StatusBar
from buderus_wps_cli.tui.widgets.breadcrumb import Breadcrumb
from buderus_wps_cli.tui.widgets.help_bar import HelpBar, HelpAction

__all__ = ["StatusBar", "Breadcrumb", "HelpBar", "HelpAction"]
