"""Pytest configuration and fixtures for Home Assistant integration tests.

This module sets up comprehensive mocks for Home Assistant modules to allow
testing the integration without the full HA runtime environment.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest


def setup_ha_mocks():
    """Set up all required Home Assistant module mocks.

    This must be called before any imports from custom_components.
    """
    # Core HA modules
    sys.modules["homeassistant"] = MagicMock()
    sys.modules["homeassistant.core"] = MagicMock()
    sys.modules["homeassistant.config_entries"] = MagicMock()

    # Exceptions module with real exception classes
    class HomeAssistantError(Exception):
        """Base Home Assistant exception."""

        pass

    exceptions_mock = MagicMock()
    exceptions_mock.HomeAssistantError = HomeAssistantError
    sys.modules["homeassistant.exceptions"] = exceptions_mock

    # Constants module with actual values we need
    const_mock = MagicMock()
    const_mock.UnitOfTemperature = MagicMock()
    const_mock.UnitOfTemperature.CELSIUS = "°C"
    sys.modules["homeassistant.const"] = const_mock

    # Helpers modules
    sys.modules["homeassistant.helpers"] = MagicMock()
    sys.modules["homeassistant.helpers.discovery"] = MagicMock()
    sys.modules["homeassistant.helpers.entity"] = MagicMock()
    sys.modules["homeassistant.helpers.entity_platform"] = MagicMock()
    sys.modules["homeassistant.helpers.config_validation"] = MagicMock()
    sys.modules["homeassistant.helpers.device_registry"] = MagicMock()

    # UpdateCoordinator mock - needs to support generic subscripting
    class MockDataUpdateCoordinator:
        """Mock DataUpdateCoordinator that supports generic subscripting."""

        def __init__(self, *args, **kwargs):
            pass

        def __class_getitem__(cls, item):
            return cls

    class MockCoordinatorEntity:
        """Mock CoordinatorEntity that supports generic subscripting."""

        coordinator = None

        def __init__(self, coordinator, *args, **kwargs):
            self.coordinator = coordinator

        def __class_getitem__(cls, item):
            return cls

    coordinator_mock = MagicMock()
    coordinator_mock.DataUpdateCoordinator = MockDataUpdateCoordinator
    coordinator_mock.CoordinatorEntity = MockCoordinatorEntity
    sys.modules["homeassistant.helpers.update_coordinator"] = coordinator_mock

    # Sensor component with class attributes
    sensor_mock = MagicMock()
    sensor_mock.SensorDeviceClass = MagicMock()
    sensor_mock.SensorDeviceClass.TEMPERATURE = "temperature"
    sensor_mock.SensorStateClass = MagicMock()
    sensor_mock.SensorStateClass.MEASUREMENT = "measurement"

    # Create a base SensorEntity class for inheritance
    class MockSensorEntity:
        _attr_device_class = None
        _attr_native_unit_of_measurement = None
        _attr_state_class = None
        _attr_name = None

        @property
        def device_class(self):
            return self._attr_device_class

        @property
        def native_unit_of_measurement(self):
            return self._attr_native_unit_of_measurement

        @property
        def state_class(self):
            return self._attr_state_class

        @property
        def name(self):
            return self._attr_name

    sensor_mock.SensorEntity = MockSensorEntity
    sys.modules["homeassistant.components.sensor"] = sensor_mock

    # Binary sensor component
    binary_sensor_mock = MagicMock()
    binary_sensor_mock.BinarySensorDeviceClass = MagicMock()
    binary_sensor_mock.BinarySensorDeviceClass.RUNNING = "running"
    binary_sensor_mock.BinarySensorDeviceClass.POWER = "power"

    class MockBinarySensorEntity:
        _attr_device_class = None
        _attr_is_on = None
        _attr_name = None

        @property
        def device_class(self):
            return self._attr_device_class

        @property
        def is_on(self):
            return self._attr_is_on

        @property
        def name(self):
            return self._attr_name

    binary_sensor_mock.BinarySensorEntity = MockBinarySensorEntity
    sys.modules["homeassistant.components.binary_sensor"] = binary_sensor_mock

    # Switch component
    switch_mock = MagicMock()

    class MockSwitchEntity:
        _attr_name = None
        _attr_is_on = None

        @property
        def name(self):
            return self._attr_name

        @property
        def is_on(self):
            return self._attr_is_on

    switch_mock.SwitchEntity = MockSwitchEntity
    sys.modules["homeassistant.components.switch"] = switch_mock

    # Number component
    number_mock = MagicMock()
    number_mock.NumberMode = MagicMock()
    number_mock.NumberMode.SLIDER = "slider"
    number_mock.NumberMode.BOX = "box"

    class MockNumberEntity:
        _attr_name = None
        _attr_native_value = None
        _attr_native_min_value = None
        _attr_native_max_value = None
        _attr_native_step = None
        _attr_mode = None

        @property
        def name(self):
            return self._attr_name

        @property
        def native_value(self):
            return self._attr_native_value

    number_mock.NumberEntity = MockNumberEntity
    sys.modules["homeassistant.components.number"] = number_mock

    # Voluptuous mock
    sys.modules["voluptuous"] = MagicMock()


# Set up mocks at module import time
setup_ha_mocks()


# Mock data class matching coordinator.BuderusData
@dataclass
class MockBuderusData:
    """Mock data class matching coordinator.BuderusData."""

    temperatures: dict[str, Optional[float]]
    compressor_running: bool
    energy_blocked: bool
    dhw_extra_duration: int
    heating_season_mode: Optional[int] = None
    dhw_program_mode: Optional[int] = None
    heating_curve_offset: Optional[float] = None
    dhw_stop_temp: Optional[float] = None
    dhw_setpoint: Optional[float] = None


@pytest.fixture
def mock_temperatures() -> dict[str, float]:
    """Provide sample temperature data."""
    return {
        "outdoor": 5.5,
        "supply": 35.0,
        "return_temp": 30.0,
        "dhw": 48.5,
        "brine_in": 8.0,
    }


@pytest.fixture
def mock_buderus_data(mock_temperatures: dict[str, float]) -> MockBuderusData:
    """Provide mock BuderusData instance."""
    return MockBuderusData(
        temperatures=mock_temperatures,
        compressor_running=True,
        energy_blocked=False,
        dhw_extra_duration=0,
        heating_season_mode=1,
        dhw_program_mode=0,
        heating_curve_offset=0.0,
        dhw_stop_temp=55.0,
        dhw_setpoint=50.0,
    )


@pytest.fixture
def mock_coordinator(mock_buderus_data: MockBuderusData) -> MagicMock:
    """Create a mock coordinator for entity tests."""
    coordinator = MagicMock()
    coordinator.data = mock_buderus_data
    coordinator.port = "/dev/ttyACM0"
    coordinator.last_update_success = True

    # Async methods
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_set_energy_blocking = AsyncMock()
    coordinator.async_set_dhw_extra_duration = AsyncMock()
    coordinator.async_set_heating_season_mode = AsyncMock()
    coordinator.async_set_dhw_program_mode = AsyncMock()
    coordinator.async_set_dhw_stop_temp = AsyncMock()
    coordinator.async_set_dhw_setpoint = AsyncMock()
    coordinator.async_set_heating_curve_offset = AsyncMock()
    coordinator.async_manual_connect = AsyncMock()
    coordinator.async_manual_disconnect = AsyncMock()

    # Sync methods for optimistic update
    coordinator.async_set_updated_data = MagicMock()

    # Manual disconnect state
    coordinator._manually_disconnected = False

    return coordinator


@pytest.fixture
def mock_coordinator_disconnected() -> MagicMock:
    """Create a mock coordinator in disconnected state."""
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.port = "/dev/ttyACM0"
    coordinator.last_update_success = False

    return coordinator


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a minimal mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.bus = MagicMock()
    hass.bus.async_listen_once = MagicMock()
    hass.async_add_executor_job = AsyncMock(side_effect=lambda f, *args: f(*args))
    hass.async_create_task = MagicMock()
    hass.async_create_background_task = MagicMock()
    hass.states = MagicMock()

    return hass


@pytest.fixture
def mock_usb_adapter() -> MagicMock:
    """Create a mock USBtin adapter."""
    adapter = MagicMock()
    adapter.connect = MagicMock()
    adapter.disconnect = MagicMock()
    adapter.send_message = MagicMock()
    adapter.read_message = MagicMock(return_value=None)

    return adapter


@pytest.fixture
def mock_heat_pump_client(mock_usb_adapter: MagicMock) -> MagicMock:
    """Create a mock HeatPumpClient."""
    client = MagicMock()
    client.read_parameter = MagicMock(return_value={"decoded": 0})
    client.write_value = MagicMock()

    return client


@pytest.fixture
def mock_broadcast_monitor() -> MagicMock:
    """Create a mock BroadcastMonitor."""
    monitor = MagicMock()
    monitor.collect = MagicMock(return_value=MagicMock())

    return monitor


@pytest.fixture
def mock_menu_api() -> MagicMock:
    """Create a mock MenuAPI."""
    api = MagicMock()
    api.status = MagicMock()
    api.status.compressor_running = False
    api.hot_water = MagicMock()
    api.hot_water.extra_duration = 0

    return api
