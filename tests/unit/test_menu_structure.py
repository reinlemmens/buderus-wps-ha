"""
Unit tests for menu structure - T029.

Tests the menu hierarchy definition and MenuItem dataclass.
"""

from buderus_wps.menu_structure import (
    DHW_PARAMS,
    MENU_ROOT,
    STATUS_PARAMS,
    MenuItem,
    build_menu_tree,
    get_circuit_param,
)


class TestMenuItem:
    """Test MenuItem dataclass."""

    def test_create_basic_menu_item(self):
        """Create a simple menu item."""
        item = MenuItem(name="Test", description="Test item")
        assert item.name == "Test"
        assert item.description == "Test item"
        assert item.parameter is None
        assert item.readable is True
        assert item.writable is False
        assert item.children == []

    def test_create_writable_menu_item(self):
        """Create a writable menu item with value range."""
        item = MenuItem(
            name="Temperature",
            description="DHW setpoint",
            parameter="DHW_SETPOINT",
            writable=True,
            value_range=(20, 65),
        )
        assert item.writable is True
        assert item.value_range == (20, 65)
        assert item.parameter == "DHW_SETPOINT"

    def test_create_menu_item_with_children(self):
        """Create a menu item with sub-items."""
        child1 = MenuItem(name="Child 1")
        child2 = MenuItem(name="Child 2")
        parent = MenuItem(name="Parent", children=[child1, child2])

        assert len(parent.children) == 2
        assert parent.children[0].name == "Child 1"


class TestMenuTree:
    """Test the built menu hierarchy."""

    def test_root_exists(self):
        """Menu root is defined."""
        assert MENU_ROOT is not None
        assert MENU_ROOT.name == "Root"

    def test_root_has_children(self):
        """Root has top-level menu categories."""
        assert len(MENU_ROOT.children) > 0
        names = [c.name for c in MENU_ROOT.children]
        assert "Status" in names
        assert "Hot Water" in names

    def test_status_menu_has_temperatures(self):
        """Status menu contains temperature items."""
        status = next(c for c in MENU_ROOT.children if c.name == "Status")
        names = [c.name for c in status.children]
        assert "Outdoor Temperature" in names
        assert "Supply Temperature" in names
        assert "Hot Water Temperature" in names

    def test_hot_water_menu_has_settings(self):
        """Hot Water menu contains settings."""
        hot_water = next(c for c in MENU_ROOT.children if c.name == "Hot Water")
        names = [c.name for c in hot_water.children]
        assert "Temperature" in names
        assert "Program Mode" in names

    def test_hot_water_temperature_is_writable(self):
        """Hot Water Temperature is writable with range."""
        hot_water = next(c for c in MENU_ROOT.children if c.name == "Hot Water")
        temp_item = next(c for c in hot_water.children if c.name == "Temperature")
        assert temp_item.writable is True
        assert temp_item.value_range == (20, 65)

    def test_build_menu_tree_returns_same_structure(self):
        """build_menu_tree() returns consistent structure."""
        tree = build_menu_tree()
        assert tree.name == "Root"
        assert len(tree.children) == len(MENU_ROOT.children)


class TestParameterMappings:
    """Test parameter name mappings."""

    def test_status_params_defined(self):
        """Status parameters are mapped."""
        assert "outdoor_temp" in STATUS_PARAMS
        assert "supply_temp" in STATUS_PARAMS
        assert "operating_mode" in STATUS_PARAMS

    def test_dhw_params_defined(self):
        """DHW parameters are mapped."""
        assert "setpoint" in DHW_PARAMS
        assert "program_mode" in DHW_PARAMS
        assert "schedule_p1_monday" in DHW_PARAMS

    def test_dhw_schedule_params_are_indices(self):
        """DHW schedule params are numeric indices for sw2."""
        assert isinstance(DHW_PARAMS["schedule_p1_monday"], int)
        assert DHW_PARAMS["schedule_p1_monday"] == 460

    def test_get_circuit_param(self):
        """get_circuit_param substitutes circuit number."""
        template = "ROOM_TEMP_C{n}"
        assert get_circuit_param(template, 1) == "ROOM_TEMP_C1"
        assert get_circuit_param(template, 2) == "ROOM_TEMP_C2"
        assert get_circuit_param(template, 4) == "ROOM_TEMP_C4"


class TestMenuCategories:
    """Test all required menu categories exist."""

    def test_has_programs_menu(self):
        """Programs menu exists for schedules."""
        names = [c.name for c in MENU_ROOT.children]
        assert "Programs" in names

    def test_has_vacation_menu(self):
        """Vacation menu exists."""
        names = [c.name for c in MENU_ROOT.children]
        assert "Vacation" in names

    def test_has_energy_menu(self):
        """Energy menu exists."""
        names = [c.name for c in MENU_ROOT.children]
        assert "Energy" in names

    def test_has_alarms_menu(self):
        """Alarms menu exists."""
        names = [c.name for c in MENU_ROOT.children]
        assert "Alarms" in names
