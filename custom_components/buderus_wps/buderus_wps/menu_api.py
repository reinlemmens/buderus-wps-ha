"""
High-level Menu API for Buderus WPS Heat Pump.

This module provides a menu-style interface to the heat pump that mirrors
the physical display menu structure. It builds on top of HeatPumpClient
to provide human-readable access to temperatures, settings, and schedules.

IMPORTANT - VALUE ENCODING CONVENTION
=====================================
All temperature and value setters in this module expect **human-readable values**.
The HeatPumpClient.write_value() method handles conversion to raw CAN format internally.

DO NOT pre-scale values before passing to write_value(). The encoder does this automatically.

Temperature Parameters (format='tem', factor=0.1):
--------------------------------------------------
- HEATING_CURVE_PARALLEL_OFFSET_GLOBAL (idx=804)
    Human-readable: -10.0 to +10.0 °C
    Raw CAN: -100 to 100
    Usage: client.write_value("HEATING_CURVE_PARALLEL_OFFSET_GLOBAL", 2.5)
           → Encoder converts 2.5°C to raw 25

- XDHW_STOP_TEMP (idx=2478) - DHW stop charging temperature
    Human-readable: 45.0 to 65.0 °C
    Raw CAN: 450 to 650
    Usage: api.hot_water.stop_temperature = 55.0  # Pass 55.0, NOT 550
    Note: idx varies by firmware; element discovery updates actual value

- DHW_SETPOINT - DHW target temperature
    Human-readable: 45.0 to 65.0 °C
    Usage: api.hot_water.temperature = 50.0  # Pass 50.0, NOT 500

- GT*_TEMP - Temperature sensor readings (read-only)
    Human-readable: Returned as °C directly
    Example: api.status.outdoor_temperature returns 5.2 (meaning 5.2°C)

Integer Parameters (format='int', factor=1):
--------------------------------------------
- XDHW_TIME (idx=2480) - Extra DHW duration
    Human-readable: 0 to 48 hours
    Raw CAN: 0 to 48 (same as human-readable)
    Usage: api.hot_water.extra_duration = 2  # 2 hours

Selector Parameters (format='dp2', 'rp1', etc.):
------------------------------------------------
- DHW_PROGRAM_MODE - DHW program selection
    Values: 0=Automatic, 1=Always_On, 2=Always_Off
    Usage: api.hot_water.program_mode = DHWProgramMode.AUTOMATIC

Example:
    >>> from buderus_wps import USBtinAdapter, HeatPumpClient, MenuAPI
    >>> adapter = USBtinAdapter('/dev/ttyACM0')
    >>> adapter.connect()
    >>> client = HeatPumpClient(adapter)
    >>> api = MenuAPI(client)
    >>> print(f"Outdoor: {api.status.outdoor_temperature}°C")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional, cast

from .enums import (
    AlarmCategory,
    CircuitType,
    DHWProgramMode,
    OperatingMode,
    RoomProgramMode,
)
from .exceptions import (
    AlarmNotClearableError,
    CircuitNotAvailableError,
    MenuNavigationError,
    ReadOnlyError,
    ValidationError,
)
from .menu_structure import (
    ALARM_PARAMS,
    CIRCUIT_PARAMS,
    DHW_PARAMS,
    ENERGY_PARAMS,
    MENU_ROOT,
    STATUS_PARAMS,
    VACATION_PARAMS,
    MenuItem,
    get_circuit_param,
)
from .schedule_codec import ScheduleCodec, WeeklySchedule

if TYPE_CHECKING:
    from .heat_pump import HeatPumpClient


# =============================================================================
# Constants
# =============================================================================

# Day names for schedule iteration (Monday=0, Sunday=6)
WEEKDAYS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StatusSnapshot:
    """Complete status reading from a single operation.

    Note: Temperature values may be None if RTR reads fail due to CAN bus
    traffic. Use BroadcastMonitor for reliable temperature readings.
    """

    outdoor_temperature: Optional[float]
    supply_temperature: Optional[float]
    hot_water_temperature: Optional[float]
    room_temperature: Optional[float]
    operating_mode: OperatingMode
    compressor_running: bool
    heating_season_mode: int
    dhw_program_mode: int


@dataclass
class VacationPeriod:
    """Vacation mode configuration."""

    active: bool
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    reduced_setpoint: Optional[float] = None


@dataclass
class Alarm:
    """An active or historical alarm."""

    code: int
    category: AlarmCategory
    description: str
    timestamp: datetime
    acknowledged: bool
    clearable: bool


# =============================================================================
# Controller Classes
# =============================================================================


class StatusView:
    """Read-only access to heat pump status and temperatures."""

    def __init__(self, client: HeatPumpClient) -> None:
        self._client = client

    def _read_temp(self, param_name: str) -> Optional[float]:
        """Read a temperature parameter, returning None if not available.

        Note: RTR-based reads often fail due to CAN bus traffic. Consider
        using BroadcastMonitor for reliable temperature readings.
        """
        try:
            result = self._client.read_parameter(param_name)
            decoded = result.get("decoded")
            if decoded is not None:
                return float(decoded)
            return None
        except Exception:
            # RTR reads are unreliable - broadcast traffic can interfere
            return None

    @property
    def outdoor_temperature(self) -> Optional[float]:
        """Outdoor temperature in degrees Celsius, or None if unavailable."""
        return self._read_temp(STATUS_PARAMS["outdoor_temp"])

    @property
    def supply_temperature(self) -> Optional[float]:
        """Supply line temperature in degrees Celsius, or None if unavailable."""
        return self._read_temp(STATUS_PARAMS["supply_temp"])

    @property
    def hot_water_temperature(self) -> Optional[float]:
        """DHW tank temperature in degrees Celsius, or None if unavailable."""
        return self._read_temp(STATUS_PARAMS["dhw_temp"])

    @property
    def room_temperature(self) -> Optional[float]:
        """Room temperature if sensor available, else None."""
        return self._read_temp(STATUS_PARAMS["room_temp"])

    @property
    def operating_mode(self) -> OperatingMode:
        """Current operating mode."""
        try:
            result = self._client.read_parameter(STATUS_PARAMS["operating_mode"])
            value = int(result.get("decoded", 0))
            return OperatingMode(value)
        except (KeyError, ValueError):
            return OperatingMode.STANDBY

    @property
    def compressor_running(self) -> bool:
        """Whether compressor is currently running.

        Uses COMPRESSOR_REAL_FREQUENCY > 0 as the reliable indicator.
        Verified 2024-12-02: frequency shows actual Hz when running, 0 when stopped.
        """
        try:
            result = self._client.read_parameter(STATUS_PARAMS["compressor_frequency"])
            return int(result.get("decoded", 0)) > 0
        except KeyError:
            return False

    @property
    def compressor_frequency(self) -> int:
        """Current compressor frequency in Hz (0 = stopped)."""
        try:
            result = self._client.read_parameter(STATUS_PARAMS["compressor_frequency"])
            return int(result.get("decoded", 0))
        except KeyError:
            return 0

    @property
    def heating_season_mode(self) -> int:
        """Current heating season mode (0=Winter, 1=Auto, 2=Off)."""
        try:
            # HEATING_SEASON_MODE is idx 884
            result = self._client.read_parameter("HEATING_SEASON_MODE")
            return int(result.get("decoded", 1))
        except (KeyError, ValueError):
            return 1  # Default to Auto

    @property
    def dhw_program_mode(self) -> int:
        """Current DHW program mode (0=Auto, 1=On, 2=Off)."""
        try:
            # DHW_PROGRAM_MODE is idx 489
            result = self._client.read_parameter("DHW_PROGRAM_MODE")
            return int(result.get("decoded", 0))
        except (KeyError, ValueError):
            return 0  # Default to Auto

    @property
    def compressor_mode(self) -> str:
        """Current compressor mode: 'DHW', 'Heating', or 'Idle'.

        Based on COMPRESSOR_DHW_REQUEST and COMPRESSOR_HEATING_REQUEST parameters.
        """
        try:
            dhw_result = self._client.read_parameter(
                STATUS_PARAMS["compressor_dhw_request"]
            )
            dhw_active = int(dhw_result.get("decoded", 0)) > 0
            if dhw_active:
                return "DHW"
        except KeyError:
            pass

        try:
            heat_result = self._client.read_parameter(
                STATUS_PARAMS["compressor_heating_request"]
            )
            heat_active = int(heat_result.get("decoded", 0)) > 0
            if heat_active:
                return "Heating"
        except KeyError:
            pass

        return "Idle"

    @property
    def compressor_hours(self) -> int:
        """Total compressor run hours."""
        try:
            result = self._client.read_parameter(STATUS_PARAMS["compressor_hours"])
            return int(result.get("decoded", 0))
        except KeyError:
            return 0

    def read_all(self) -> StatusSnapshot:
        """
        Read all status values in a single operation.

        Performance: Designed to complete in <2 seconds (SC-001).

        Returns:
            StatusSnapshot with all current values
        """
        return StatusSnapshot(
            outdoor_temperature=self.outdoor_temperature,
            supply_temperature=self.supply_temperature,
            hot_water_temperature=self.hot_water_temperature,
            room_temperature=self.room_temperature,
            operating_mode=self.operating_mode,
            compressor_running=self.compressor_running,
            heating_season_mode=self.heating_season_mode,
            dhw_program_mode=self.dhw_program_mode,
        )


class HotWaterController:
    """Control DHW (hot water) settings and schedules."""

    def __init__(self, client: HeatPumpClient) -> None:
        self._client = client

    @property
    def temperature(self) -> float:
        """Current temperature setpoint (20-65°C)."""
        result = self._client.read_parameter(DHW_PARAMS["setpoint"])
        return float(result.get("decoded", 0))

    @temperature.setter
    def temperature(self, value: float) -> None:
        """Set DHW temperature setpoint.

        Args:
            value: Temperature in °C (human-readable, 45.0-65.0°C)
                   The encoder converts this to raw format internally.

        Raises:
            ValidationError: If value outside allowed range
        """
        if not 45.0 <= value <= 65.0:
            raise ValidationError(
                field="temperature",
                value=value,
                constraint="must be between 45 and 65 degrees",
                allowed_range=(45.0, 65.0),
            )
        # Pass human-readable °C value - encoder handles conversion to raw
        self._client.write_value(DHW_PARAMS["setpoint"], value)

    @property
    def extra_duration(self) -> int:
        """Extra hot water duration in minutes."""
        result = self._client.read_parameter(DHW_PARAMS["extra_duration"])
        return int(result.get("decoded", 0))

    @extra_duration.setter
    def extra_duration(self, value: int) -> None:
        """Set extra hot water duration."""
        self._client.write_value(DHW_PARAMS["extra_duration"], value)

    @property
    def stop_temperature(self) -> float:
        """Stop charging temperature."""
        result = self._client.read_parameter(DHW_PARAMS["stop_temp"])
        return float(result.get("decoded", 0))

    @stop_temperature.setter
    def stop_temperature(self, value: float) -> None:
        """Set DHW stop charging temperature.

        Args:
            value: Temperature in °C (human-readable, 45.0-65.0°C)
                   The encoder converts this to raw format internally.

        Raises:
            ValidationError: If value outside allowed range
        """
        if not 45.0 <= value <= 65.0:
            raise ValidationError(
                field="stop_temperature",
                value=value,
                constraint="must be between 45 and 65 degrees",
                allowed_range=(45.0, 65.0),
            )
        # Pass human-readable °C value - encoder handles conversion to raw
        self._client.write_value(DHW_PARAMS["stop_temp"], value)

    @property
    def program_mode(self) -> DHWProgramMode:
        """Current DHW program mode."""
        result = self._client.read_parameter(DHW_PARAMS["program_mode"])
        value = int(result.get("decoded", 0))
        return DHWProgramMode(value)

    @program_mode.setter
    def program_mode(self, value: DHWProgramMode) -> None:
        """Set DHW program mode."""
        self._client.write_value(DHW_PARAMS["program_mode"], value.value)

    def get_schedule(self, program: int) -> WeeklySchedule:
        """
        Get weekly schedule for program 1 or 2.

        Args:
            program: Program number (1 or 2)

        Returns:
            WeeklySchedule with all 7 days
        """
        if program not in (1, 2):
            raise ValueError("Program must be 1 or 2")

        prefix = f"schedule_p{program}_"
        slots = []

        for day in WEEKDAYS:
            param_idx = cast(int, DHW_PARAMS[f"{prefix}{day}"])
            # PROTOCOL: Use odd index (+1) for sw2 format to get both start and end times
            read_idx = ScheduleCodec.get_sw2_read_index(param_idx)
            raw = self._client.read_value(read_idx)
            slot = ScheduleCodec.decode(raw)
            slots.append(slot)

        return WeeklySchedule(*slots)

    def set_schedule(self, program: int, schedule: WeeklySchedule) -> None:
        """
        Set weekly schedule for program 1 or 2.

        Args:
            program: Program number (1 or 2)
            schedule: WeeklySchedule (times must be on 30-min boundaries)
        """
        if program not in (1, 2):
            raise ValueError("Program must be 1 or 2")

        # Validate all slots before writing
        for day_idx in range(7):
            slot = schedule.get_day(day_idx)
            slot.validate(resolution_minutes=30)

        prefix = f"schedule_p{program}_"

        for i, day in enumerate(WEEKDAYS):
            param_idx = cast(int, DHW_PARAMS[f"{prefix}{day}"])
            slot = schedule.get_day(i)
            encoded = ScheduleCodec.encode(slot)
            self._client.write_value(param_idx, encoded)


class Circuit:
    """Control settings for a heating circuit."""

    def __init__(self, client: HeatPumpClient, number: int) -> None:
        self._client = client
        self._number = number
        self._type = CircuitType.UNMIXED if number == 1 else CircuitType.MIXED

    @property
    def number(self) -> int:
        """Circuit number (1-4)."""
        return self._number

    @property
    def circuit_type(self) -> CircuitType:
        """Circuit type (unmixed or mixed)."""
        return self._type

    def _get_param(self, key: str) -> str:
        """Get parameter name for this circuit."""
        template = CIRCUIT_PARAMS.get(key, key)
        return get_circuit_param(template, self._number)

    @property
    def temperature(self) -> float:
        """Current supply temperature."""
        result = self._client.read_parameter(self._get_param("supply_temp"))
        return float(result.get("decoded", 0))

    @property
    def setpoint(self) -> float:
        """Target temperature setpoint."""
        result = self._client.read_parameter(self._get_param("setpoint"))
        return float(result.get("decoded", 0))

    @setpoint.setter
    def setpoint(self, value: float) -> None:
        """Set circuit target temperature setpoint.

        Args:
            value: Temperature in °C (human-readable, 5.0-30.0°C)
                   The encoder converts this to raw format internally.

        Raises:
            ValidationError: If value outside allowed range
        """
        if not 5.0 <= value <= 30.0:
            raise ValidationError(
                field="setpoint",
                value=value,
                constraint="must be between 5 and 30 degrees",
                allowed_range=(5.0, 30.0),
            )
        # Pass human-readable °C value - encoder handles conversion to raw
        self._client.write_value(self._get_param("setpoint"), value)

    @property
    def program_mode(self) -> RoomProgramMode:
        """Current room program mode."""
        result = self._client.read_parameter(self._get_param("program_mode"))
        value = int(result.get("decoded", 0))
        return RoomProgramMode(value)

    @program_mode.setter
    def program_mode(self, value: RoomProgramMode) -> None:
        """Set room program mode."""
        self._client.write_value(self._get_param("program_mode"), value.value)

    @property
    def summer_mode(self) -> bool:
        """Whether summer mode is active."""
        result = self._client.read_parameter(self._get_param("summer_mode"))
        return bool(result.get("decoded", 0))

    @property
    def summer_threshold(self) -> float:
        """Summer/winter switchover temperature."""
        result = self._client.read_parameter(self._get_param("summer_threshold"))
        return float(result.get("decoded", 0))

    def get_schedule(self, program: int) -> WeeklySchedule:
        """Get weekly schedule for program 1 or 2."""
        if program not in (1, 2):
            raise ValueError("Program must be 1 or 2")

        slots = []

        for day in WEEKDAYS:
            param = self._get_param(f"schedule_p{program}_{day}")
            # sw1 format: documented indices work directly
            raw = self._client.read_value(param)
            slot = ScheduleCodec.decode(raw)
            slots.append(slot)

        return WeeklySchedule(*slots)

    def set_schedule(self, program: int, schedule: WeeklySchedule) -> None:
        """Set weekly schedule for program 1 or 2."""
        if program not in (1, 2):
            raise ValueError("Program must be 1 or 2")

        for i, day in enumerate(WEEKDAYS):
            param = self._get_param(f"schedule_p{program}_{day}")
            slot = schedule.get_day(i)
            encoded = ScheduleCodec.encode(slot)
            self._client.write_value(param, encoded)

    @property
    def vacation(self) -> VacationPeriod:
        """Vacation mode settings for this circuit."""
        # Read vacation parameters for this circuit
        try:
            start_param = get_circuit_param(
                VACATION_PARAMS["circuit_start"], self._number
            )
            end_param = get_circuit_param(VACATION_PARAMS["circuit_end"], self._number)

            start_result = self._client.read_parameter(start_param)
            end_result = self._client.read_parameter(end_param)

            # If both dates are 0, vacation is not active
            start_val = start_result.get("decoded", 0)
            end_val = end_result.get("decoded", 0)

            if start_val == 0 and end_val == 0:
                return VacationPeriod(active=False)

            return VacationPeriod(
                active=True,
                start_date=self._decode_date(start_val),
                end_date=self._decode_date(end_val),
            )
        except KeyError:
            return VacationPeriod(active=False)

    def _decode_date(self, value: int) -> Optional[date]:
        """Decode date value from heat pump format."""
        if value == 0:
            return None
        # Date format TBD based on protocol
        return None


class EnergyView:
    """Read-only access to energy statistics."""

    def __init__(self, client: HeatPumpClient) -> None:
        self._client = client

    @property
    def heat_generated_kwh(self) -> float:
        """Total heat energy generated (kWh)."""
        result = self._client.read_parameter(ENERGY_PARAMS["heat_generated"])
        return float(result.get("decoded", 0))

    @property
    def aux_heater_kwh(self) -> float:
        """Auxiliary heater electricity consumption (kWh)."""
        result = self._client.read_parameter(ENERGY_PARAMS["aux_heater_kwh"])
        return float(result.get("decoded", 0))


class AlarmController:
    """Manage alarms and information logs."""

    def __init__(self, client: HeatPumpClient) -> None:
        self._client = client

    @property
    def active_alarms(self) -> list[Alarm]:
        """List of currently active alarms."""
        alarms = []
        for i in range(1, 6):
            try:
                result = self._client.read_parameter(ALARM_PARAMS[f"alarm_log_{i}"])
                alarm = self._parse_alarm(result, i)
                if alarm and not alarm.acknowledged:
                    alarms.append(alarm)
            except KeyError:
                continue
        return alarms

    @property
    def alarm_log(self) -> list[Alarm]:
        """Historical alarm log entries."""
        alarms = []
        for i in range(1, 6):
            try:
                result = self._client.read_parameter(ALARM_PARAMS[f"alarm_log_{i}"])
                alarm = self._parse_alarm(result, i)
                if alarm:
                    alarms.append(alarm)
            except KeyError:
                continue
        return alarms

    @property
    def info_log(self) -> list[Alarm]:
        """Information/warning log entries."""
        entries = []
        for i in range(1, 6):
            try:
                result = self._client.read_parameter(ALARM_PARAMS[f"info_log_{i}"])
                entry = self._parse_alarm(result, i, category=AlarmCategory.INFO)
                if entry:
                    entries.append(entry)
            except KeyError:
                continue
        return entries

    def _parse_alarm(
        self,
        result: dict[str, Any],
        index: int,
        category: AlarmCategory = AlarmCategory.ALARM,
    ) -> Optional[Alarm]:
        """Parse alarm data from parameter result."""
        decoded = result.get("decoded")
        if decoded is None or decoded == 0:
            return None

        # The decoded value is the alarm code itself (e.g., 5283)
        error_code = int(decoded)

        return Alarm(
            code=error_code,
            category=category,
            description=f"Error {error_code}",  # TODO: Map codes to text descriptions
            timestamp=datetime.now(),  # We don't get a timestamp from these params
            acknowledged=False,  # Status not available in this simple integer
            clearable=True,
        )

    def acknowledge(self, alarm: Alarm) -> None:
        """Acknowledge an active alarm."""
        self._client.write_value(ALARM_PARAMS["alarm_acknowledge"], alarm.code)

    def clear(self, alarm: Alarm) -> None:
        """Clear a resolved alarm."""
        if not alarm.clearable:
            raise AlarmNotClearableError(alarm.code)
        self._client.write_value(ALARM_PARAMS["alarm_clear"], alarm.code)


class VacationController:
    """Manage vacation mode settings."""

    def __init__(self, client: HeatPumpClient) -> None:
        self._client = client

    def get_circuit(self, circuit: int) -> VacationPeriod:
        """Get vacation settings for a circuit."""
        if not 1 <= circuit <= 4:
            raise CircuitNotAvailableError(circuit, [1, 2, 3, 4])

        try:
            start_param = get_circuit_param(VACATION_PARAMS["circuit_start"], circuit)
            end_param = get_circuit_param(VACATION_PARAMS["circuit_end"], circuit)

            start_result = self._client.read_parameter(start_param)
            end_result = self._client.read_parameter(end_param)

            start_val = start_result.get("decoded", 0)
            end_val = end_result.get("decoded", 0)

            if start_val == 0 and end_val == 0:
                return VacationPeriod(active=False)

            return VacationPeriod(active=True)
        except KeyError:
            return VacationPeriod(active=False)

    def set_circuit(self, circuit: int, period: VacationPeriod) -> None:
        """Set vacation period for a circuit."""
        if not 1 <= circuit <= 4:
            raise CircuitNotAvailableError(circuit, [1, 2, 3, 4])

        start_param = get_circuit_param(VACATION_PARAMS["circuit_start"], circuit)
        end_param = get_circuit_param(VACATION_PARAMS["circuit_end"], circuit)

        if period.active and period.start_date and period.end_date:
            # Encode dates (format TBD)
            start_val = self._encode_date(period.start_date)
            end_val = self._encode_date(period.end_date)
            self._client.write_value(start_param, start_val)
            self._client.write_value(end_param, end_val)
        else:
            # Clear vacation
            self._client.write_value(start_param, 0)
            self._client.write_value(end_param, 0)

    def clear_circuit(self, circuit: int) -> None:
        """Clear vacation mode for a circuit."""
        self.set_circuit(circuit, VacationPeriod(active=False))

    @property
    def hot_water(self) -> VacationPeriod:
        """DHW vacation settings."""
        try:
            start_result = self._client.read_parameter(VACATION_PARAMS["dhw_start"])
            end_result = self._client.read_parameter(VACATION_PARAMS["dhw_end"])

            start_val = start_result.get("decoded", 0)
            end_val = end_result.get("decoded", 0)

            if start_val == 0 and end_val == 0:
                return VacationPeriod(active=False)

            return VacationPeriod(active=True)
        except KeyError:
            return VacationPeriod(active=False)

    def set_hot_water(self, period: VacationPeriod) -> None:
        """Set vacation period for DHW."""
        if period.active and period.start_date and period.end_date:
            start_val = self._encode_date(period.start_date)
            end_val = self._encode_date(period.end_date)
            self._client.write_value(VACATION_PARAMS["dhw_start"], start_val)
            self._client.write_value(VACATION_PARAMS["dhw_end"], end_val)
        else:
            self._client.write_value(VACATION_PARAMS["dhw_start"], 0)
            self._client.write_value(VACATION_PARAMS["dhw_end"], 0)

    def clear_hot_water(self) -> None:
        """Clear vacation mode for DHW."""
        self.set_hot_water(VacationPeriod(active=False))

    def _encode_date(self, d: date) -> int:
        """Encode date to heat pump format."""
        # Date encoding format TBD based on protocol
        return 0


class MenuNavigator:
    """Navigate the menu hierarchy."""

    def __init__(self, client: HeatPumpClient) -> None:
        self._client = client
        self._root = MENU_ROOT
        self._current = MENU_ROOT
        self._path: list[str] = []

    @property
    def root(self) -> MenuItem:
        """Top-level menu item."""
        return self._root

    @property
    def current(self) -> MenuItem:
        """Currently selected menu item."""
        return self._current

    @property
    def path(self) -> list[str]:
        """Breadcrumb path to current item."""
        return self._path.copy()

    def navigate(self, path: str) -> MenuItem:
        """
        Navigate to a menu item by path.

        Args:
            path: Slash-separated path (e.g., "Hot Water/Temperature")

        Returns:
            The MenuItem at the specified path
        """
        parts = path.strip("/").split("/") if path else []
        current = self._root
        new_path: list[str] = []

        for part in parts:
            found = None
            for child in current.children:
                if child.name.lower() == part.lower():
                    found = child
                    break

            if found is None:
                available = [c.name for c in current.children]
                raise MenuNavigationError(path, available)

            current = found
            new_path.append(current.name)

        self._current = current
        self._path = new_path
        return current

    def up(self) -> MenuItem:
        """Go to parent menu item."""
        if not self._path:
            return self._current

        self._path.pop()
        if not self._path:
            self._current = self._root
        else:
            # Navigate back to parent
            parent_path = "/".join(self._path)
            self.navigate(parent_path)

        return self._current

    def items(self) -> list[MenuItem]:
        """List children of current menu item."""
        return self._current.children.copy()

    def get_value(self) -> Any:
        """Read value of current menu item."""
        if not self._current.parameter:
            raise ReadOnlyError(self._current.name)

        result = self._client.read_parameter(self._current.parameter)
        return result.get("decoded")

    def set_value(self, value: Any) -> None:
        """Write value to current menu item."""
        if not self._current.parameter:
            raise ReadOnlyError(self._current.name)

        if not self._current.writable:
            raise ReadOnlyError(self._current.parameter)

        # Validate against range if specified
        if self._current.value_range:
            min_val, max_val = self._current.value_range
            if not min_val <= value <= max_val:
                raise ValidationError(
                    field=self._current.name,
                    value=value,
                    constraint=f"must be between {min_val} and {max_val}",
                    allowed_range=self._current.value_range,
                )

        self._client.write_value(self._current.parameter, value)


# =============================================================================
# Main API Class
# =============================================================================


class MenuAPI:
    """
    High-level menu-style API for Buderus WPS heat pump.

    This class provides intuitive access to heat pump functions organized
    like the physical display menu structure.

    Usage:
        >>> from buderus_wps import USBtinAdapter, HeatPumpClient, MenuAPI
        >>> adapter = USBtinAdapter('/dev/ttyACM0')
        >>> adapter.connect()
        >>> client = HeatPumpClient(adapter)
        >>> api = MenuAPI(client)
        >>> print(f"Outdoor: {api.status.outdoor_temperature}°C")
    """

    def __init__(self, client: HeatPumpClient) -> None:
        """
        Initialize Menu API.

        Args:
            client: HeatPumpClient instance for CAN communication
        """
        self._client = client
        self._status = StatusView(client)
        self._hot_water = HotWaterController(client)
        self._circuits: dict[int, Circuit] = {}
        self._energy = EnergyView(client)
        self._alarms = AlarmController(client)
        self._vacation = VacationController(client)
        self._menu = MenuNavigator(client)

    @property
    def status(self) -> StatusView:
        """Read-only status and temperature access."""
        return self._status

    @property
    def hot_water(self) -> HotWaterController:
        """DHW settings and schedules."""
        return self._hot_water

    def get_circuit(self, number: int) -> Circuit:
        """
        Get controller for a heating circuit.

        Args:
            number: Circuit number (1-4)

        Returns:
            Circuit controller

        Raises:
            CircuitNotAvailableError: If circuit number invalid
        """
        if not 1 <= number <= 4:
            raise CircuitNotAvailableError(number, [1, 2, 3, 4])

        if number not in self._circuits:
            self._circuits[number] = Circuit(self._client, number)

        return self._circuits[number]

    @property
    def energy(self) -> EnergyView:
        """Read-only energy statistics."""
        return self._energy

    @property
    def alarms(self) -> AlarmController:
        """Alarm management."""
        return self._alarms

    @property
    def vacation(self) -> VacationController:
        """Vacation mode management."""
        return self._vacation

    @property
    def menu(self) -> MenuNavigator:
        """Hierarchical menu navigation."""
        return self._menu
