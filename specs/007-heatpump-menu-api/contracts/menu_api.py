"""
API Contract: MenuAPI

This file defines the public interface for the Heat Pump Menu API.
It serves as the contract between the API and its consumers.

Note: This is a design document, not implementation code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import time, date, datetime
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any


# === Enumerations ===

class OperatingMode(Enum):
    """Heat pump operating states."""
    STANDBY = 0
    HEATING = 1
    COOLING = 2
    DHW_PRIORITY = 3
    DEFROST = 4


class RoomProgramMode(Enum):
    """Room heating program modes."""
    HP_OPTIMIZED = 0
    PROGRAM_1 = 1
    PROGRAM_2 = 2
    FAMILY = 3
    MORNING = 4
    EVENING = 5
    SENIORS = 6


class DHWProgramMode(Enum):
    """DHW (hot water) program modes."""
    ALWAYS_ON = 0
    PROGRAM_1 = 1
    PROGRAM_2 = 2


class CircuitType(Enum):
    """Heating circuit types."""
    UNMIXED = auto()  # Primary circuit (circuit 1)
    MIXED = auto()    # Secondary circuits (2-4) with mixing valve


class AlarmCategory(Enum):
    """Alarm severity categories."""
    INFO = 0
    WARNING = 1
    ALARM = 2


# === Data Classes ===

@dataclass
class ScheduleSlot:
    """A time period within a daily schedule."""
    start_time: time  # Start of active period
    end_time: time    # End of active period

    def is_active(self, at: time) -> bool:
        """Check if the given time falls within this slot."""
        ...

    def validate(self, resolution_minutes: int = 30) -> None:
        """
        Validate time boundaries.

        Raises:
            ValidationError: If times don't align with resolution
        """
        ...


@dataclass
class WeeklySchedule:
    """A complete weekly schedule with slots for each day."""
    monday: ScheduleSlot
    tuesday: ScheduleSlot
    wednesday: ScheduleSlot
    thursday: ScheduleSlot
    friday: ScheduleSlot
    saturday: ScheduleSlot
    sunday: ScheduleSlot

    def get_day(self, day: int) -> ScheduleSlot:
        """Get schedule for day (0=Monday, 6=Sunday)."""
        ...


@dataclass
class VacationPeriod:
    """Vacation mode configuration."""
    active: bool
    start_date: Optional[date]
    end_date: Optional[date]
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


@dataclass
class StatusSnapshot:
    """Complete status reading from a single operation."""
    outdoor_temperature: float
    supply_temperature: float
    hot_water_temperature: float
    room_temperature: Optional[float]
    operating_mode: OperatingMode
    compressor_running: bool


@dataclass
class MenuItem:
    """A node in the menu hierarchy."""
    name: str
    description: str
    readable: bool
    writable: bool
    value_range: Optional[Tuple[Any, Any]]
    children: List['MenuItem']


# === Abstract Interfaces ===

class StatusView(ABC):
    """Read-only access to heat pump status and temperatures."""

    @property
    @abstractmethod
    def outdoor_temperature(self) -> float:
        """Outdoor temperature in degrees Celsius."""
        ...

    @property
    @abstractmethod
    def supply_temperature(self) -> float:
        """Supply line temperature in degrees Celsius."""
        ...

    @property
    @abstractmethod
    def hot_water_temperature(self) -> float:
        """DHW tank temperature in degrees Celsius."""
        ...

    @property
    @abstractmethod
    def room_temperature(self) -> Optional[float]:
        """Room temperature if sensor available, else None."""
        ...

    @property
    @abstractmethod
    def operating_mode(self) -> OperatingMode:
        """Current operating mode."""
        ...

    @property
    @abstractmethod
    def compressor_running(self) -> bool:
        """Whether compressor is currently running."""
        ...

    @property
    @abstractmethod
    def compressor_hours(self) -> int:
        """Total compressor run hours."""
        ...

    @abstractmethod
    def read_all(self) -> StatusSnapshot:
        """
        Read all status values in a single operation.

        Performance: Must complete in <2 seconds (SC-001).

        Returns:
            StatusSnapshot with all current values
        """
        ...


class HotWaterController(ABC):
    """Control DHW (hot water) settings and schedules."""

    @property
    @abstractmethod
    def temperature(self) -> float:
        """Current temperature setpoint (20-65°C)."""
        ...

    @temperature.setter
    @abstractmethod
    def temperature(self, value: float) -> None:
        """
        Set temperature setpoint.

        Args:
            value: Temperature in degrees (20-65)

        Raises:
            ValidationError: If value outside 20-65 range
        """
        ...

    @property
    @abstractmethod
    def extra_duration(self) -> int:
        """Extra hot water duration in minutes."""
        ...

    @property
    @abstractmethod
    def stop_temperature(self) -> float:
        """Stop charging temperature."""
        ...

    @property
    @abstractmethod
    def program_mode(self) -> DHWProgramMode:
        """Current DHW program mode."""
        ...

    @program_mode.setter
    @abstractmethod
    def program_mode(self, value: DHWProgramMode) -> None:
        """Set DHW program mode."""
        ...

    @abstractmethod
    def get_schedule(self, program: int) -> WeeklySchedule:
        """
        Get weekly schedule for program 1 or 2.

        Args:
            program: Program number (1 or 2)

        Returns:
            WeeklySchedule with all 7 days
        """
        ...

    @abstractmethod
    def set_schedule(self, program: int, schedule: WeeklySchedule) -> None:
        """
        Set weekly schedule for program 1 or 2.

        Args:
            program: Program number (1 or 2)
            schedule: WeeklySchedule to set (times must be on 30-min boundaries)

        Raises:
            ValidationError: If times not on 30-minute boundaries
        """
        ...


class Circuit(ABC):
    """Control settings for a heating circuit."""

    @property
    @abstractmethod
    def number(self) -> int:
        """Circuit number (1-4)."""
        ...

    @property
    @abstractmethod
    def circuit_type(self) -> CircuitType:
        """Circuit type (unmixed or mixed)."""
        ...

    @property
    @abstractmethod
    def temperature(self) -> float:
        """Current supply temperature."""
        ...

    @property
    @abstractmethod
    def setpoint(self) -> float:
        """Target temperature setpoint."""
        ...

    @setpoint.setter
    @abstractmethod
    def setpoint(self, value: float) -> None:
        """Set target temperature."""
        ...

    @property
    @abstractmethod
    def program_mode(self) -> RoomProgramMode:
        """Current room program mode."""
        ...

    @program_mode.setter
    @abstractmethod
    def program_mode(self, value: RoomProgramMode) -> None:
        """Set room program mode."""
        ...

    @property
    @abstractmethod
    def summer_mode(self) -> bool:
        """Whether summer mode is active."""
        ...

    @property
    @abstractmethod
    def summer_threshold(self) -> float:
        """Summer/winter switchover temperature."""
        ...

    @abstractmethod
    def get_schedule(self, program: int) -> WeeklySchedule:
        """Get weekly schedule for program 1 or 2."""
        ...

    @abstractmethod
    def set_schedule(self, program: int, schedule: WeeklySchedule) -> None:
        """Set weekly schedule for program 1 or 2."""
        ...

    @property
    @abstractmethod
    def vacation(self) -> VacationPeriod:
        """Vacation mode settings for this circuit."""
        ...


class EnergyView(ABC):
    """Read-only access to energy statistics."""

    @property
    @abstractmethod
    def heat_generated_kwh(self) -> float:
        """Total heat energy generated (kWh)."""
        ...

    @property
    @abstractmethod
    def aux_heater_kwh(self) -> float:
        """Auxiliary heater electricity consumption (kWh)."""
        ...


class AlarmController(ABC):
    """Manage alarms and information logs."""

    @property
    @abstractmethod
    def active_alarms(self) -> List[Alarm]:
        """List of currently active alarms."""
        ...

    @property
    @abstractmethod
    def alarm_log(self) -> List[Alarm]:
        """Historical alarm log entries."""
        ...

    @property
    @abstractmethod
    def info_log(self) -> List[Alarm]:
        """Information/warning log entries."""
        ...

    @abstractmethod
    def acknowledge(self, alarm: Alarm) -> None:
        """
        Acknowledge an active alarm.

        Args:
            alarm: The alarm to acknowledge
        """
        ...

    @abstractmethod
    def clear(self, alarm: Alarm) -> None:
        """
        Clear a resolved alarm.

        Args:
            alarm: The alarm to clear

        Raises:
            ValidationError: If alarm is not clearable
        """
        ...


class VacationController(ABC):
    """Manage vacation mode settings."""

    @abstractmethod
    def get_circuit(self, circuit: int) -> VacationPeriod:
        """Get vacation settings for a circuit."""
        ...

    @abstractmethod
    def set_circuit(self, circuit: int, period: VacationPeriod) -> None:
        """Set vacation period for a circuit."""
        ...

    @abstractmethod
    def clear_circuit(self, circuit: int) -> None:
        """Clear vacation mode for a circuit."""
        ...

    @property
    @abstractmethod
    def hot_water(self) -> VacationPeriod:
        """DHW vacation settings."""
        ...

    @abstractmethod
    def set_hot_water(self, period: VacationPeriod) -> None:
        """Set vacation period for DHW."""
        ...

    @abstractmethod
    def clear_hot_water(self) -> None:
        """Clear vacation mode for DHW."""
        ...


class MenuNavigator(ABC):
    """Navigate the menu hierarchy."""

    @property
    @abstractmethod
    def root(self) -> MenuItem:
        """Top-level menu item."""
        ...

    @property
    @abstractmethod
    def current(self) -> MenuItem:
        """Currently selected menu item."""
        ...

    @property
    @abstractmethod
    def path(self) -> List[str]:
        """Breadcrumb path to current item."""
        ...

    @abstractmethod
    def navigate(self, path: str) -> MenuItem:
        """
        Navigate to a menu item by path.

        Args:
            path: Slash-separated path (e.g., "Hot Water/Temperature")

        Returns:
            The MenuItem at the specified path

        Raises:
            KeyError: If path does not exist
        """
        ...

    @abstractmethod
    def up(self) -> MenuItem:
        """Go to parent menu item."""
        ...

    @abstractmethod
    def items(self) -> List[MenuItem]:
        """List children of current menu item."""
        ...

    @abstractmethod
    def get_value(self) -> Any:
        """
        Read value of current menu item.

        Raises:
            PermissionError: If item is not readable
        """
        ...

    @abstractmethod
    def set_value(self, value: Any) -> None:
        """
        Write value to current menu item.

        Raises:
            PermissionError: If item is not writable
            ValidationError: If value out of range
        """
        ...


# === Main API Class ===

class MenuAPI(ABC):
    """
    High-level menu-style API for Buderus WPS heat pump.

    Usage:
        from buderus_wps import USBtinAdapter, HeatPumpClient, MenuAPI

        adapter = USBtinAdapter('/dev/ttyACM0')
        adapter.connect()
        client = HeatPumpClient(adapter)
        api = MenuAPI(client)

        # Read status
        print(f"Outdoor: {api.status.outdoor_temperature}°C")

        # Modify DHW temperature
        api.hot_water.temperature = 55.0

        # Read schedule
        schedule = api.hot_water.get_schedule(1)
        print(f"Monday: {schedule.monday.start_time}-{schedule.monday.end_time}")
    """

    @property
    @abstractmethod
    def status(self) -> StatusView:
        """Read-only status and temperature access."""
        ...

    @property
    @abstractmethod
    def hot_water(self) -> HotWaterController:
        """DHW settings and schedules."""
        ...

    @abstractmethod
    def get_circuit(self, number: int) -> Circuit:
        """
        Get controller for a heating circuit.

        Args:
            number: Circuit number (1-4)

        Returns:
            Circuit controller

        Raises:
            ValueError: If circuit number invalid
        """
        ...

    @property
    @abstractmethod
    def energy(self) -> EnergyView:
        """Read-only energy statistics."""
        ...

    @property
    @abstractmethod
    def alarms(self) -> AlarmController:
        """Alarm management."""
        ...

    @property
    @abstractmethod
    def vacation(self) -> VacationController:
        """Vacation mode management."""
        ...

    @property
    @abstractmethod
    def menu(self) -> MenuNavigator:
        """Hierarchical menu navigation."""
        ...
