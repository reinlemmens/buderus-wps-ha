"""
Unit tests for Menu API controllers - T020, T038, T047, T056, T063, T072, T078, T087.

Tests all controller classes with mocked HeatPumpClient.
"""

from datetime import date, datetime, time
from unittest.mock import MagicMock

import pytest

from buderus_wps.enums import (
    AlarmCategory,
    CircuitType,
    DHWProgramMode,
    OperatingMode,
    RoomProgramMode,
)
from buderus_wps.exceptions import (
    AlarmNotClearableError,
    CircuitNotAvailableError,
    MenuNavigationError,
    ParameterNotFoundError,
    ReadOnlyError,
    ValidationError,
)
from buderus_wps.menu_api import (
    Alarm,
    AlarmController,
    Circuit,
    EnergyView,
    HotWaterController,
    MenuAPI,
    MenuNavigator,
    StatusSnapshot,
    StatusView,
    VacationController,
    VacationPeriod,
)
from buderus_wps.schedule_codec import ScheduleSlot, WeeklySchedule


@pytest.fixture
def mock_client():
    """Create a mock HeatPumpClient."""
    client = MagicMock()
    return client


# =============================================================================
# T020: Unit tests for StatusView (US1)
# =============================================================================


class TestStatusView:
    """Test StatusView class."""

    def test_outdoor_temperature(self, mock_client):
        """Read outdoor temperature."""
        mock_client.read_parameter.return_value = {"decoded": 8.5}
        view = StatusView(mock_client)

        temp = view.outdoor_temperature
        assert temp == 8.5
        mock_client.read_parameter.assert_called()

    def test_supply_temperature(self, mock_client):
        """Read supply temperature."""
        mock_client.read_parameter.return_value = {"decoded": 35.0}
        view = StatusView(mock_client)

        temp = view.supply_temperature
        assert temp == 35.0

    def test_hot_water_temperature(self, mock_client):
        """Read hot water temperature."""
        mock_client.read_parameter.return_value = {"decoded": 52.0}
        view = StatusView(mock_client)

        temp = view.hot_water_temperature
        assert temp == 52.0

    def test_room_temperature_available(self, mock_client):
        """Read room temperature when sensor available."""
        mock_client.read_parameter.return_value = {"decoded": 21.5}
        view = StatusView(mock_client)

        temp = view.room_temperature
        assert temp == 21.5

    def test_room_temperature_unavailable(self, mock_client):
        """Room temperature returns None when not available."""
        mock_client.read_parameter.side_effect = ParameterNotFoundError("ROOM_TEMP")
        view = StatusView(mock_client)

        temp = view.room_temperature
        assert temp is None

    def test_operating_mode(self, mock_client):
        """Read operating mode."""
        mock_client.read_parameter.return_value = {"decoded": 1}
        view = StatusView(mock_client)

        mode = view.operating_mode
        assert mode == OperatingMode.HEATING

    def test_compressor_running_true(self, mock_client):
        """Compressor status true."""
        mock_client.read_parameter.return_value = {"decoded": 1}
        view = StatusView(mock_client)

        assert view.compressor_running is True

    def test_compressor_running_false(self, mock_client):
        """Compressor status false."""
        mock_client.read_parameter.return_value = {"decoded": 0}
        view = StatusView(mock_client)

        assert view.compressor_running is False

    def test_compressor_hours(self, mock_client):
        """Read compressor hours."""
        mock_client.read_parameter.return_value = {"decoded": 12500}
        view = StatusView(mock_client)

        hours = view.compressor_hours
        assert hours == 12500

    def test_read_all_returns_snapshot(self, mock_client):
        """read_all() returns StatusSnapshot."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 8.5},  # outdoor_temp
            {"decoded": 35.0},  # supply_temp
            {"decoded": 52.0},  # dhw_temp
            {"decoded": 21.5},  # room_temp
            {"decoded": 1},  # operating_mode
            {"decoded": 1},  # compressor_running
        ]
        view = StatusView(mock_client)

        snapshot = view.read_all()

        assert isinstance(snapshot, StatusSnapshot)
        assert snapshot.outdoor_temperature == 8.5
        assert snapshot.supply_temperature == 35.0
        assert snapshot.hot_water_temperature == 52.0
        assert snapshot.room_temperature == 21.5
        assert snapshot.operating_mode == OperatingMode.HEATING
        assert snapshot.compressor_running is True

    def test_outdoor_temp_missing_returns_none(self, mock_client):
        """Return None when outdoor temp unavailable (RTR reads are unreliable)."""
        mock_client.read_parameter.side_effect = ParameterNotFoundError("GT2_TEMP")
        view = StatusView(mock_client)

        # StatusView now returns None instead of raising, since RTR reads
        # are unreliable and broadcast monitoring should be used instead
        assert view.outdoor_temperature is None


# =============================================================================
# T038: Unit tests for HotWaterController (US3)
# =============================================================================


class TestHotWaterController:
    """Test HotWaterController class."""

    def test_temperature_read(self, mock_client):
        """Read DHW temperature."""
        mock_client.read_parameter.return_value = {"decoded": 50.0}
        ctrl = HotWaterController(mock_client)

        temp = ctrl.temperature
        assert temp == 50.0

    def test_temperature_write_valid(self, mock_client):
        """Write valid DHW temperature."""
        ctrl = HotWaterController(mock_client)

        ctrl.temperature = 55.0
        mock_client.write_value.assert_called_once_with("DHW_SETPOINT", 550)

    def test_temperature_write_below_range(self, mock_client):
        """Reject temperature below 20."""
        ctrl = HotWaterController(mock_client)

        with pytest.raises(ValidationError) as exc_info:
            ctrl.temperature = 19.0
        assert exc_info.value.field == "temperature"
        assert exc_info.value.value == 19.0

    def test_temperature_write_above_range(self, mock_client):
        """Reject temperature above 65."""
        ctrl = HotWaterController(mock_client)

        with pytest.raises(ValidationError) as exc_info:
            ctrl.temperature = 66.0
        assert exc_info.value.field == "temperature"

    def test_temperature_write_at_lower_bound(self, mock_client):
        """Accept temperature at lower bound (20)."""
        ctrl = HotWaterController(mock_client)

        ctrl.temperature = 20.0
        mock_client.write_value.assert_called_once()

    def test_temperature_write_at_upper_bound(self, mock_client):
        """Accept temperature at upper bound (65)."""
        ctrl = HotWaterController(mock_client)

        ctrl.temperature = 65.0
        mock_client.write_value.assert_called_once()

    def test_extra_duration_read(self, mock_client):
        """Read extra duration."""
        mock_client.read_parameter.return_value = {"decoded": 30}
        ctrl = HotWaterController(mock_client)

        duration = ctrl.extra_duration
        assert duration == 30

    def test_extra_duration_write(self, mock_client):
        """Write extra duration."""
        ctrl = HotWaterController(mock_client)

        ctrl.extra_duration = 60
        mock_client.write_value.assert_called()

    def test_program_mode_read(self, mock_client):
        """Read program mode."""
        mock_client.read_parameter.return_value = {"decoded": 1}
        ctrl = HotWaterController(mock_client)

        mode = ctrl.program_mode
        assert mode == DHWProgramMode.PROGRAM_1

    def test_program_mode_write(self, mock_client):
        """Write program mode."""
        ctrl = HotWaterController(mock_client)

        ctrl.program_mode = DHWProgramMode.PROGRAM_2
        mock_client.write_value.assert_called_with("DHW_PROGRAM_MODE", 2)


# =============================================================================
# T047: Unit tests for schedule read/write (US4)
# =============================================================================


class TestHotWaterSchedules:
    """Test HotWaterController schedule methods."""

    def test_get_schedule_program_1(self, mock_client):
        """Get Program 1 schedule."""
        # Return 2-byte encoded schedule for each day
        mock_client.read_value.return_value = bytes([12, 44])  # 06:00-22:00
        ctrl = HotWaterController(mock_client)

        schedule = ctrl.get_schedule(1)

        assert isinstance(schedule, WeeklySchedule)
        assert schedule.monday.start_time == time(6, 0)
        assert schedule.monday.end_time == time(22, 0)

    def test_get_schedule_program_2(self, mock_client):
        """Get Program 2 schedule."""
        mock_client.read_value.return_value = bytes([0, 47])  # 00:00-23:30
        ctrl = HotWaterController(mock_client)

        schedule = ctrl.get_schedule(2)
        assert schedule.monday.start_time == time(0, 0)
        assert schedule.monday.end_time == time(23, 30)

    def test_get_schedule_invalid_program(self, mock_client):
        """Reject invalid program number."""
        ctrl = HotWaterController(mock_client)

        with pytest.raises(ValueError) as exc_info:
            ctrl.get_schedule(3)
        assert "1 or 2" in str(exc_info.value)

    def test_set_schedule_writes_all_days(self, mock_client):
        """set_schedule writes 7 days."""
        slot = ScheduleSlot(time(6, 0), time(22, 0))
        schedule = WeeklySchedule(
            monday=slot,
            tuesday=slot,
            wednesday=slot,
            thursday=slot,
            friday=slot,
            saturday=slot,
            sunday=slot,
        )
        ctrl = HotWaterController(mock_client)

        ctrl.set_schedule(1, schedule)

        # Should write 7 times (once per day)
        assert mock_client.write_value.call_count == 7

    def test_set_schedule_validates_30min(self, mock_client):
        """set_schedule validates 30-minute boundaries."""
        bad_slot = ScheduleSlot(time(6, 15), time(22, 0))  # Invalid: 15 min
        schedule = WeeklySchedule(
            monday=bad_slot,
            tuesday=bad_slot,
            wednesday=bad_slot,
            thursday=bad_slot,
            friday=bad_slot,
            saturday=bad_slot,
            sunday=bad_slot,
        )
        ctrl = HotWaterController(mock_client)

        with pytest.raises(ValidationError):
            ctrl.set_schedule(1, schedule)


# =============================================================================
# T056: Unit tests for program mode control (US5)
# =============================================================================


class TestCircuitProgramMode:
    """Test Circuit program mode control."""

    def test_program_mode_read(self, mock_client):
        """Read circuit program mode."""
        mock_client.read_parameter.return_value = {"decoded": 1}
        circuit = Circuit(mock_client, 1)

        mode = circuit.program_mode
        assert mode == RoomProgramMode.PROGRAM_1

    def test_program_mode_write(self, mock_client):
        """Write circuit program mode."""
        circuit = Circuit(mock_client, 1)

        circuit.program_mode = RoomProgramMode.PROGRAM_2
        mock_client.write_value.assert_called()

    def test_summer_mode_read(self, mock_client):
        """Read summer mode status."""
        mock_client.read_parameter.return_value = {"decoded": 1}
        circuit = Circuit(mock_client, 1)

        assert circuit.summer_mode is True

    def test_summer_threshold_read(self, mock_client):
        """Read summer threshold."""
        mock_client.read_parameter.return_value = {"decoded": 18.0}
        circuit = Circuit(mock_client, 1)

        threshold = circuit.summer_threshold
        assert threshold == 18.0


# =============================================================================
# T063: Unit tests for VacationController (US9)
# =============================================================================


class TestVacationController:
    """Test VacationController class."""

    def test_get_circuit_inactive(self, mock_client):
        """Get vacation for circuit with no vacation set."""
        mock_client.read_parameter.return_value = {"decoded": 0}
        ctrl = VacationController(mock_client)

        period = ctrl.get_circuit(1)
        assert period.active is False

    def test_get_circuit_active(self, mock_client):
        """Get vacation for circuit with vacation set."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 1},  # start date (non-zero)
            {"decoded": 2},  # end date
        ]
        ctrl = VacationController(mock_client)

        period = ctrl.get_circuit(1)
        assert period.active is True

    def test_get_circuit_invalid_number(self, mock_client):
        """Reject invalid circuit number."""
        ctrl = VacationController(mock_client)

        with pytest.raises(CircuitNotAvailableError):
            ctrl.get_circuit(5)

    def test_set_circuit_clears_vacation(self, mock_client):
        """Setting inactive period clears vacation."""
        ctrl = VacationController(mock_client)

        ctrl.set_circuit(1, VacationPeriod(active=False))
        assert mock_client.write_value.call_count == 2  # start and end

    def test_clear_circuit(self, mock_client):
        """Clear circuit vacation."""
        ctrl = VacationController(mock_client)

        ctrl.clear_circuit(1)
        assert mock_client.write_value.call_count == 2

    def test_hot_water_vacation_inactive(self, mock_client):
        """Get DHW vacation when not set."""
        mock_client.read_parameter.return_value = {"decoded": 0}
        ctrl = VacationController(mock_client)

        period = ctrl.hot_water
        assert period.active is False

    def test_set_hot_water_vacation(self, mock_client):
        """Set DHW vacation period."""
        ctrl = VacationController(mock_client)

        ctrl.set_hot_water(
            VacationPeriod(
                active=True,
                start_date=date(2024, 12, 1),
                end_date=date(2024, 12, 15),
            )
        )
        assert mock_client.write_value.call_count == 2

    def test_clear_hot_water(self, mock_client):
        """Clear DHW vacation."""
        ctrl = VacationController(mock_client)

        ctrl.clear_hot_water()
        assert mock_client.write_value.call_count == 2


# =============================================================================
# T072: Unit tests for EnergyView (US6)
# =============================================================================


class TestEnergyView:
    """Test EnergyView class."""

    def test_heat_generated_kwh(self, mock_client):
        """Read heat generated."""
        mock_client.read_parameter.return_value = {"decoded": 12500.5}
        view = EnergyView(mock_client)

        kwh = view.heat_generated_kwh
        assert kwh == 12500.5

    def test_aux_heater_kwh(self, mock_client):
        """Read auxiliary heater consumption."""
        mock_client.read_parameter.return_value = {"decoded": 250.0}
        view = EnergyView(mock_client)

        kwh = view.aux_heater_kwh
        assert kwh == 250.0


# =============================================================================
# T078: Unit tests for AlarmController (US7)
# =============================================================================


class TestAlarmController:
    """Test AlarmController class."""

    def test_active_alarms_empty(self, mock_client):
        """No active alarms."""
        mock_client.read_parameter.return_value = {"decoded": 0}
        ctrl = AlarmController(mock_client)

        alarms = ctrl.active_alarms
        assert alarms == []

    def test_active_alarms_present(self, mock_client):
        """Active alarms present."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 101},  # alarm 1
            {"decoded": 0},  # alarm 2 (none)
            {"decoded": 0},
            {"decoded": 0},
            {"decoded": 0},
        ]
        ctrl = AlarmController(mock_client)

        alarms = ctrl.active_alarms
        assert len(alarms) == 1
        assert alarms[0].code == 1

    def test_alarm_log(self, mock_client):
        """Read alarm log."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 101},
            {"decoded": 102},
            {"decoded": 0},
            {"decoded": 0},
            {"decoded": 0},
        ]
        ctrl = AlarmController(mock_client)

        log = ctrl.alarm_log
        assert len(log) == 2

    def test_info_log(self, mock_client):
        """Read info log."""
        mock_client.read_parameter.side_effect = [
            {"decoded": 50},
            {"decoded": 0},
            {"decoded": 0},
            {"decoded": 0},
            {"decoded": 0},
        ]
        ctrl = AlarmController(mock_client)

        log = ctrl.info_log
        assert len(log) == 1
        assert log[0].category == AlarmCategory.INFO

    def test_acknowledge_alarm(self, mock_client):
        """Acknowledge an alarm."""
        ctrl = AlarmController(mock_client)
        alarm = Alarm(
            code=1,
            category=AlarmCategory.ALARM,
            description="Test",
            timestamp=datetime.now(),
            acknowledged=False,
            clearable=True,
        )

        ctrl.acknowledge(alarm)
        mock_client.write_value.assert_called()

    def test_clear_alarm_success(self, mock_client):
        """Clear a clearable alarm."""
        ctrl = AlarmController(mock_client)
        alarm = Alarm(
            code=1,
            category=AlarmCategory.ALARM,
            description="Test",
            timestamp=datetime.now(),
            acknowledged=True,
            clearable=True,
        )

        ctrl.clear(alarm)
        mock_client.write_value.assert_called()

    def test_clear_alarm_not_clearable(self, mock_client):
        """Cannot clear non-clearable alarm."""
        ctrl = AlarmController(mock_client)
        alarm = Alarm(
            code=1,
            category=AlarmCategory.ALARM,
            description="Test",
            timestamp=datetime.now(),
            acknowledged=True,
            clearable=False,
        )

        with pytest.raises(AlarmNotClearableError):
            ctrl.clear(alarm)


# =============================================================================
# T087: Unit tests for Circuit class (US8)
# =============================================================================


class TestCircuit:
    """Test Circuit class."""

    def test_circuit_number(self, mock_client):
        """Circuit has correct number."""
        circuit = Circuit(mock_client, 2)
        assert circuit.number == 2

    def test_circuit_type_unmixed(self, mock_client):
        """Circuit 1 is unmixed."""
        circuit = Circuit(mock_client, 1)
        assert circuit.circuit_type == CircuitType.UNMIXED

    def test_circuit_type_mixed(self, mock_client):
        """Circuits 2-4 are mixed."""
        circuit = Circuit(mock_client, 2)
        assert circuit.circuit_type == CircuitType.MIXED

    def test_temperature_read(self, mock_client):
        """Read circuit temperature."""
        mock_client.read_parameter.return_value = {"decoded": 38.5}
        circuit = Circuit(mock_client, 1)

        temp = circuit.temperature
        assert temp == 38.5

    def test_setpoint_read(self, mock_client):
        """Read circuit setpoint."""
        mock_client.read_parameter.return_value = {"decoded": 22.0}
        circuit = Circuit(mock_client, 1)

        setpoint = circuit.setpoint
        assert setpoint == 22.0

    def test_setpoint_write(self, mock_client):
        """Write circuit setpoint."""
        circuit = Circuit(mock_client, 1)

        circuit.setpoint = 23.0
        mock_client.write_value.assert_called()

    def test_get_schedule(self, mock_client):
        """Get circuit schedule."""
        mock_client.read_value.return_value = bytes([12, 44])
        circuit = Circuit(mock_client, 1)

        schedule = circuit.get_schedule(1)
        assert isinstance(schedule, WeeklySchedule)

    def test_set_schedule(self, mock_client):
        """Set circuit schedule."""
        slot = ScheduleSlot(time(6, 0), time(22, 0))
        schedule = WeeklySchedule(
            monday=slot,
            tuesday=slot,
            wednesday=slot,
            thursday=slot,
            friday=slot,
            saturday=slot,
            sunday=slot,
        )
        circuit = Circuit(mock_client, 1)

        circuit.set_schedule(1, schedule)
        assert mock_client.write_value.call_count == 7


# =============================================================================
# MenuNavigator Tests (US2 - already covered in test_menu_structure.py)
# =============================================================================


class TestMenuNavigator:
    """Test MenuNavigator class."""

    def test_navigate_to_valid_path(self, mock_client):
        """Navigate to valid menu path."""
        nav = MenuNavigator(mock_client)

        item = nav.navigate("Status")
        assert item.name == "Status"
        assert nav.path == ["Status"]

    def test_navigate_nested(self, mock_client):
        """Navigate to nested path."""
        nav = MenuNavigator(mock_client)

        item = nav.navigate("Hot Water/Temperature")
        assert item.name == "Temperature"
        assert nav.path == ["Hot Water", "Temperature"]

    def test_navigate_invalid_path(self, mock_client):
        """Navigate to invalid path raises."""
        nav = MenuNavigator(mock_client)

        with pytest.raises(MenuNavigationError) as exc_info:
            nav.navigate("NotAMenu")
        assert "NotAMenu" in str(exc_info.value)

    def test_up_from_nested(self, mock_client):
        """Go up from nested item."""
        nav = MenuNavigator(mock_client)
        nav.navigate("Hot Water/Temperature")

        item = nav.up()
        assert item.name == "Hot Water"

    def test_up_from_root(self, mock_client):
        """Go up from root stays at root."""
        nav = MenuNavigator(mock_client)

        item = nav.up()
        assert item.name == "Root"

    def test_items_lists_children(self, mock_client):
        """items() lists current children."""
        nav = MenuNavigator(mock_client)

        items = nav.items()
        names = [i.name for i in items]
        assert "Status" in names
        assert "Hot Water" in names

    def test_get_value_no_parameter(self, mock_client):
        """get_value on non-parameter item raises."""
        nav = MenuNavigator(mock_client)
        nav.navigate("Status")

        with pytest.raises(ReadOnlyError):
            nav.get_value()

    def test_set_value_not_writable(self, mock_client):
        """set_value on read-only item raises."""
        nav = MenuNavigator(mock_client)
        mock_client.read_parameter.return_value = {"decoded": 8.5}

        nav.navigate("Status/Outdoor Temperature")

        with pytest.raises(ReadOnlyError):
            nav.set_value(10.0)


# =============================================================================
# MenuAPI Tests
# =============================================================================


class TestMenuAPI:
    """Test MenuAPI main class."""

    def test_create_menu_api(self, mock_client):
        """Create MenuAPI instance."""
        api = MenuAPI(mock_client)

        assert api.status is not None
        assert api.hot_water is not None
        assert api.energy is not None
        assert api.alarms is not None
        assert api.vacation is not None
        assert api.menu is not None

    def test_get_circuit_valid(self, mock_client):
        """Get valid circuit."""
        api = MenuAPI(mock_client)

        circuit = api.get_circuit(1)
        assert circuit.number == 1

    def test_get_circuit_invalid(self, mock_client):
        """Get invalid circuit number raises."""
        api = MenuAPI(mock_client)

        with pytest.raises(CircuitNotAvailableError):
            api.get_circuit(5)

    def test_get_circuit_cached(self, mock_client):
        """Same circuit returned for same number."""
        api = MenuAPI(mock_client)

        c1 = api.get_circuit(1)
        c2 = api.get_circuit(1)
        assert c1 is c2

    def test_status_property(self, mock_client):
        """status property returns StatusView."""
        api = MenuAPI(mock_client)
        assert isinstance(api.status, StatusView)

    def test_hot_water_property(self, mock_client):
        """hot_water property returns HotWaterController."""
        api = MenuAPI(mock_client)
        assert isinstance(api.hot_water, HotWaterController)
