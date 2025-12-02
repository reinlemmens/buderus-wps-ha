# Data Model: Terminal Menu UI

**Feature**: 008-terminal-menu-ui
**Date**: 2025-11-28

## Overview

This document defines the data structures and state models for the terminal menu UI. The TUI is a stateful application with screen transitions, navigation state, and connection management.

## Application State

### AppState

The root state container for the entire application.

```
AppState
├── connection: ConnectionState
├── screen: ScreenType
├── navigation: NavigationState
├── error: ErrorInfo | None
└── last_refresh: datetime
```

| Field | Type | Description |
|-------|------|-------------|
| connection | ConnectionState | Current connection status |
| screen | ScreenType | Active screen being displayed |
| navigation | NavigationState | Menu navigation state |
| error | ErrorInfo | None | Current error (if any) |
| last_refresh | datetime | Timestamp of last data refresh |

### ConnectionState

Enumeration of connection states.

| Value | Description |
|-------|-------------|
| CONNECTING | Initial connection in progress |
| CONNECTED | Successfully connected to heat pump |
| DISCONNECTED | Not connected (initial or after error) |
| TIMEOUT | Communication timeout occurred |
| ERROR | Connection error occurred |

### ScreenType

Enumeration of available screens.

| Value | Description |
|-------|-------------|
| DASHBOARD | Status dashboard (default on launch) |
| MENU | Menu navigation view |
| EDITOR | Value editing view |
| SCHEDULE | Schedule display/edit view |
| ERROR | Error display view |

---

## Screen Models

### DashboardModel

Data displayed on the status dashboard screen. All temperatures read via broadcast monitoring.

```
DashboardModel
├── outdoor_temp: float | None
├── supply_temp: float | None
├── return_temp: float | None
├── dhw_temp: float | None
├── brine_in_temp: float | None
├── circuit_temps: list[CircuitTempModel]
├── operating_mode: OperatingMode | None
├── compressor_running: bool
├── compressor_frequency: int
├── compressor_mode: str
├── aux_heater_active: bool | None
├── defrost_active: bool | None
└── error_active: bool
```

| Field | Type | Description |
|-------|------|-------------|
| outdoor_temp | float | None | Outdoor temperature in °C (GT2) |
| supply_temp | float | None | Supply water temperature in °C (GT8) |
| return_temp | float | None | Return water temperature in °C (GT9) |
| dhw_temp | float | None | DHW (hot water) temperature in °C (GT3) |
| brine_in_temp | float | None | Brine inlet temperature in °C (GT1) |
| circuit_temps | list[CircuitTempModel] | Per-circuit room temperatures |
| operating_mode | OperatingMode | None | Current operating mode |
| compressor_running | bool | Whether compressor is running (frequency > 0) |
| compressor_frequency | int | Compressor frequency in Hz (0 = stopped) |
| compressor_mode | str | Compressor mode: "DHW", "Heating", or "Idle" |
| aux_heater_active | bool | None | Whether auxiliary heater is active |
| defrost_active | bool | None | Whether defrost cycle is active |
| error_active | bool | Whether any alarm is active |

### CircuitTempModel

Temperature data for a single heating circuit.

```
CircuitTempModel
├── circuit_number: int
├── circuit_name: str
├── room_temp: float | None
├── setpoint: float | None
└── program_mode: str | None
```

| Field | Type | Description |
|-------|------|-------------|
| circuit_number | int | Circuit number (1-4) |
| circuit_name | str | Display name from config |
| room_temp | float | None | Room temperature in °C |
| setpoint | float | None | Target setpoint in °C |
| program_mode | str | None | Active program mode |

### MenuModel

Data for the menu navigation screen.

```
MenuModel
├── items: list[MenuItemModel]
├── selected_index: int
├── scroll_offset: int
└── visible_count: int
```

| Field | Type | Description |
|-------|------|-------------|
| items | list[MenuItemModel] | Menu items at current level |
| selected_index | int | Currently highlighted item index |
| scroll_offset | int | Scroll position for long menus |
| visible_count | int | Number of items visible on screen |

### MenuItemModel

Individual menu item display data.

```
MenuItemModel
├── name: str
├── display_value: str | None
├── has_children: bool
├── is_writable: bool
└── icon: str | None
```

| Field | Type | Description |
|-------|------|-------------|
| name | str | Menu item display name |
| display_value | str | None | Current value (for leaf nodes) |
| has_children | bool | Whether item has submenus |
| is_writable | bool | Whether value can be edited |
| icon | str | None | Optional icon character |

### EditorModel

Data for the value editing screen.

```
EditorModel
├── parameter_name: str
├── current_value: str
├── edit_buffer: str
├── cursor_position: int
├── value_type: ValueType
├── min_value: float | None
├── max_value: float | None
├── unit: str | None
├── options: list[str] | None
├── error_message: str | None
└── is_dirty: bool
```

| Field | Type | Description |
|-------|------|-------------|
| parameter_name | str | Name of parameter being edited |
| current_value | str | Original value before editing |
| edit_buffer | str | Current edited value |
| cursor_position | int | Cursor position in edit buffer |
| value_type | ValueType | Type of value (numeric, enum, time) |
| min_value | float | None | Minimum allowed value |
| max_value | float | None | Maximum allowed value |
| unit | str | None | Display unit (°C, kWh, etc.) |
| options | list[str] | None | Valid options for enum values |
| error_message | str | None | Validation error message |
| is_dirty | bool | Whether value has been modified |

### ValueType

Enumeration of editable value types.

| Value | Description |
|-------|-------------|
| NUMERIC | Numeric value with min/max range |
| ENUM | Selection from predefined options |
| TIME | Time value (HH:MM format) |
| DATE | Date value (YYYY-MM-DD format) |

### ScheduleModel

Data for the schedule display/edit screen.

```
ScheduleModel
├── program_name: str
├── program_number: int
├── days: list[DayScheduleModel]
├── selected_day: int
├── editing: bool
└── edit_field: ScheduleField | None
```

| Field | Type | Description |
|-------|------|-------------|
| program_name | str | Schedule name (e.g., "DHW Program 1") |
| program_number | int | Program number (1-3) |
| days | list[DayScheduleModel] | Schedule for each day |
| selected_day | int | Currently selected day (0=Monday) |
| editing | bool | Whether in edit mode |
| edit_field | ScheduleField | None | Field being edited |

### DayScheduleModel

Schedule data for a single day.

```
DayScheduleModel
├── day_name: str
├── start_time: time | None
├── end_time: time | None
└── is_active: bool
```

| Field | Type | Description |
|-------|------|-------------|
| day_name | str | Day name (e.g., "Monday") |
| start_time | time | None | Start time (30-min boundary) |
| end_time | time | None | End time (30-min boundary) |
| is_active | bool | Whether schedule is active for this day |

### ScheduleField

Enumeration of editable schedule fields.

| Value | Description |
|-------|-------------|
| START_TIME | Editing start time |
| END_TIME | Editing end time |

---

## Navigation State

### NavigationState

Tracks position in the menu hierarchy.

```
NavigationState
├── path: list[str]
├── current_item: MenuItem | None
└── history: list[NavigationEntry]
```

| Field | Type | Description |
|-------|------|-------------|
| path | list[str] | Current path from root (e.g., ["Hot Water", "Temperature"]) |
| current_item | MenuItem | None | Currently selected menu item |
| history | list[NavigationEntry] | Navigation history for back function |

### NavigationEntry

Single entry in navigation history.

```
NavigationEntry
├── path: list[str]
├── selected_index: int
└── scroll_offset: int
```

| Field | Type | Description |
|-------|------|-------------|
| path | list[str] | Path at this point |
| selected_index | int | Selected item index |
| scroll_offset | int | Scroll position |

---

## Widget Models

### StatusBarModel

Data for the header status bar.

```
StatusBarModel
├── title: str
├── connection_status: ConnectionState
├── clock: str
└── error_indicator: bool
```

| Field | Type | Description |
|-------|------|-------------|
| title | str | Application title |
| connection_status | ConnectionState | Current connection state |
| clock | str | Current time display |
| error_indicator | bool | Whether error icon is shown |

### BreadcrumbModel

Data for the navigation breadcrumb.

```
BreadcrumbModel
├── segments: list[str]
└── max_width: int
```

| Field | Type | Description |
|-------|------|-------------|
| segments | list[str] | Path segments to display |
| max_width | int | Maximum display width |

### HelpBarModel

Data for the bottom help bar.

```
HelpBarModel
└── actions: list[HelpAction]
```

### HelpAction

Single help action display.

```
HelpAction
├── key: str
└── description: str
```

| Field | Type | Description |
|-------|------|-------------|
| key | str | Key or key combination (e.g., "Enter") |
| description | str | Action description (e.g., "Select") |

---

## Error Handling

### ErrorInfo

Error information for display.

```
ErrorInfo
├── error_type: ErrorType
├── message: str
├── details: str | None
├── recoverable: bool
└── timestamp: datetime
```

| Field | Type | Description |
|-------|------|-------------|
| error_type | ErrorType | Category of error |
| message | str | User-friendly error message |
| details | str | None | Technical details (optional) |
| recoverable | bool | Whether retry is possible |
| timestamp | datetime | When error occurred |

### ErrorType

Enumeration of error categories.

| Value | Description |
|-------|-------------|
| CONNECTION | Connection to device failed |
| TIMEOUT | Communication timeout |
| VALIDATION | Input validation failed |
| WRITE_FAILED | Failed to write value |
| UNKNOWN | Unknown error |

---

## State Transitions

### Screen Transitions

```
DASHBOARD ──[Enter]──> MENU
    ↑                    │
    └──[Escape]──────────┘
                         │
MENU ──[Enter on leaf]──> EDITOR
    ↑                       │
    └──[Escape/Enter]───────┘
                         │
MENU ──[Enter on schedule]──> SCHEDULE
    ↑                           │
    └──[Escape]─────────────────┘
```

### Connection State Transitions

```
DISCONNECTED ──[connect()]──> CONNECTING
       ↑                          │
       │                    ┌─────┴─────┐
       │                    ↓           ↓
       │               CONNECTED     ERROR
       │                    │           │
       └──[disconnect()]────┴───────────┘
       ↑
CONNECTED ──[timeout]──> TIMEOUT
       ↑                    │
       └──[retry success]───┘
```

### Edit Mode Transitions

```
VIEW_MODE ──[Enter]──> EDIT_MODE
    ↑                      │
    │              ┌───────┴───────┐
    │              ↓               ↓
    └──[Escape]────┤      [Enter + valid]
                   │               │
                   │               ↓
                   └───────── WRITE_PENDING
                                   │
                              ┌────┴────┐
                              ↓         ↓
                          SUCCESS    FAILED
                              │         │
                              └────┬────┘
                                   ↓
                              VIEW_MODE
```

---

## Key Bindings

| Key | Dashboard | Menu | Editor | Schedule |
|-----|-----------|------|--------|----------|
| Up | - | Select previous | - | Select previous day |
| Down | - | Select next | - | Select next day |
| Left | - | Go to parent | - | - |
| Right | - | Enter submenu | - | - |
| Enter | Go to Menu | Enter/Edit | Confirm | Edit field |
| Escape | Quit dialog | Go to parent | Cancel | Exit edit |
| r | Refresh | Refresh | - | Refresh |
| q | Quit | Quit | - | Quit |
| Backspace | - | Go to parent | Delete char | - |
| 0-9 | - | - | Input digit | Input time |

---

## Configuration Models

### CircuitConfiguration

Configuration for heating circuits loaded from buderus-wps.yaml.

```
CircuitConfiguration
├── circuits: list[CircuitConfig]
└── default_circuit_count: int
```

| Field | Type | Description |
|-------|------|-------------|
| circuits | list[CircuitConfig] | Configured heating circuits |
| default_circuit_count | int | Default if config missing (1) |

### CircuitConfig

Single circuit configuration entry.

```
CircuitConfig
├── number: int
├── name: str
├── room_temp_sensor: str
├── setpoint_param: str
└── program_param: str
```

| Field | Type | Description |
|-------|------|-------------|
| number | int | Circuit number (1-4) |
| name | str | Display name for UI |
| room_temp_sensor | str | Sensor name for broadcast monitoring |
| setpoint_param | str | Parameter name for setpoint |
| program_param | str | Parameter name for program mode |
