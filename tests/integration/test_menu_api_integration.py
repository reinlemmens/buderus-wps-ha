"""
Integration tests for Menu API - T021, T030, T039, T048, T057, T064, T073, T079, T088.

Tests Menu API with mocked HeatPumpClient simulating realistic interactions.
"""

from datetime import time
from unittest.mock import MagicMock

import pytest
from buderus_wps.enums import DHWProgramMode, OperatingMode, RoomProgramMode
from buderus_wps.exceptions import ValidationError
from buderus_wps.menu_api import MenuAPI
from buderus_wps.schedule_codec import ScheduleSlot, WeeklySchedule


@pytest.fixture
def mock_client():
    """Create a realistic mock client."""
    client = MagicMock()
    # Set up default responses
    client.read_parameter.return_value = {"decoded": 0}
    client.read_value.return_value = bytes([12, 44])  # Default schedule 06:00-22:00
    return client


@pytest.fixture
def api(mock_client):
    """Create MenuAPI instance."""
    return MenuAPI(mock_client)


# =============================================================================
# T021: Integration test for status reading (US1)
# =============================================================================


class TestStatusIntegration:
    """Integration tests for status reading workflow."""

    def test_full_status_read_workflow(self, mock_client):
        """Complete status reading workflow."""
        # Simulate realistic responses using actual parameter names from STATUS_PARAMS
        responses = {
            "GT2_TEMP": {"decoded": 8.5},  # outdoor_temp
            "GT8_TEMP": {"decoded": 35.0},  # supply_temp
            "GT3_TEMP": {"decoded": 52.0},  # dhw_temp
            "ROOM_TEMP_C1": {"decoded": 21.5},  # room_temp
            "DRIFTTILLSTAND": {"decoded": 1},  # operating_mode
            "COMPRESSOR": {"decoded": 1},  # compressor_status (matches partial)
        }

        def read_param(name):
            # Check for exact match or partial match
            name_upper = name.upper()
            for key, val in responses.items():
                if key in name_upper or name_upper in key:
                    return val
            return {"decoded": 0}

        mock_client.read_parameter.side_effect = read_param

        api = MenuAPI(mock_client)
        snapshot = api.status.read_all()

        assert snapshot.outdoor_temperature == 8.5
        assert snapshot.supply_temperature == 35.0
        assert snapshot.hot_water_temperature == 52.0
        assert snapshot.operating_mode == OperatingMode.HEATING
        assert snapshot.compressor_running is True

    def test_status_batch_read_under_2_seconds(self, mock_client):
        """Verify status reading performance target (SC-001)."""
        import time as time_module

        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)

        start = time_module.time()
        _ = api.status.read_all()
        elapsed = time_module.time() - start

        # With mocked client, should be near-instant
        assert elapsed < 2.0


# =============================================================================
# T030: Integration test for menu navigation (US2)
# =============================================================================


class TestMenuNavigationIntegration:
    """Integration tests for menu navigation workflow."""

    def test_navigation_workflow(self, api):
        """Navigate through menu hierarchy."""
        # Start at root
        root = api.menu.current
        assert root.name == "Root"

        # Navigate to Status
        status = api.menu.navigate("Status")
        assert status.name == "Status"
        assert api.menu.path == ["Status"]

        # List children
        children = api.menu.items()
        names = [c.name for c in children]
        assert "Outdoor Temperature" in names

        # Go deeper
        temp = api.menu.navigate("Status/Outdoor Temperature")
        assert temp.name == "Outdoor Temperature"

        # Go back up
        api.menu.up()
        assert api.menu.current.name == "Status"

        api.menu.up()
        assert api.menu.current.name == "Root"

    def test_navigate_to_writable_item(self, mock_client):
        """Navigate and modify writable item."""
        mock_client.read_parameter.return_value = {"decoded": 50}

        api = MenuAPI(mock_client)
        api.menu.navigate("Hot Water/Temperature")

        item = api.menu.current
        assert item.writable is True
        assert item.value_range == (20, 65)


# =============================================================================
# T039: Integration test for DHW operations (US3)
# =============================================================================


class TestDHWIntegration:
    """Integration tests for DHW control workflow."""

    def test_dhw_temperature_workflow(self, mock_client):
        """Read, modify, verify DHW temperature."""
        mock_client.read_parameter.return_value = {"decoded": 50.0}

        api = MenuAPI(mock_client)

        # Read current
        current = api.hot_water.temperature
        assert current == 50.0

        # Modify
        api.hot_water.temperature = 55.0

        # Verify write was called with human-readable value (encoder handles conversion)
        mock_client.write_value.assert_called_with("DHW_SETPOINT", 55.0)

    def test_dhw_program_mode_workflow(self, mock_client):
        """Switch DHW program modes."""
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)

        # Read current mode
        mode = api.hot_water.program_mode
        assert mode == DHWProgramMode.ALWAYS_ON

        # Switch to Program 1
        api.hot_water.program_mode = DHWProgramMode.PROGRAM_1
        mock_client.write_value.assert_called_with("DHW_PROGRAM_MODE", 1)

    def test_dhw_validation_rejects_invalid(self, mock_client):
        """Validation prevents invalid temperature."""
        api = MenuAPI(mock_client)

        with pytest.raises(ValidationError) as exc_info:
            api.hot_water.temperature = 70.0  # Above max of 65

        assert exc_info.value.field == "temperature"
        assert exc_info.value.value == 70.0
        # Write should NOT have been called
        mock_client.write_value.assert_not_called()


# =============================================================================
# T048: Integration test for schedule operations (US4)
# =============================================================================


class TestScheduleIntegration:
    """Integration tests for schedule operations."""

    def test_dhw_schedule_read_workflow(self, mock_client):
        """Read complete DHW weekly schedule."""
        # Each day returns same schedule: 06:00-22:00
        mock_client.read_value.return_value = bytes([12, 44])

        api = MenuAPI(mock_client)
        schedule = api.hot_water.get_schedule(1)

        assert schedule.monday.start_time == time(6, 0)
        assert schedule.monday.end_time == time(22, 0)
        assert schedule.sunday.start_time == time(6, 0)

    def test_dhw_schedule_modify_workflow(self, mock_client):
        """Modify and write DHW schedule."""
        weekday_slot = ScheduleSlot(time(6, 0), time(22, 0))
        weekend_slot = ScheduleSlot(time(8, 0), time(23, 0))

        schedule = WeeklySchedule(
            monday=weekday_slot,
            tuesday=weekday_slot,
            wednesday=weekday_slot,
            thursday=weekday_slot,
            friday=weekday_slot,
            saturday=weekend_slot,
            sunday=weekend_slot,
        )

        api = MenuAPI(mock_client)
        api.hot_water.set_schedule(1, schedule)

        # Should have written 7 days
        assert mock_client.write_value.call_count == 7

    def test_circuit_schedule_workflow(self, mock_client):
        """Read circuit schedule."""
        mock_client.read_value.return_value = bytes([12, 44])

        api = MenuAPI(mock_client)
        circuit = api.get_circuit(1)
        schedule = circuit.get_schedule(1)

        assert schedule.monday.start_time == time(6, 0)


# =============================================================================
# T057: Integration test for mode switching (US5)
# =============================================================================


class TestModeSwitchingIntegration:
    """Integration tests for program mode control."""

    def test_circuit_mode_workflow(self, mock_client):
        """Switch circuit program mode."""
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)
        circuit = api.get_circuit(1)

        # Read current mode
        mode = circuit.program_mode
        assert mode == RoomProgramMode.HP_OPTIMIZED

        # Switch to Program 1
        circuit.program_mode = RoomProgramMode.PROGRAM_1
        mock_client.write_value.assert_called()

    def test_summer_mode_status(self, mock_client):
        """Read summer mode settings."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # summer_mode = True
            {"decoded": 18.0},  # threshold
        ]

        api = MenuAPI(mock_client)
        circuit = api.get_circuit(1)

        assert circuit.summer_mode is True


# =============================================================================
# T064: Integration test for vacation mode (US9)
# =============================================================================


class TestVacationIntegration:
    """Integration tests for vacation mode."""

    def test_vacation_workflow(self, mock_client):
        """Set and clear vacation mode."""
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)

        # Check initial state
        period = api.vacation.get_circuit(1)
        assert period.active is False

        # Clear (even if already clear)
        api.vacation.clear_circuit(1)
        assert mock_client.write_value.call_count == 2

    def test_dhw_vacation_workflow(self, mock_client):
        """Set DHW vacation."""
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)

        # Check initial
        period = api.vacation.hot_water
        assert period.active is False

        # Clear
        api.vacation.clear_hot_water()
        assert mock_client.write_value.call_count == 2


# =============================================================================
# T073: Integration test for energy reading (US6)
# =============================================================================


class TestEnergyIntegration:
    """Integration tests for energy statistics."""

    def test_energy_read_workflow(self, mock_client):
        """Read energy statistics."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 12500.5},  # heat_generated
            {"decoded": 250.0},  # aux_heater
        ]

        api = MenuAPI(mock_client)

        heat = api.energy.heat_generated_kwh
        aux = api.energy.aux_heater_kwh

        assert heat == 12500.5
        assert aux == 250.0


# =============================================================================
# T079: Integration test for alarm operations (US7)
# =============================================================================


class TestAlarmIntegration:
    """Integration tests for alarm management."""

    def test_alarm_workflow(self, mock_client):
        """Read and manage alarms."""
        # No active alarms
        mock_client.read_parameter.return_value = {"decoded": 0}

        api = MenuAPI(mock_client)

        alarms = api.alarms.active_alarms
        assert len(alarms) == 0

        log = api.alarms.alarm_log
        assert len(log) == 0

        info = api.alarms.info_log
        assert len(info) == 0


# =============================================================================
# T088: Integration test for multi-circuit operations (US8)
# =============================================================================


class TestMultiCircuitIntegration:
    """Integration tests for multi-circuit access."""

    def test_access_all_circuits(self, mock_client):
        """Access all 4 circuits."""
        mock_client.read_parameter.return_value = {"decoded": 20.0}

        api = MenuAPI(mock_client)

        for i in range(1, 5):
            circuit = api.get_circuit(i)
            assert circuit.number == i

    def test_circuits_independent(self, mock_client):
        """Each circuit has independent settings."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 38.0},  # circuit 1 temp
            {"decoded": 42.0},  # circuit 2 temp
        ]

        api = MenuAPI(mock_client)

        c1 = api.get_circuit(1)
        c2 = api.get_circuit(2)

        t1 = c1.temperature
        t2 = c2.temperature

        assert t1 == 38.0
        assert t2 == 42.0
