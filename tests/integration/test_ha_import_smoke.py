"""Smoke tests for Home Assistant integration imports.

These tests verify that all imports used by the HA integration are available
from the buderus_wps library. This catches issues like missing exports in __init__.py
or renamed classes that would cause runtime failures.

NOTE: The HA integration imports from .buderus_wps (bundled copy), but in the
repo we test against the main buderus_wps package which is the source of truth.
The deploy script copies buderus_wps/ -> custom_components/buderus_wps/buderus_wps/

Run with: pytest tests/integration/test_ha_import_smoke.py -v
"""


class TestLibraryExports:
    """Verify all exports expected by HA integration are available."""

    def test_coordinator_imports_from_buderus_wps(self):
        """Verify coordinator.py imports work.

        From coordinator.py line 252-257:
            from .buderus_wps import (
                BroadcastMonitor,
                HeatPump,
                HeatPumpClient,
                USBtinAdapter,
            )
        """
        from buderus_wps import (
            BroadcastMonitor,
            HeatPump,
            HeatPumpClient,
            USBtinAdapter,
        )

        # Verify they're actual classes, not mocks
        assert isinstance(BroadcastMonitor, type) or callable(BroadcastMonitor)
        assert isinstance(HeatPump, type)
        assert isinstance(HeatPumpClient, type)
        assert isinstance(USBtinAdapter, type)

    def test_coordinator_imports_menu_api(self):
        """Verify coordinator.py MenuAPI import works.

        From coordinator.py line 258:
            from .buderus_wps.menu_api import MenuAPI
        """
        from buderus_wps.menu_api import MenuAPI

        assert isinstance(MenuAPI, type)

    def test_coordinator_imports_exceptions(self):
        """Verify coordinator.py exception imports work.

        From coordinator.py lines 259-267 and 164-176:
            from .buderus_wps.exceptions import (
                TimeoutError as BuderusTimeoutError,
                DeviceCommunicationError,
                DeviceDisconnectedError,
                DeviceInitializationError,
                DeviceNotFoundError,
                DevicePermissionError,
                ReadTimeoutError,
            )
        """
        from buderus_wps.exceptions import (
            DeviceCommunicationError,
            DeviceDisconnectedError,
            DeviceInitializationError,
            DeviceNotFoundError,
            DevicePermissionError,
            TimeoutError,
        )

        # Verify they're exception classes
        assert issubclass(TimeoutError, Exception)
        assert issubclass(DeviceCommunicationError, Exception)
        assert issubclass(DeviceDisconnectedError, Exception)
        assert issubclass(DeviceInitializationError, Exception)
        assert issubclass(DeviceNotFoundError, Exception)
        assert issubclass(DevicePermissionError, Exception)

    def test_coordinator_imports_config(self):
        """Verify coordinator.py config import works.

        From coordinator.py line 396:
            from .buderus_wps.config import get_default_sensor_map
        """
        from buderus_wps.config import get_default_sensor_map

        assert callable(get_default_sensor_map)

        # Verify it returns expected type
        sensor_map = get_default_sensor_map()
        assert isinstance(sensor_map, dict)

    def test_config_flow_imports(self):
        """Verify config_flow.py imports work.

        From config_flow.py lines 74-75:
            from .buderus_wps.can_adapter import USBtinAdapter
            from .buderus_wps.heat_pump import HeatPumpClient
        """
        from buderus_wps.can_adapter import USBtinAdapter
        from buderus_wps.heat_pump import HeatPumpClient

        assert isinstance(USBtinAdapter, type)
        assert isinstance(HeatPumpClient, type)

    def test_switch_imports_exceptions(self):
        """Verify switch.py exception imports work.

        From switch.py line 157-159:
            from .buderus_wps.exceptions import (
                DeviceNotFoundError,
            )
        """
        from buderus_wps.exceptions import DeviceNotFoundError

        assert issubclass(DeviceNotFoundError, Exception)


class TestLibraryInitExports:
    """Verify __init__.py exports match what integration expects."""

    def test_all_public_exports_importable(self):
        """Verify all items in __all__ are importable."""
        import buderus_wps

        if hasattr(buderus_wps, "__all__"):
            for name in buderus_wps.__all__:
                assert hasattr(
                    buderus_wps, name
                ), f"__all__ lists '{name}' but it's not importable"

    def test_heatpump_class_has_required_methods(self):
        """Verify HeatPump class has methods used by HeatPumpClient."""
        from buderus_wps import HeatPump

        hp = HeatPump()

        # Methods used by HeatPumpClient._lookup()
        assert hasattr(hp, "get_parameter"), "HeatPump missing get_parameter method"

        # Properties used elsewhere
        assert hasattr(hp, "parameters"), "HeatPump missing parameters property"
        assert hasattr(hp, "data_source"), "HeatPump missing data_source property"

    def test_parameter_class_has_required_attributes(self):
        """Verify Parameter class has attributes used by integration."""
        from buderus_wps import Parameter

        # Create a test parameter
        param = Parameter(
            idx=1,
            extid="61E1E1FC660023",
            min=0,
            max=5,
            format="int",
            read=0,
            text="TEST_PARAM",
        )

        # Attributes used by integration
        assert hasattr(param, "idx")
        assert hasattr(param, "text")
        assert hasattr(param, "min")
        assert hasattr(param, "max")
        assert hasattr(param, "format")
        assert hasattr(param, "read")


class TestNoMockLeakage:
    """Ensure these tests use real classes, not mocks from conftest."""

    def test_heatpump_actually_loads_parameters(self):
        """Verify HeatPump loads real parameter data, not mock."""
        from buderus_wps import HeatPump

        hp = HeatPump()

        # Should have loaded ~1789 parameters from fallback
        assert (
            hp.parameter_count() > 1000
        ), f"Expected 1000+ parameters, got {hp.parameter_count()} - might be using mock"

        # Should be able to look up a known parameter
        param = hp.get_parameter("ACCESS_LEVEL")
        assert param is not None
        assert param.text == "ACCESS_LEVEL"

    def test_usbtinAdapter_is_real_class(self):
        """Verify USBtinAdapter is a real class with expected interface."""
        from buderus_wps import USBtinAdapter

        # Should have connect/disconnect methods
        assert hasattr(USBtinAdapter, "connect")
        assert hasattr(USBtinAdapter, "disconnect")
        assert hasattr(USBtinAdapter, "send_frame")
