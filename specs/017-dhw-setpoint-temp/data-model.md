# Data Model: DHW Setpoint Temperature

**Feature**: 017-dhw-setpoint-temp
**Date**: 2026-01-04

## Entities

### BuderusData (Modified)

The existing `BuderusData` dataclass in `coordinator.py` will be extended with one new field.

**New Field**:

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `dhw_setpoint` | `float \| None` | DHW target temperature in °C | `DHW_CALCULATED_SETPOINT_TEMP` parameter |

**Existing Related Fields** (for context):

| Field | Type | Description |
|-------|------|-------------|
| `dhw_stop_temp` | `float \| None` | DHW stop charging temperature (boost mode) |
| `dhw_extra_duration` | `int` | Extra DHW production hours remaining |
| `dhw_program_mode` | `int \| None` | DHW program mode (0=Auto, 1=On, 2=Off) |

---

### DHW Setpoint Temperature Entity

**Home Assistant Entity**:

| Property | Value |
|----------|-------|
| Domain | `number` |
| Entity ID | `number.heat_pump_dhw_setpoint_temperature` |
| Name | "DHW Setpoint Temperature" |
| Unit | °C |
| Min | 40.0 |
| Max | 70.0 |
| Step | 0.5 |
| Mode | Box (input field) |
| Icon | `mdi:water-thermometer` |

---

## Parameter Mapping

| Heat Pump Parameter | Index | Format | Range (raw) | Range (°C) | Direction |
|---------------------|-------|--------|-------------|------------|-----------|
| `DHW_CALCULATED_SETPOINT_TEMP` | 385 | tem | 400-700 | 40.0-70.0 | Read/Write |

**Encoding**:
- Raw value = Temperature × 10
- Example: 55.0°C → raw 550

---

## State Transitions

```
                    ┌─────────────────┐
                    │   Unavailable   │
                    │  (no connection)│
                    └────────┬────────┘
                             │ connect
                             ▼
┌─────────────────┐    ┌─────────────────┐
│    Loading      │───▶│     Ready       │
│ (initial read)  │    │ (value: 40-70°C)│
└─────────────────┘    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
            ┌───────────┐     ┌───────────┐
            │  Reading  │     │  Writing  │
            │(poll/RTR) │     │(user set) │
            └─────┬─────┘     └─────┬─────┘
                  │                 │
                  └────────┬────────┘
                           ▼
                    ┌─────────────────┐
                    │     Ready       │
                    │ (updated value) │
                    └─────────────────┘
```

---

## Validation Rules

| Rule | Constraint | Error Message |
|------|------------|---------------|
| Minimum | value >= 40.0 | "DHW setpoint must be at least 40.0°C" |
| Maximum | value <= 70.0 | "DHW setpoint must not exceed 70.0°C" |
| Step | value % 0.5 == 0 | (HA handles automatically) |

---

## Relationships

```
┌──────────────────────┐
│    Heat Pump         │
│  (physical device)   │
└──────────┬───────────┘
           │ CAN bus
           ▼
┌──────────────────────┐
│   BuderusCoordinator │
│   - dhw_setpoint     │◄───────────────────┐
│   - dhw_stop_temp    │                    │
│   - dhw_program_mode │                    │
└──────────┬───────────┘                    │
           │ data                           │ write
           ▼                                │
┌──────────────────────┐     ┌──────────────┴───────┐
│ BuderusDHWSetpoint   │────▶│ async_set_dhw_setpoint│
│ Number (HA Entity)   │     │ (coordinator method)  │
└──────────────────────┘     └──────────────────────┘
```
