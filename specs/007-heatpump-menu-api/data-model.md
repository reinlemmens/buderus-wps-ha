# Data Model: Heat Pump Menu API

**Feature**: 007-heatpump-menu-api | **Phase**: 1 | **Date**: 2025-11-28

## Core Classes

### MenuAPI

The main entry point providing menu-style access to heat pump functions.

```
MenuAPI
├── client: HeatPumpClient          # Underlying CAN client
├── status: StatusView              # Read-only status/temperatures
├── hot_water: HotWaterController   # DHW settings and schedules
├── circuits: Dict[int, Circuit]    # Heating circuits 1-4
├── energy: EnergyView              # Energy statistics (read-only)
├── alarms: AlarmController         # Alarm log and management
├── vacation: VacationController    # Vacation mode settings
└── menu: MenuNavigator             # Hierarchical menu access
```

### StatusView (Read-Only)

```
StatusView
├── outdoor_temperature: float      # Outdoor sensor (°C)
├── supply_temperature: float       # Supply line (°C)
├── hot_water_temperature: float    # DHW tank (°C)
├── room_temperature: float         # Room sensor (°C, if available)
├── operating_mode: OperatingMode   # HEATING, COOLING, DHW, STANDBY
├── compressor_running: bool        # Compressor on/off
├── compressor_hours: int           # Total run hours
└── read_all() -> StatusSnapshot    # Read all in single operation
```

### HotWaterController

```
HotWaterController
├── temperature: float              # Current setpoint (20-65°C)
├── extra_duration: int             # Extra hot water minutes
├── stop_temperature: float         # Stop charging temperature
├── program_mode: DHWProgramMode    # ALWAYS_ON, PROGRAM_1, PROGRAM_2
├── get_schedule(program: int) -> WeeklySchedule
├── set_schedule(program: int, schedule: WeeklySchedule)
└── vacation: VacationPeriod        # DHW vacation settings
```

### Circuit

```
Circuit
├── number: int                     # 1-4
├── type: CircuitType               # UNMIXED (1) or MIXED (2-4)
├── temperature: float              # Current supply temperature
├── setpoint: float                 # Target temperature
├── program_mode: RoomProgramMode   # HP_OPTIMIZED, PROGRAM_1, etc.
├── summer_mode: bool               # Summer/winter mode
├── summer_threshold: float         # Switchover temperature
├── get_schedule(program: int) -> WeeklySchedule
├── set_schedule(program: int, schedule: WeeklySchedule)
└── vacation: VacationPeriod        # Circuit vacation settings
```

### WeeklySchedule

```
WeeklySchedule
├── monday: ScheduleSlot
├── tuesday: ScheduleSlot
├── wednesday: ScheduleSlot
├── thursday: ScheduleSlot
├── friday: ScheduleSlot
├── saturday: ScheduleSlot
├── sunday: ScheduleSlot
└── get_day(day: int) -> ScheduleSlot  # 0=Monday, 6=Sunday
```

### ScheduleSlot

```
ScheduleSlot
├── start_time: time               # Start of active period (HH:MM)
├── end_time: time                 # End of active period (HH:MM)
├── is_active(at: time) -> bool    # Check if time is within slot
└── validate(resolution: int)       # Check 30-min boundary (DHW)
```

### VacationPeriod

```
VacationPeriod
├── active: bool                    # Currently in vacation mode
├── start_date: date | None         # Vacation start
├── end_date: date | None           # Vacation end
├── reduced_setpoint: float | None  # Temperature during vacation
└── clear()                         # Cancel vacation mode
```

### AlarmController

```
AlarmController
├── active_alarms: List[Alarm]      # Currently active alarms
├── alarm_log: List[AlarmEntry]     # Historical alarm log
├── info_log: List[InfoEntry]       # Information/warning log
├── acknowledge(alarm: Alarm)       # Mark alarm as acknowledged
└── clear(alarm: Alarm)             # Clear resolved alarm
```

### Alarm / AlarmEntry

```
Alarm
├── code: int                       # Alarm code number
├── category: AlarmCategory         # WARNING, ALARM
├── description: str                # Human-readable description
├── timestamp: datetime             # When occurred
├── acknowledged: bool              # Has been acknowledged
└── clearable: bool                 # Can be cleared via API
```

### MenuNavigator

```
MenuNavigator
├── root: MenuItem                  # Top-level menu
├── current: MenuItem               # Current position
├── path: List[str]                 # Breadcrumb path
├── navigate(path: str) -> MenuItem # Navigate by path
├── up() -> MenuItem                # Go to parent
├── items() -> List[MenuItem]       # List children
└── get_value() -> Any              # Read current item value
```

### MenuItem

```
MenuItem
├── name: str                       # Display name
├── description: str                # Help text
├── children: List[MenuItem]        # Sub-menu items
├── parameter: Parameter | None     # Linked parameter (leaf nodes)
├── readable: bool                  # Can read value
├── writable: bool                  # Can write value
├── value_range: Tuple[Any, Any]    # Min/max if applicable
└── get_value() -> Any              # Read current value
```

## Enumerations

### OperatingMode
```
STANDBY = 0
HEATING = 1
COOLING = 2
DHW_PRIORITY = 3
DEFROST = 4
```

### RoomProgramMode
```
HP_OPTIMIZED = 0
PROGRAM_1 = 1
PROGRAM_2 = 2
FAMILY = 3
MORNING = 4
EVENING = 5
SENIORS = 6
```

### DHWProgramMode
```
ALWAYS_ON = 0
PROGRAM_1 = 1
PROGRAM_2 = 2
```

### CircuitType
```
UNMIXED = 1      # Primary circuit (circuit 1)
MIXED = 2        # Secondary circuits (2-4) with mixing valve
```

### AlarmCategory
```
INFO = 0         # Informational message
WARNING = 1      # Warning condition
ALARM = 2        # Critical alarm
```

## Validation Rules

| Entity | Field | Rule |
|--------|-------|------|
| HotWaterController | temperature | 20.0 <= value <= 65.0 |
| ScheduleSlot | start_time | Must be on 30-min boundary for DHW |
| ScheduleSlot | end_time | Must be on 30-min boundary for DHW |
| ScheduleSlot | times | start_time < end_time |
| VacationPeriod | dates | start_date <= end_date |
| Circuit | number | 1 <= value <= 4 |
| AlarmController | clear() | Only if alarm.clearable == True |

## Parameter Mapping Examples

| API Path | Parameter Name | Format |
|----------|----------------|--------|
| status.outdoor_temperature | OUTDOOR_TEMP | temp |
| status.supply_temperature | SUPPLY_TEMP | temp |
| hot_water.temperature | DHW_SETTEMP | temp |
| hot_water.schedule[1].monday | DHW_TIMER_P1_MONDAY (+1) | sw2 |
| circuits[1].program_mode | ROOM_PROGRAM_MODE_C1 | rp0 |
| circuits[1].schedule[1].monday | ROOM_TIMER_P1_MONDAY_C1 | sw1 |
| vacation.circuits[1].start_date | VACATION_START_C1 | date |
| alarms.alarm_log[0] | ALARM_LOG_1 | alarm |
