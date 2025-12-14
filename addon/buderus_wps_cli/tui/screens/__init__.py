"""Screen components for the TUI application.

Each screen handles rendering and user input for a specific view:
- Dashboard: Status overview with temperatures and operating state
- Menu: Hierarchical menu navigation
- Editor: Value editing with validation
- Schedule: Weekly schedule display and editing
"""

from buderus_wps_cli.tui.screens.base import Screen
from buderus_wps_cli.tui.screens.dashboard import DashboardScreen, DashboardModel
from buderus_wps_cli.tui.screens.menu import MenuScreen, MenuModel, MenuItemModel
from buderus_wps_cli.tui.screens.editor import EditorScreen, EditorModel, ValueType
from buderus_wps_cli.tui.screens.schedule import ScheduleScreen, ScheduleModel, DayScheduleModel

__all__ = [
    "Screen",
    "DashboardScreen",
    "DashboardModel",
    "MenuScreen",
    "MenuModel",
    "MenuItemModel",
    "EditorScreen",
    "EditorModel",
    "ValueType",
    "ScheduleScreen",
    "ScheduleModel",
    "DayScheduleModel",
]
