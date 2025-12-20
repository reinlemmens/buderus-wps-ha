"""
Menu hierarchy definition for Heat Pump Menu API.

This module defines the menu structure that mirrors the physical
heat pump display, mapping menu paths to parameter names.

Menu Structure (from user manual Table 3):
- Status (temperatures, operating state)
- Hot Water (DHW settings, schedules)
- Program Mode (circuit program modes)
- Programs (weekly schedules)
- Compressor (status, run hours)
- Vacation (vacation mode settings)
- Energy (heat generated, aux heater)
- Alarms (alarm log, info log)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


@dataclass
class MenuItem:
    """
    A node in the menu hierarchy.

    Attributes:
        name: Display name (matches user manual)
        description: Help text explaining the setting
        parameter: Linked parameter name (for leaf nodes), None for categories
        readable: Whether the value can be read
        writable: Whether the value can be written
        value_range: (min, max) tuple if applicable
        children: Sub-menu items (empty for leaf nodes)
        format: Value format hint (temp, time, enum, etc.)
    """

    name: str
    description: str = ""
    parameter: Optional[str] = None
    readable: bool = True
    writable: bool = False
    value_range: Optional[Tuple[Any, Any]] = None
    children: List[MenuItem] = field(default_factory=list)
    format: Optional[str] = None


# =============================================================================
# Parameter Mappings
# Maps API paths to actual parameter names from the registry
# =============================================================================

# Status/Temperature Parameters
# GT sensor mapping (from FHEM/IVT documentation):
#   GT1 = Brine inlet, GT2 = Outdoor, GT3 = DHW tank
#   GT5 = Evaporator, GT6 = Compressor, GT8 = Supply, GT9 = Return
STATUS_PARAMS = {
    "outdoor_temp": "GT2_TEMP",
    "supply_temp": "GT8_TEMP",
    "return_temp": "GT9_TEMP",
    "dhw_temp": "GT3_TEMP",
    "room_temp": "ROOM_TEMP_C1",
    "operating_mode": "DRIFTTILLSTAND",
    "compressor_status": "COMPRESSOR_STATE",
    "compressor_hours": "COMPRESSOR_OPERATING_HOURS",
    # Compressor running detection (verified 2024-12-02):
    # - COMPRESSOR_REAL_FREQUENCY > 0 means compressor is running
    # - COMPRESSOR_DHW_REQUEST > 0 means DHW mode requested
    # - COMPRESSOR_HEATING_REQUEST > 0 means heating mode requested
    "compressor_frequency": "COMPRESSOR_REAL_FREQUENCY",
    "compressor_dhw_request": "COMPRESSOR_DHW_REQUEST",
    "compressor_heating_request": "COMPRESSOR_HEATING_REQUEST",
}

# DHW (Hot Water) Parameters
DHW_PARAMS = {
    "setpoint": "DHW_SETPOINT",
    "stop_temp": "XDHW_STOP_TEMP",  # Corrected from DHW_STOP_TEMP
    "extra_duration": "XDHW_TIME",  # Corrected from DHW_EXTRA_DURATION
    "program_mode": "DHW_PROGRAM_MODE",
    # Schedule parameters (sw2 format - use odd indices for full data)
    "schedule_p1_monday": 460,  # Documented index; use +1 for reading
    "schedule_p1_tuesday": 462,
    "schedule_p1_wednesday": 464,
    "schedule_p1_thursday": 466,
    "schedule_p1_friday": 468,
    "schedule_p1_saturday": 470,
    "schedule_p1_sunday": 472,
    "schedule_p2_monday": 474,
    "schedule_p2_tuesday": 476,
    "schedule_p2_wednesday": 478,
    "schedule_p2_thursday": 480,
    "schedule_p2_friday": 482,
    "schedule_p2_saturday": 484,
    "schedule_p2_sunday": 486,
}

# Circuit Parameters (template - replace C? with circuit number)
CIRCUIT_PARAMS = {
    "room_temp": "ROOM_TEMP_C{n}",
    "supply_temp": "SUPPLY_TEMP_C{n}",
    "setpoint": "ROOM_SETPOINT_C{n}",
    "program_mode": "ROOM_PROGRAM_MODE_C{n}",
    "summer_mode": "SUMMER_MODE_C{n}",
    "summer_threshold": "SUMMER_THRESHOLD_C{n}",
    # Room schedule parameters (sw1 format - documented indices work)
    "schedule_p1_monday": "ROOM_TIMER_P1_MONDAY_C{n}",
    "schedule_p1_tuesday": "ROOM_TIMER_P1_TUESDAY_C{n}",
    "schedule_p1_wednesday": "ROOM_TIMER_P1_WEDNESDAY_C{n}",
    "schedule_p1_thursday": "ROOM_TIMER_P1_THURSDAY_C{n}",
    "schedule_p1_friday": "ROOM_TIMER_P1_FRIDAY_C{n}",
    "schedule_p1_saturday": "ROOM_TIMER_P1_SATURDAY_C{n}",
    "schedule_p1_sunday": "ROOM_TIMER_P1_SUNDAY_C{n}",
}

# Vacation Parameters
VACATION_PARAMS = {
    "circuit_start": "VACATION_START_C{n}",
    "circuit_end": "VACATION_END_C{n}",
    "circuit_setpoint": "VACATION_SETPOINT_C{n}",
    "dhw_start": "VACATION_DHW_START",
    "dhw_end": "VACATION_DHW_END",
}

# Energy Parameters
ENERGY_PARAMS = {
    "heat_generated": "HEAT_GENERATED_TOTAL",
    "heat_generated_24h": "HEAT_GENERATED_24H",
    "aux_heater_kwh": "AUX_HEATER_ENERGY",
    "aux_heater_hours": "AUX_HEATER_HOURS",
}

# Alarm Parameters
ALARM_PARAMS = {
    "alarm_log_1": "ALARM_LOG_1",
    "alarm_log_2": "ALARM_LOG_2",
    "alarm_log_3": "ALARM_LOG_3",
    "alarm_log_4": "ALARM_LOG_4",
    "alarm_log_5": "ALARM_LOG_5",
    "info_log_1": "INFO_LOG_1",
    "info_log_2": "INFO_LOG_2",
    "info_log_3": "INFO_LOG_3",
    "info_log_4": "INFO_LOG_4",
    "info_log_5": "INFO_LOG_5",
    "alarm_acknowledge": "ALARM_ACKNOWLEDGE",
    "alarm_clear": "ALARM_CLEAR",
}


def get_circuit_param(param_template: str, circuit: int) -> str:
    """
    Get parameter name for a specific circuit.

    Args:
        param_template: Template with {n} placeholder
        circuit: Circuit number (1-4)

    Returns:
        Parameter name with circuit number substituted
    """
    return param_template.format(n=circuit)


# =============================================================================
# Menu Hierarchy Definition
# =============================================================================


def build_menu_tree() -> MenuItem:
    """
    Build the complete menu hierarchy tree.

    Returns:
        Root MenuItem with complete hierarchy
    """
    return MenuItem(
        name="Root",
        description="Heat Pump Menu",
        children=[
            MenuItem(
                name="Status",
                description="Current temperatures and operating state",
                children=[
                    MenuItem(
                        name="Outdoor Temperature",
                        description="Current outdoor temperature",
                        parameter=STATUS_PARAMS["outdoor_temp"],
                        format="temp",
                    ),
                    MenuItem(
                        name="Supply Temperature",
                        description="Heat pump supply line temperature",
                        parameter=STATUS_PARAMS["supply_temp"],
                        format="temp",
                    ),
                    MenuItem(
                        name="Hot Water Temperature",
                        description="DHW tank temperature",
                        parameter=STATUS_PARAMS["dhw_temp"],
                        format="temp",
                    ),
                    MenuItem(
                        name="Room Temperature",
                        description="Room temperature (if sensor available)",
                        parameter=STATUS_PARAMS["room_temp"],
                        format="temp",
                    ),
                    MenuItem(
                        name="Operating Mode",
                        description="Current operating state (Heating/Cooling/DHW/Standby)",
                        parameter=STATUS_PARAMS["operating_mode"],
                        format="enum",
                    ),
                    MenuItem(
                        name="Compressor",
                        description="Compressor status and run hours",
                        parameter=STATUS_PARAMS["compressor_status"],
                        format="enum",
                    ),
                ],
            ),
            MenuItem(
                name="Hot Water",
                description="Domestic hot water settings",
                children=[
                    MenuItem(
                        name="Temperature",
                        description="DHW setpoint temperature (20-65°C)",
                        parameter=str(DHW_PARAMS["setpoint"]),
                        readable=True,
                        writable=True,
                        value_range=(20, 65),
                        format="temp",
                    ),
                    MenuItem(
                        name="Stop Temperature",
                        description="Temperature to stop DHW charging",
                        parameter=str(DHW_PARAMS["stop_temp"]),
                        readable=True,
                        writable=True,
                        format="temp",
                    ),
                    MenuItem(
                        name="Extra Duration",
                        description="Extra hot water duration (minutes)",
                        parameter=str(DHW_PARAMS["extra_duration"]),
                        readable=True,
                        writable=True,
                        format="minutes",
                    ),
                    MenuItem(
                        name="Program Mode",
                        description="DHW program selection (Always On/Program 1/Program 2)",
                        parameter=str(DHW_PARAMS["program_mode"]),
                        readable=True,
                        writable=True,
                        format="enum",
                    ),
                ],
            ),
            MenuItem(
                name="Programs",
                description="Weekly heating and DHW schedules",
                children=[
                    MenuItem(
                        name="DHW Schedule",
                        description="Hot water weekly schedule",
                        children=[
                            MenuItem(
                                name="Program 1",
                                description="DHW Schedule Program 1",
                            ),
                            MenuItem(
                                name="Program 2",
                                description="DHW Schedule Program 2",
                            ),
                        ],
                    ),
                    MenuItem(
                        name="Room Schedule",
                        description="Room heating weekly schedule",
                        children=[
                            MenuItem(
                                name="Circuit 1",
                                description="Room Schedule Circuit 1",
                            ),
                            MenuItem(
                                name="Circuit 2",
                                description="Room Schedule Circuit 2",
                            ),
                            MenuItem(
                                name="Circuit 3",
                                description="Room Schedule Circuit 3",
                            ),
                            MenuItem(
                                name="Circuit 4",
                                description="Room Schedule Circuit 4",
                            ),
                        ],
                    ),
                ],
            ),
            MenuItem(
                name="Vacation",
                description="Vacation mode settings",
                children=[
                    MenuItem(
                        name="Circuit 1",
                        description="Vacation mode for heating circuit 1",
                    ),
                    MenuItem(
                        name="Circuit 2",
                        description="Vacation mode for heating circuit 2",
                    ),
                    MenuItem(
                        name="Circuit 3",
                        description="Vacation mode for heating circuit 3",
                    ),
                    MenuItem(
                        name="Circuit 4",
                        description="Vacation mode for heating circuit 4",
                    ),
                    MenuItem(
                        name="Hot Water",
                        description="Vacation mode for DHW",
                    ),
                ],
            ),
            MenuItem(
                name="Energy",
                description="Energy statistics",
                children=[
                    MenuItem(
                        name="Heat Generated",
                        description="Total heat energy generated (kWh)",
                        parameter=ENERGY_PARAMS["heat_generated"],
                        format="kwh",
                    ),
                    MenuItem(
                        name="Aux Heater",
                        description="Auxiliary heater energy consumption (kWh)",
                        parameter=ENERGY_PARAMS["aux_heater_kwh"],
                        format="kwh",
                    ),
                ],
            ),
            MenuItem(
                name="Alarms",
                description="Alarm and information logs",
                children=[
                    MenuItem(
                        name="Alarm Log",
                        description="Historical alarm entries",
                    ),
                    MenuItem(
                        name="Info Log",
                        description="Information and warning entries",
                    ),
                ],
            ),
        ],
    )


# Build the menu tree once at module load
MENU_ROOT = build_menu_tree()
