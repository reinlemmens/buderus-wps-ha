# Research: Heat Pump Menu API

**Feature**: 007-heatpump-menu-api | **Phase**: 0 | **Date**: 2025-11-28

## Protocol Discoveries

### DHW Schedule Encoding (sw2 format)

**Discovery**: The FHEM documentation lists DHW schedule parameters at even indices (460, 462, 464, etc.), but these only return 1 byte containing the end time. The **odd indices** (+1: 461, 463, 465, etc.) return 2 bytes containing both start and end times.

**Evidence from hardware testing**:
```
# Documented index 460 (DHW_TIMER_P1_MONDAY) - returns 1 byte (end time only)
Parameter 460: raw=0x1E (30) = end at 15:00

# Odd index 461 (undocumented) - returns 2 bytes (start AND end)
Parameter 461: raw=0x5A1E = start=26 (13:00), end=30 (15:00)
```

**Encoding scheme**:
- High byte (bits 0-5): Start time slot (30-minute increments from 00:00)
- Low byte (bits 0-5): End time slot (30-minute increments from 00:00)
- Slot 0 = 00:00, Slot 1 = 00:30, Slot 26 = 13:00, Slot 30 = 15:00, Slot 47 = 23:30

**Implication**: To read full DHW schedules, use odd indices (param.idx + 1) for sw2 format parameters.

### Room Schedule Encoding (sw1 format)

**Behavior**: sw1 format parameters (room heating schedules) return 2 bytes at the documented indices, containing both start and end times in the same encoding as sw2.

**Key difference**: sw1 uses documented indices directly; sw2 requires +1 offset.

### Menu-to-Parameter Mapping

The physical menu structure maps to parameter groups:

| Menu Category | Parameter Prefix | Example Parameters |
|---------------|------------------|-------------------|
| Hot Water | DHW_* | DHW_SETTEMP, DHW_TIMER_P1_* |
| Program Mode | PROGRAM_*, ROOM_PROGRAM_* | ROOM_PROGRAM_MODE_C1 |
| Compressor | COMPRESSOR_* | COMPRESSOR_STATUS, COMPRESSOR_HOURS |
| Energy | ENERGY_*, HEAT_* | HEAT_GENERATED_24H, AUX_HEATER_KWH |
| Vacation | VACATION_* | VACATION_START_C1, VACATION_END_C1 |
| Alarms | ALARM_*, INFO_* | ALARM_LOG_1, INFO_LOG_1 |

### Parameter Format Types

| Format | Description | Decoding |
|--------|-------------|----------|
| temp | Temperature (tenths of degrees) | value / 10.0 |
| dp1 | Signed decimal, 1 decimal place | value / 10.0 |
| dp2 | Signed decimal, 2 decimal places | value / 100.0 |
| rp0 | Unsigned integer | value |
| sw1 | Room schedule (2 bytes) | documented index |
| sw2 | DHW schedule (2 bytes) | odd index (+1) |

## Technology Decisions

### API Design

**Decision**: Use property-style accessors with method names matching menu labels.

**Rationale**: SC-006 requires API alignment with user manual (e.g., `hot_water` not `dhw`). Property accessors provide intuitive navigation: `api.hot_water.temperature` mirrors "Hot Water → Temperature" menu path.

### Schedule Representation

**Decision**: Use `ScheduleSlot` dataclass with `start_time` and `end_time` as `time` objects.

**Rationale**: Python's `datetime.time` provides natural HH:MM representation and validation. Converting to/from 30-minute slots is encapsulated in `schedule_codec.py`.

### Circuit Abstraction

**Decision**: Use `Circuit` class with circuit number parameter (1-4).

**Rationale**: Circuits 2-4 are optional mixed circuits. Single class handles all circuit types; parameter names use `_C1`, `_C2`, etc. suffixes.

### Error Handling

**Decision**: Raise specific exceptions with constraint details.

**Rationale**: FR-034 requires meaningful error messages. Custom exceptions (e.g., `ValidationError`, `ReadOnlyError`) include the violated constraint and allowed values.

## Open Questions (Resolved)

1. ~~Alarm write capability~~ → Full control (read/acknowledge/clear)
2. ~~Vacation mode scope~~ → In scope (read/write)

## References

- FHEM plugin: `fhem/26_KM273v018.pm` (authoritative protocol reference)
- User manual: Table 3 (menu structure)
- Hardware testing session: 2025-11-28 (sw2 odd-index discovery)
