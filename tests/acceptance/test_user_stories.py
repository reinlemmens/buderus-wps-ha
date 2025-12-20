"""
Acceptance tests for Menu API User Stories - T022, T031, T040, T049, T058, T065, T074, T080, T089, T095.

These tests verify each user story's acceptance scenarios.
"""

from datetime import date, time
from unittest.mock import MagicMock

import pytest

from buderus_wps.enums import (
    AlarmCategory,
    CircuitType,
    DHWProgramMode,
    OperatingMode,
    RoomProgramMode,
)
from buderus_wps.exceptions import CircuitNotAvailableError, ValidationError
from buderus_wps.menu_api import MenuAPI, VacationPeriod
from buderus_wps.schedule_codec import ScheduleSlot, WeeklySchedule


@pytest.fixture
def mock_client():
    """Create a mock HeatPumpClient for acceptance tests."""
    client = MagicMock()
    client.read_parameter.return_value = {"decoded": 0}
    client.read_value.return_value = bytes([12, 44])
    return client


@pytest.fixture
def api(mock_client):
    """Create MenuAPI instance."""
    return MenuAPI(mock_client)


# =============================================================================
# T022: US1 - Read Current System Status (MVP)
# =============================================================================


class TestUS1StatusReading:
    """
    As a homeowner, I want to see current temperatures and operating status
    so I can understand my heating system's state.

    Acceptance Criteria:
    - AC1: Display outdoor, supply, and DHW temperatures
    - AC2: Show operating mode and compressor status
    - AC3: Read all status in under 2 seconds
    """

    def test_ac1_display_temperatures(self, mock_client):
        """AC1: Display outdoor, supply, and DHW temperatures."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 8.5},  # outdoor
            {"decoded": 35.0},  # supply
            {"decoded": 52.0},  # dhw
            {"decoded": 21.5},  # room
            {"decoded": 1},  # mode
            {"decoded": 1},  # compressor
        ]

        api = MenuAPI(mock_client)
        status = api.status.read_all()

        assert status.outdoor_temperature == 8.5
        assert status.supply_temperature == 35.0
        assert status.hot_water_temperature == 52.0

    def test_ac2_show_operating_status(self, mock_client):
        """AC2: Show operating mode and compressor status."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 8.5},
            {"decoded": 35.0},
            {"decoded": 52.0},
            {"decoded": None},
            {"decoded": 1},  # HEATING mode
            {"decoded": 1},  # compressor running
        ]

        api = MenuAPI(mock_client)
        status = api.status.read_all()

        assert status.operating_mode == OperatingMode.HEATING
        assert status.compressor_running is True

    def test_ac3_read_all_performance(self, mock_client):
        """AC3: Read all status in under 2 seconds."""
        import time as time_module

        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)

        start = time_module.time()
        _ = api.status.read_all()
        elapsed = time_module.time() - start

        assert elapsed < 2.0, f"Status read took {elapsed:.2f}s (max: 2.0s)"


# =============================================================================
# T031: US2 - Navigate Menu Structure
# =============================================================================


class TestUS2MenuNavigation:
    """
    As a homeowner, I want to explore available settings through a menu
    so I can find the features I need.

    Acceptance Criteria:
    - AC1: Navigate menu hierarchy like physical display
    - AC2: Access settings via path names
    - AC3: Navigate completes in under 5 seconds
    """

    def test_ac1_navigate_like_physical_display(self, api):
        """AC1: Navigate menu hierarchy like physical display."""
        # Start at root
        assert api.menu.current.name == "Root"

        # Navigate to Status (like pressing down/select on device)
        api.menu.navigate("Status")
        assert api.menu.current.name == "Status"

        # List available items
        items = api.menu.items()
        assert len(items) > 0

        # Go back (like pressing back button)
        api.menu.up()
        assert api.menu.current.name == "Root"

    def test_ac2_access_via_path_names(self, api):
        """AC2: Access settings via path names."""
        # Navigate directly using path
        item = api.menu.navigate("Hot Water/Temperature")
        assert item.name == "Temperature"
        assert api.menu.path == ["Hot Water", "Temperature"]

        # Navigate to another path
        item = api.menu.navigate("Status/Outdoor Temperature")
        assert item.name == "Outdoor Temperature"

    def test_ac3_navigation_performance(self, api):
        """AC3: Navigate completes in under 5 seconds."""
        import time as time_module

        start = time_module.time()

        # Simulate multiple navigation operations
        api.menu.navigate("Status")
        api.menu.navigate("Hot Water/Temperature")
        api.menu.navigate("Programs")
        api.menu.up()

        elapsed = time_module.time() - start
        assert elapsed < 5.0, f"Navigation took {elapsed:.2f}s (max: 5.0s)"


# =============================================================================
# T040: US3 - Hot Water Settings
# =============================================================================


class TestUS3HotWaterSettings:
    """
    As a homeowner, I want to read and modify hot water settings
    so I can control my DHW system.

    Acceptance Criteria:
    - AC1: Read DHW temperature
    - AC2: Modify temperature within 20-65 range
    - AC3: Read and set program mode
    - AC4: Reject invalid temperatures
    """

    def test_ac1_read_dhw_temperature(self, mock_client):
        """AC1: Read DHW temperature."""
        mock_client.read_parameter.return_value = {"decoded": 50.0}

        api = MenuAPI(mock_client)
        temp = api.hot_water.temperature

        assert temp == 50.0

    def test_ac2_modify_temperature_in_range(self, mock_client):
        """AC2: Modify temperature within 20-65 range."""
        api = MenuAPI(mock_client)

        # Set to valid value
        api.hot_water.temperature = 55.0
        mock_client.write_value.assert_called_with("DHW_SETPOINT", 550)

        # Boundary values
        api.hot_water.temperature = 20.0  # min
        api.hot_water.temperature = 65.0  # max

    def test_ac3_program_mode(self, mock_client):
        """AC3: Read and set program mode."""
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)

        # Read current mode
        mode = api.hot_water.program_mode
        assert mode == DHWProgramMode.ALWAYS_ON

        # Set new mode
        api.hot_water.program_mode = DHWProgramMode.PROGRAM_1
        mock_client.write_value.assert_called_with("DHW_PROGRAM_MODE", 1)

    def test_ac4_reject_invalid_temperatures(self, mock_client):
        """AC4: Reject invalid temperatures."""
        api = MenuAPI(mock_client)

        with pytest.raises(ValidationError):
            api.hot_water.temperature = 19.0  # Below min

        with pytest.raises(ValidationError):
            api.hot_water.temperature = 66.0  # Above max


# =============================================================================
# T049: US4 - Weekly Schedules
# =============================================================================


class TestUS4WeeklySchedules:
    """
    As a homeowner, I want to view and modify weekly schedules
    so I can optimize heating times.

    Acceptance Criteria:
    - AC1: Read DHW weekly schedule
    - AC2: Modify schedule times (30-min resolution)
    - AC3: Set different schedules for weekdays/weekends
    - AC4: Reject non-30-minute times
    """

    def test_ac1_read_dhw_schedule(self, mock_client):
        """AC1: Read DHW weekly schedule."""
        mock_client.read_value.return_value = bytes([12, 44])  # 06:00-22:00

        api = MenuAPI(mock_client)
        schedule = api.hot_water.get_schedule(1)

        assert schedule.monday.start_time == time(6, 0)
        assert schedule.monday.end_time == time(22, 0)

    def test_ac2_modify_schedule_30min_resolution(self, mock_client):
        """AC2: Modify schedule times (30-min resolution)."""
        slot = ScheduleSlot(time(6, 30), time(22, 30))
        schedule = WeeklySchedule(
            monday=slot,
            tuesday=slot,
            wednesday=slot,
            thursday=slot,
            friday=slot,
            saturday=slot,
            sunday=slot,
        )

        api = MenuAPI(mock_client)
        api.hot_water.set_schedule(1, schedule)

        assert mock_client.write_value.call_count == 7

    def test_ac3_different_weekend_schedule(self, mock_client):
        """AC3: Set different schedules for weekdays/weekends."""
        weekday = ScheduleSlot(time(6, 0), time(22, 0))
        weekend = ScheduleSlot(time(8, 0), time(23, 30))

        schedule = WeeklySchedule(
            monday=weekday,
            tuesday=weekday,
            wednesday=weekday,
            thursday=weekday,
            friday=weekday,
            saturday=weekend,
            sunday=weekend,
        )

        api = MenuAPI(mock_client)
        api.hot_water.set_schedule(1, schedule)

        assert mock_client.write_value.call_count == 7

    def test_ac4_reject_non_30min_times(self, mock_client):
        """AC4: Reject non-30-minute times."""
        bad_slot = ScheduleSlot(time(6, 15), time(22, 0))  # 15 min invalid
        schedule = WeeklySchedule(
            monday=bad_slot,
            tuesday=bad_slot,
            wednesday=bad_slot,
            thursday=bad_slot,
            friday=bad_slot,
            saturday=bad_slot,
            sunday=bad_slot,
        )

        api = MenuAPI(mock_client)

        with pytest.raises(ValidationError):
            api.hot_water.set_schedule(1, schedule)


# =============================================================================
# T058: US5 - Control Operating Modes
# =============================================================================


class TestUS5OperatingModes:
    """
    As a homeowner, I want to switch program modes
    so I can change heating behavior.

    Acceptance Criteria:
    - AC1: Read current program mode
    - AC2: Switch between program modes
    - AC3: Read summer mode status
    """

    def test_ac1_read_program_mode(self, mock_client):
        """AC1: Read current program mode."""
        mock_client.read_parameter.return_value = {"decoded": 1}

        api = MenuAPI(mock_client)
        circuit = api.get_circuit(1)

        mode = circuit.program_mode
        assert mode == RoomProgramMode.PROGRAM_1

    def test_ac2_switch_program_modes(self, mock_client):
        """AC2: Switch between program modes."""
        api = MenuAPI(mock_client)
        circuit = api.get_circuit(1)

        circuit.program_mode = RoomProgramMode.PROGRAM_2
        mock_client.write_value.assert_called()

    def test_ac3_read_summer_mode(self, mock_client):
        """AC3: Read summer mode status."""
        mock_client.read_parameter.return_value = {"decoded": 1}

        api = MenuAPI(mock_client)
        circuit = api.get_circuit(1)

        assert circuit.summer_mode is True


# =============================================================================
# T065: US9 - Vacation Mode
# =============================================================================


class TestUS9VacationMode:
    """
    As a homeowner, I want to configure vacation mode
    so I can reduce heating while away.

    Acceptance Criteria:
    - AC1: Set vacation dates for circuits
    - AC2: Set vacation for DHW
    - AC3: Clear vacation mode
    """

    def test_ac1_set_circuit_vacation(self, mock_client):
        """AC1: Set vacation dates for circuits."""
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)

        period = VacationPeriod(
            active=True,
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 15),
        )
        api.vacation.set_circuit(1, period)

        assert mock_client.write_value.call_count == 2

    def test_ac2_set_dhw_vacation(self, mock_client):
        """AC2: Set vacation for DHW."""
        api = MenuAPI(mock_client)

        period = VacationPeriod(
            active=True,
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 15),
        )
        api.vacation.set_hot_water(period)

        assert mock_client.write_value.call_count == 2

    def test_ac3_clear_vacation(self, mock_client):
        """AC3: Clear vacation mode."""
        api = MenuAPI(mock_client)

        api.vacation.clear_circuit(1)
        api.vacation.clear_hot_water()

        # Each clear writes 2 values (start=0, end=0)
        assert mock_client.write_value.call_count == 4


# =============================================================================
# T074: US6 - Energy Statistics
# =============================================================================


class TestUS6EnergyStatistics:
    """
    As a homeowner, I want to see energy statistics
    so I can monitor efficiency.

    Acceptance Criteria:
    - AC1: Read heat generated kWh
    - AC2: Read auxiliary heater kWh
    """

    def test_ac1_heat_generated(self, mock_client):
        """AC1: Read heat generated kWh."""
        mock_client.read_parameter.return_value = {"decoded": 12500.5}

        api = MenuAPI(mock_client)
        kwh = api.energy.heat_generated_kwh

        assert kwh == 12500.5

    def test_ac2_aux_heater(self, mock_client):
        """AC2: Read auxiliary heater kWh."""
        mock_client.read_parameter.return_value = {"decoded": 250.0}

        api = MenuAPI(mock_client)
        kwh = api.energy.aux_heater_kwh

        assert kwh == 250.0


# =============================================================================
# T080: US7 - Alarms
# =============================================================================


class TestUS7Alarms:
    """
    As a homeowner, I want to see and manage alarms
    so I can respond to issues.

    Acceptance Criteria:
    - AC1: Read active alarms
    - AC2: Read alarm log
    - AC3: Acknowledge alarms
    """

    def test_ac1_read_active_alarms(self, mock_client):
        """AC1: Read active alarms."""
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)
        alarms = api.alarms.active_alarms

        assert isinstance(alarms, list)

    def test_ac2_read_alarm_log(self, mock_client):
        """AC2: Read alarm log."""
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)
        log = api.alarms.alarm_log

        assert isinstance(log, list)

    def test_ac3_acknowledge_alarm(self, mock_client):
        """AC3: Acknowledge alarms."""
        from datetime import datetime

        from buderus_wps.menu_api import Alarm

        api = MenuAPI(mock_client)

        alarm = Alarm(
            code=1,
            category=AlarmCategory.ALARM,
            description="Test alarm",
            timestamp=datetime.now(),
            acknowledged=False,
            clearable=True,
        )

        api.alarms.acknowledge(alarm)
        mock_client.write_value.assert_called()


# =============================================================================
# T089: US8 - Multi-Circuit Configuration
# =============================================================================


class TestUS8MultiCircuit:
    """
    As a homeowner, I want to access multiple heating circuits
    so I can control each zone.

    Acceptance Criteria:
    - AC1: Access circuits 1-4
    - AC2: Read circuit-specific settings
    - AC3: Modify circuit setpoints
    - AC4: Reject invalid circuit numbers
    """

    def test_ac1_access_all_circuits(self, mock_client):
        """AC1: Access circuits 1-4."""
        api = MenuAPI(mock_client)

        for i in range(1, 5):
            circuit = api.get_circuit(i)
            assert circuit.number == i

    def test_ac2_read_circuit_settings(self, mock_client):
        """AC2: Read circuit-specific settings."""
        mock_client.read_parameter.return_value = {"decoded": 38.0}

        api = MenuAPI(mock_client)
        circuit = api.get_circuit(1)

        temp = circuit.temperature
        assert temp == 38.0

        # Check circuit type
        assert circuit.circuit_type == CircuitType.UNMIXED

    def test_ac3_modify_circuit_setpoint(self, mock_client):
        """AC3: Modify circuit setpoints."""
        api = MenuAPI(mock_client)
        circuit = api.get_circuit(1)

        circuit.setpoint = 22.0
        mock_client.write_value.assert_called()

    def test_ac4_reject_invalid_circuit(self, mock_client):
        """AC4: Reject invalid circuit numbers."""
        api = MenuAPI(mock_client)

        with pytest.raises(CircuitNotAvailableError):
            api.get_circuit(0)

        with pytest.raises(CircuitNotAvailableError):
            api.get_circuit(5)


# =============================================================================
# T095: Full acceptance test suite
# =============================================================================


class TestFullAcceptanceSuite:
    """Complete end-to-end workflow tests."""

    def test_complete_homeowner_workflow(self, mock_client):
        """Simulate complete homeowner interaction."""
        # Setup realistic responses
        mock_client.read_parameter.return_value = {"decoded": 20.0}
        mock_client.read_value.return_value = bytes([12, 44])

        api = MenuAPI(mock_client)

        # 1. Check status
        outdoor = api.status.outdoor_temperature
        assert outdoor == 20.0

        # 2. Navigate menu
        api.menu.navigate("Hot Water")
        items = api.menu.items()
        assert len(items) > 0

        # 3. Adjust DHW
        api.hot_water.temperature = 50.0

        # 4. Check schedule
        schedule = api.hot_water.get_schedule(1)
        assert schedule.monday is not None

        # 5. Check circuits
        for i in range(1, 5):
            circuit = api.get_circuit(i)
            assert circuit.number == i

        # 6. Check energy
        kwh = api.energy.heat_generated_kwh
        assert kwh == 20.0  # From our mock

        # 7. Check alarms
        alarms = api.alarms.active_alarms
        assert isinstance(alarms, list)

        # 8. Check vacation (mock returns non-zero, so vacation shows active)
        vacation = api.vacation.hot_water
        # With mock returning 20.0, vacation will appear active
        assert isinstance(vacation, VacationPeriod)

    def test_error_handling_workflow(self, mock_client):
        """Test graceful error handling throughout API."""
        api = MenuAPI(mock_client)

        # Invalid temperature rejected
        with pytest.raises(ValidationError):
            api.hot_water.temperature = 100.0

        # Invalid circuit rejected
        with pytest.raises(CircuitNotAvailableError):
            api.get_circuit(99)

        # Invalid schedule rejected
        bad_slot = ScheduleSlot(time(6, 15), time(22, 0))
        bad_schedule = WeeklySchedule(
            monday=bad_slot,
            tuesday=bad_slot,
            wednesday=bad_slot,
            thursday=bad_slot,
            friday=bad_slot,
            saturday=bad_slot,
            sunday=bad_slot,
        )
        with pytest.raises(ValidationError):
            api.hot_water.set_schedule(1, bad_schedule)
