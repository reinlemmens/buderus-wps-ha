# Quickstart: Heat Pump Menu API

**Feature**: 007-heatpump-menu-api | **Date**: 2025-11-28

## Installation

The Menu API is part of the `buderus_wps` library:

```python
from buderus_wps import USBtinAdapter, HeatPumpClient, MenuAPI
```

## Basic Usage

### Connect and Create API

```python
from buderus_wps import USBtinAdapter, HeatPumpClient, MenuAPI

# Connect to heat pump
adapter = USBtinAdapter('/dev/ttyACM0', baudrate=115200, timeout=5.0)
adapter.connect()

# Create client and API
client = HeatPumpClient(adapter)
api = MenuAPI(client)
```

### Read Status (User Story 1)

```python
# Read individual temperatures
print(f"Outdoor: {api.status.outdoor_temperature}°C")
print(f"Supply: {api.status.supply_temperature}°C")
print(f"Hot Water: {api.status.hot_water_temperature}°C")
print(f"Room: {api.status.room_temperature}°C")

# Read operating mode
print(f"Mode: {api.status.operating_mode.name}")
print(f"Compressor: {'Running' if api.status.compressor_running else 'Off'}")

# Read all status in single operation (<2 seconds)
snapshot = api.status.read_all()
```

### Navigate Menu (User Story 2)

```python
# List top-level menu items
for item in api.menu.items():
    print(f"{item.name}: {item.description}")

# Navigate to a specific item
hot_water_menu = api.menu.navigate("Hot Water")
print(f"Items: {[i.name for i in hot_water_menu.children]}")

# Get current value
temp_item = api.menu.navigate("Hot Water/Temperature")
print(f"DHW Temp: {api.menu.get_value()}°C")
```

### Control Hot Water (User Story 3)

```python
# Read current settings
print(f"Temperature: {api.hot_water.temperature}°C")
print(f"Program Mode: {api.hot_water.program_mode.name}")

# Change temperature (validated: 20-65°C)
api.hot_water.temperature = 55.0

# Change program mode
from buderus_wps import DHWProgramMode
api.hot_water.program_mode = DHWProgramMode.PROGRAM_1
```

### Manage Schedules (User Story 4)

```python
from datetime import time

# Read DHW schedule for Program 1
schedule = api.hot_water.get_schedule(program=1)
print(f"Monday: {schedule.monday.start_time} - {schedule.monday.end_time}")

# Modify schedule (times must be on 30-minute boundaries)
from buderus_wps import WeeklySchedule, ScheduleSlot

new_schedule = WeeklySchedule(
    monday=ScheduleSlot(time(6, 0), time(22, 0)),
    tuesday=ScheduleSlot(time(6, 0), time(22, 0)),
    wednesday=ScheduleSlot(time(6, 0), time(22, 0)),
    thursday=ScheduleSlot(time(6, 0), time(22, 0)),
    friday=ScheduleSlot(time(6, 0), time(22, 0)),
    saturday=ScheduleSlot(time(7, 30), time(23, 30)),
    sunday=ScheduleSlot(time(7, 30), time(23, 30)),
)
api.hot_water.set_schedule(program=1, schedule=new_schedule)
```

### Control Operating Modes (User Story 5)

```python
from buderus_wps import RoomProgramMode

# Read current mode for circuit 1
circuit = api.get_circuit(1)
print(f"Program Mode: {circuit.program_mode.name}")
print(f"Summer Mode: {circuit.summer_mode}")

# Change program mode
circuit.program_mode = RoomProgramMode.PROGRAM_1
```

### Read Energy Statistics (User Story 6)

```python
# Read energy values
print(f"Heat Generated: {api.energy.heat_generated_kwh} kWh")
print(f"Aux Heater: {api.energy.aux_heater_kwh} kWh")
```

### Handle Alarms (User Story 7)

```python
# Check for active alarms
for alarm in api.alarms.active_alarms:
    print(f"[{alarm.category.name}] {alarm.code}: {alarm.description}")
    print(f"  Time: {alarm.timestamp}, Acknowledged: {alarm.acknowledged}")

# Acknowledge an alarm
if api.alarms.active_alarms:
    api.alarms.acknowledge(api.alarms.active_alarms[0])

# Clear a resolved alarm
for alarm in api.alarms.active_alarms:
    if alarm.clearable:
        api.alarms.clear(alarm)
```

### Multi-Circuit Configuration (User Story 8)

```python
# Access different circuits
for i in range(1, 5):
    try:
        circuit = api.get_circuit(i)
        print(f"Circuit {i} ({circuit.circuit_type.name}):")
        print(f"  Temperature: {circuit.temperature}°C")
        print(f"  Setpoint: {circuit.setpoint}°C")
    except CircuitNotAvailableError:
        print(f"Circuit {i}: Not configured")
```

### Vacation Mode (User Story 9)

```python
from datetime import date
from buderus_wps import VacationPeriod

# Check vacation status
vacation = api.vacation.get_circuit(1)
print(f"Vacation active: {vacation.active}")
if vacation.active:
    print(f"  {vacation.start_date} to {vacation.end_date}")

# Set vacation mode
api.vacation.set_circuit(1, VacationPeriod(
    active=True,
    start_date=date(2025, 12, 20),
    end_date=date(2025, 12, 27),
    reduced_setpoint=15.0
))

# Also set DHW vacation
api.vacation.set_hot_water(VacationPeriod(
    active=True,
    start_date=date(2025, 12, 20),
    end_date=date(2025, 12, 27)
))

# Clear vacation when returning early
api.vacation.clear_circuit(1)
api.vacation.clear_hot_water()
```

## Error Handling

```python
from buderus_wps import (
    ValidationError,
    ReadOnlyError,
    ParameterNotFoundError,
    MenuNavigationError,
    AlarmNotClearableError,
    CircuitNotAvailableError,
)

try:
    api.hot_water.temperature = 70.0  # Out of range
except ValidationError as e:
    print(f"Invalid: {e.constraint}")
    print(f"Allowed: {e.allowed_range}")

try:
    api.alarms.clear(some_alarm)
except AlarmNotClearableError as e:
    print(f"Cannot clear alarm {e.alarm_code}: {e.reason}")
```

## Cleanup

```python
# Always disconnect when done
adapter.disconnect()
```

## Performance Notes

- `api.status.read_all()` completes in <2 seconds (SC-001)
- Menu navigation to any setting completes in <5 seconds (SC-002)
- All write operations validate before sending to avoid CAN errors
