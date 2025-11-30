"""Menu screen for hierarchical navigation.

Displays menu items with arrow key navigation and breadcrumb path.
"""

import curses
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from buderus_wps_cli.tui.screens.base import Screen
from buderus_wps_cli.tui.state import ConnectionState
from buderus_wps_cli.tui.keyboard import get_action
from buderus_wps_cli.tui.widgets import StatusBar, HelpBar, HelpAction, Breadcrumb


@dataclass
class MenuItemModel:
    """Data model for a single menu item.

    Attributes:
        id: Unique identifier for the item
        label: Display label
        item_type: Type of item (submenu, parameter, action)
        value: Current value for parameter items
        read_only: Whether item is read-only
    """

    id: str
    label: str
    item_type: str  # "submenu", "parameter", "action"
    value: Optional[str] = None
    read_only: bool = False


@dataclass
class MenuModel:
    """Data model for menu display.

    Attributes:
        title: Menu title
        items: List of menu items
        selected_index: Currently selected item index
    """

    title: str
    items: list[MenuItemModel] = field(default_factory=list)
    selected_index: int = 0


class MenuScreen(Screen):
    """Menu navigation screen.

    Displays a list of menu items with keyboard navigation.
    Supports hierarchical navigation with breadcrumb display.
    """

    def __init__(self, stdscr: Any, connection: ConnectionState) -> None:
        """Initialize the menu screen.

        Args:
            stdscr: The curses standard screen
            connection: Current connection state
        """
        super().__init__(stdscr)
        self.connection = connection
        self.model = MenuModel(title="Menu", items=[])
        self._path: list[str] = []

        # Widgets
        self.status_bar = StatusBar(stdscr, self.width)
        self.help_bar = HelpBar(stdscr, self.width)
        self.breadcrumb = Breadcrumb(stdscr, self.width)
        self._update_help_bar()

    def _update_help_bar(self) -> None:
        """Update help bar based on current state."""
        self.help_bar.set_actions([
            HelpAction("Enter", "Select"),
            HelpAction("Esc", "Back"),
            HelpAction("r", "Refresh"),
            HelpAction("q", "Quit"),
        ])

    def update_model(self, model: MenuModel) -> None:
        """Update the menu data model.

        Args:
            model: New menu model with items
        """
        self.model = model

    def set_path(self, path: list[str]) -> None:
        """Set the navigation path for breadcrumb display.

        Args:
            path: List of menu labels from root
        """
        self._path = path

    def render(self) -> None:
        """Render the menu screen."""
        self.clear()

        # Header with status
        self.status_bar.render(0, self.connection)

        # Separator
        self.draw_hline(1, 0, self.width)

        # Breadcrumb
        self.breadcrumb.render(2, self._path)

        # Menu title
        self.draw_text(3, 2, self.model.title, curses.A_BOLD)
        self.draw_hline(4, 2, 60, ord("-"))

        # Menu items
        start_row = 6
        visible_items = self.height - start_row - 3  # Leave room for help bar

        for i, item in enumerate(self.model.items[:visible_items]):
            row = start_row + i
            self._render_item(row, i, item)

        # Separator
        self.draw_hline(self.height - 2, 0, self.width)

        # Help bar
        self.help_bar.render(self.height - 1)

        self.refresh()

    def _render_item(self, row: int, index: int, item: MenuItemModel) -> None:
        """Render a single menu item.

        Args:
            row: Row position
            index: Item index in list
            item: The menu item to render
        """
        is_selected = index == self.model.selected_index

        # Build display text
        if item.item_type == "submenu":
            prefix = "> "
            suffix = " ..."
        elif item.item_type == "parameter":
            prefix = "  "
            suffix = ""
        else:
            prefix = "  "
            suffix = ""

        # Format item text
        label = f"{prefix}{item.label}"
        if item.value is not None:
            # Right-align value
            value_col = 40
            label = label.ljust(value_col - len(prefix))
            label += item.value
        label += suffix

        # Apply highlighting
        attr = curses.A_REVERSE if is_selected else curses.A_NORMAL

        # Draw the item
        try:
            self.stdscr.addstr(row, 2, label[:self.width - 4], attr)
        except curses.error:
            pass

    def handle_key(self, key: int) -> Optional[Union[str, tuple[str, str]]]:
        """Handle a key press.

        Args:
            key: The curses key code

        Returns:
            Action string, tuple of (action, item_id), or None
        """
        action = get_action(key)

        if action == "quit":
            return "quit"
        elif action == "back":
            return "back"
        elif action == "refresh":
            return "refresh"
        elif action == "move_down":
            self._move_selection(1)
            return None
        elif action == "move_up":
            self._move_selection(-1)
            return None
        elif action == "select":
            if self.model.items:
                selected = self.model.items[self.model.selected_index]
                return ("select", selected.id)
            return None

        return None

    def _move_selection(self, delta: int) -> None:
        """Move selection up or down with wrapping.

        Args:
            delta: Direction to move (+1 down, -1 up)
        """
        if not self.model.items:
            return

        new_index = self.model.selected_index + delta
        item_count = len(self.model.items)

        # Wrap around
        if new_index < 0:
            new_index = item_count - 1
        elif new_index >= item_count:
            new_index = 0

        self.model.selected_index = new_index

    def handle_resize(self) -> None:
        """Handle terminal resize."""
        super().handle_resize()
        self.status_bar.update_width(self.width)
        self.help_bar.update_width(self.width)
        self.breadcrumb.update_width(self.width)
