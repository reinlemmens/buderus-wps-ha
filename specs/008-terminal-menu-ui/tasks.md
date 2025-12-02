# Tasks: Terminal Menu UI

**Feature**: 008-terminal-menu-ui | **Branch**: `008-terminal-menu-ui`
**Updated**: 2025-12-02 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

Implementation tasks for the Terminal Menu UI feature. Tasks are organized by phase and user story priority, with testing integrated at each step per Constitution IV.

**Existing Code Status**:
- `buderus_wps_cli/tui/app.py` - Exists, needs enhancement for circuits, editor
- `buderus_wps_cli/tui/screens/dashboard.py` - Exists, needs multi-circuit temps
- `buderus_wps_cli/tui/screens/menu.py` - Exists, needs dynamic circuit menus
- `buderus_wps_cli/tui/screens/editor.py` - Exists, needs completion
- `buderus_wps_cli/tui/screens/schedule.py` - Exists, needs completion

**Key Requirements**:
- FR-014: ALL temperatures via broadcast monitoring (not RTR)
- FR-015-18: Configurable 1-4 heating circuits from buderus-wps.yaml
- FR-019: Compressor status with frequency and mode (DHW/Heating/Idle)
- FR-020: Dynamic menu structure (only show configured circuits)
- Clarification: Direct digit typing (0-9, backspace), stay in edit until Enter/Escape

---

## Phase 1: Setup (Shared Infrastructure) ✅

**Purpose**: Project initialization and TUI module structure

- [x] T001 Create TUI package structure: `buderus_wps_cli/tui/__init__.py`
- [x] T002 [P] Create screens subpackage: `buderus_wps_cli/tui/screens/__init__.py`
- [x] T003 [P] Create widgets subpackage: `buderus_wps_cli/tui/widgets/__init__.py`
- [x] T004 Add `buderus-tui` CLI entry point in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites) ✅

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

### Tests for Foundation ✅

- [x] T005 [P] Unit test for AppState and ConnectionState in `tests/unit/test_tui_state.py`
- [x] T006 [P] Unit test for keyboard handling in `tests/unit/test_tui_keyboard.py`
- [x] T007 [P] Unit test for base screen class in `tests/unit/test_tui_screens.py`

### Implementation for Foundation ✅

- [x] T008 Implement AppState, ConnectionState, ScreenType enums in `buderus_wps_cli/tui/state.py`
- [x] T009 Implement keyboard key mapping and action dispatch in `buderus_wps_cli/tui/keyboard.py`
- [x] T010 Implement base Screen class with curses wrapper in `buderus_wps_cli/tui/screens/base.py`
- [x] T011 Implement ErrorInfo and ErrorType in `buderus_wps_cli/tui/state.py`
- [x] T012 Implement StatusBar widget in `buderus_wps_cli/tui/widgets/status_bar.py`
- [x] T013 [P] Implement Breadcrumb widget in `buderus_wps_cli/tui/widgets/breadcrumb.py`
- [x] T014 [P] Implement HelpBar widget in `buderus_wps_cli/tui/widgets/help_bar.py`
- [x] T015 Create main application entry point with curses.wrapper in `buderus_wps_cli/tui/app.py`
- [x] T016 Implement connection to MenuAPI in `buderus_wps_cli/tui/app.py`

**Checkpoint**: Foundation ready ✅

---

## Phase 2.5: Circuit Configuration (NEW - Foundation Extension)

**Purpose**: Load and apply dynamic circuit configuration from YAML

### Tests for Circuit Configuration

- [ ] T100 [P] Unit test for CircuitConfig loading in `tests/unit/test_tui_config.py`
- [ ] T101 [P] Unit test for missing/invalid config handling in `tests/unit/test_tui_config.py`

### Implementation for Circuit Configuration

- [ ] T102 Add CircuitConfig dataclass to `buderus_wps/config.py`
  - Fields: number, name, room_temp_sensor, setpoint_param, program_param
- [ ] T103 Implement load_circuit_config() in `buderus_wps/config.py`
  - Load from buderus-wps.yaml
  - Return list of CircuitConfig
  - Default to single circuit if missing
- [ ] T104 Add CircuitTempModel dataclass to `buderus_wps_cli/tui/screens/dashboard.py`
  - Fields: circuit_number, circuit_name, room_temp, setpoint, program_mode
- [ ] T105 Load circuit config in TUIApp.__init__() in `buderus_wps_cli/tui/app.py`

**Checkpoint**: Circuit configuration loaded from YAML

---

## Phase 3: User Story 1 - View System Status Dashboard (Priority: P1) 🎯 MVP

**Goal**: Display a status dashboard showing current temperatures and system status on startup

**Acceptance Scenarios**:
1. Dashboard displays all key temps and operating status on startup
2. Press 'r' to refresh, updates within 5 seconds
3. Connection error shows troubleshooting hints
4. ALL temperatures from broadcast monitoring (not RTR)

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [P] [US1] Unit test for DashboardModel with circuit_temps list in `tests/unit/test_tui_dashboard.py`
- [ ] T018 [P] [US1] Unit test for DashboardScreen rendering multi-circuit temps in `tests/unit/test_tui_dashboard.py`
- [ ] T019 [P] [US1] Unit test for compressor status display (frequency, mode) in `tests/unit/test_tui_dashboard.py`
- [ ] T020 [P] [US1] Integration test for dashboard with mocked broadcast monitor in `tests/integration/test_tui_integration.py`

### Implementation for User Story 1

- [ ] T021 [US1] Extend DashboardModel in `buderus_wps_cli/tui/screens/dashboard.py`
  - Add: circuit_temps: list[CircuitTempModel]
  - Add: brine_in_temp: Optional[float]
  - Add: compressor_frequency: int
  - Add: compressor_mode: str (DHW/Heating/Idle)
  - Remove: single room_temp (replaced by circuit_temps)

- [ ] T022 [US1] Update DashboardScreen._render_status() in `buderus_wps_cli/tui/screens/dashboard.py`
  - Add "Heating Circuits" section after main temps
  - Display each circuit: "{name}: {room_temp}°C → {setpoint}°C"
  - Only show circuits from configuration (not empty slots)
  - Handle missing room temp (show "---")

- [ ] T023 [US1] Update compressor display in `buderus_wps_cli/tui/screens/dashboard.py`
  - Show "Compressor: Running at {freq} Hz ({mode})" when frequency > 0
  - Show "Compressor: Stopped (Idle)" when frequency = 0
  - Mode from COMPRESSOR_DHW_REQUEST > 0 = DHW, COMPRESSOR_HEATING_REQUEST > 0 = Heating

- [ ] T024 [US1] Extend broadcast temp mapping in `buderus_wps_cli/tui/app.py`
  - Add room_temp_c1..c4 to TEMP_BROADCAST_MAP
  - Map per-circuit temps to CircuitTempModel
  - Use circuit config to determine which sensors to map

- [ ] T025 [US1] Add connection error display with troubleshooting hints in `buderus_wps_cli/tui/screens/dashboard.py`

- [ ] T026 [US1] Wire dashboard as startup screen in `buderus_wps_cli/tui/app.py`

**Checkpoint**: User Story 1 complete - dashboard displays multi-circuit status, compressor freq/mode

---

## Phase 4: User Story 2 - Navigate Menu Structure (Priority: P1)

**Goal**: Navigate through menus using arrow keys with breadcrumb display

**Acceptance Scenarios**:
1. Up/Down arrows highlight menu items sequentially
2. Enter navigates into submenu or shows value
3. Escape/Backspace returns to parent menu
4. Breadcrumb shows current location (e.g., "Hot Water > Temperature")

### Tests for User Story 2

- [ ] T027 [P] [US2] Unit test for MenuModel and MenuItemModel in `tests/unit/test_tui_menu.py`
- [ ] T028 [P] [US2] Unit test for dynamic circuit menu building in `tests/unit/test_tui_menu.py`
- [ ] T029 [P] [US2] Unit test for MenuScreen rendering and navigation in `tests/unit/test_tui_menu.py`
- [ ] T030 [P] [US2] Integration test for menu navigation workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 2

- [ ] T031 [US2] Implement MenuModel and MenuItemModel dataclasses in `buderus_wps_cli/tui/screens/menu.py`

- [ ] T032 [US2] Implement dynamic "Heating Circuits" menu in `buderus_wps_cli/tui/app.py`
  - Build menu items from circuit config (FR-020)
  - 2-circuit config shows 2 entries
  - 4-circuit config shows 4 entries
  - 0 circuits shows "No heating circuits configured"

- [ ] T033 [US2] Implement NavigationState with path tracking in `buderus_wps_cli/tui/state.py`

- [ ] T034 [US2] Implement MenuScreen with arrow key navigation in `buderus_wps_cli/tui/screens/menu.py`

- [ ] T035 [US2] Integrate MenuScreen with MenuNavigator from MenuAPI in `buderus_wps_cli/tui/screens/menu.py`

- [ ] T036 [US2] Implement breadcrumb display using Breadcrumb widget in `buderus_wps_cli/tui/screens/menu.py`

- [ ] T037 [US2] Add Enter/Escape/Backspace navigation handlers in `buderus_wps_cli/tui/screens/menu.py`

- [ ] T038 [US2] Wire menu screen transition from dashboard (Enter key) in `buderus_wps_cli/tui/app.py`

**Checkpoint**: User Stories 1 AND 2 complete - can view dashboard and navigate menu with dynamic circuits

---

## Phase 5: User Story 3 - Adjust Hot Water Temperature (Priority: P2)

**Goal**: Edit DHW temperature setpoint with validation and direct digit input

**Acceptance Scenarios**:
1. Enter opens edit mode with current value and cursor ready
2. Type digits (0-9), backspace to correct - input updates accordingly
3. Value 20-65 + Enter: accepted and written
4. Value outside range + Enter: error shown, stay in edit mode
5. Valid value + Enter: written to heat pump, return to menu
6. Escape: cancel edit, discard changes, return to menu

### Tests for User Story 3

- [ ] T039 [P] [US3] Unit test for EditorModel and ValueType in `tests/unit/test_tui_editor.py`
- [ ] T040 [P] [US3] Unit test for direct digit input (0-9, backspace) in `tests/unit/test_tui_editor.py`
- [ ] T041 [P] [US3] Unit test for numeric validation in EditorScreen in `tests/unit/test_tui_editor.py`
- [ ] T042 [P] [US3] Unit test for staying in edit mode on validation error in `tests/unit/test_tui_editor.py`
- [ ] T043 [P] [US3] Integration test for temperature edit workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 3

- [ ] T044 [US3] Implement EditorModel dataclass with ValueType enum in `buderus_wps_cli/tui/screens/editor.py`

- [ ] T045 [US3] Implement EditorScreen with direct digit input in `buderus_wps_cli/tui/screens/editor.py`
  - Accept digit keys (0-9) to build value in edit_buffer
  - Backspace removes last character
  - Non-digit keys ignored (no beep)
  - Display: parameter name, current value, edit buffer with cursor

- [ ] T046 [US3] Add validation with error display in `buderus_wps_cli/tui/screens/editor.py`
  - Enter: check value against min_value, max_value
  - Invalid: show error message, stay in edit mode (don't return to menu)
  - Clear error when user types new digit

- [ ] T047 [US3] Add write confirmation and return to menu in `buderus_wps_cli/tui/screens/editor.py`
  - Valid + Enter: write value, show confirmation, return to menu
  - Write failure: show error, stay in edit mode

- [ ] T048 [US3] Add Escape handler in `buderus_wps_cli/tui/screens/editor.py`
  - Discard edit_buffer
  - Return to menu without writing
  - Original value unchanged

- [ ] T049 [US3] Integrate EditorScreen with HotWaterController from MenuAPI in `buderus_wps_cli/tui/screens/editor.py`

- [ ] T050 [US3] Wire editor transition from menu for writable items in `buderus_wps_cli/tui/app.py`

**Checkpoint**: User Story 3 complete - can edit temperature with validation, stays in edit on error

---

## Phase 6: User Story 4 - Monitor and Control Heating Circuits (Priority: P2)

**Goal**: View and control all configured heating circuits with room temp, setpoint, and program

**Acceptance Scenarios**:
1. Heating Circuits menu shows all configured circuits with room temp, setpoint, program
2. Select circuit shows detail with room temp (broadcast), setpoint, program mode
3. Edit circuit setpoint: valid temp written to heat pump
4. All room temps from broadcast monitoring
5. Uses configured circuit mappings from buderus-wps.yaml
6. 2-circuit config shows only 2 entries (not empty slots)
7. 4-circuit config shows all 4 entries with configured names

### Tests for User Story 4

- [ ] T051 [P] [US4] Unit test for per-circuit display in menu in `tests/unit/test_tui_menu.py`
- [ ] T052 [P] [US4] Unit test for circuit detail view in `tests/unit/test_tui_menu.py`
- [ ] T053 [P] [US4] Unit test for 2-circuit vs 4-circuit menu rendering in `tests/unit/test_tui_menu.py`
- [ ] T054 [P] [US4] Integration test for circuit setpoint edit in `tests/integration/test_tui_integration.py`

### Implementation for User Story 4

- [ ] T055 [US4] Implement per-circuit menu items in `buderus_wps_cli/tui/app.py`
  - Each circuit shows: "{name} ({room_temp}°C)"
  - Navigate into circuit for details

- [ ] T056 [US4] Implement circuit detail view in `buderus_wps_cli/tui/screens/menu.py`
  - Display room temperature (from CircuitTempModel)
  - Display current setpoint
  - Display active program mode
  - Allow editing setpoint (launches editor)

- [ ] T057 [US4] Implement circuit setpoint editing in `buderus_wps_cli/tui/app.py`
  - Open editor with circuit-specific min/max
  - Write uses circuit-specific parameter from config
  - Confirmation shown on success

- [ ] T058 [US4] Map room temp sensors per circuit in `buderus_wps_cli/tui/app.py`
  - Use room_temp_sensor from CircuitConfig
  - Map to TEMP_BROADCAST_MAP entry
  - Handle missing sensor gracefully (show "---")

**Checkpoint**: User Story 4 complete - can view/control multiple circuits

---

## Phase 7: User Story 5 - View and Edit Weekly Schedules (Priority: P2)

**Goal**: Display and modify DHW and per-circuit schedules with 30-minute boundary validation

**Acceptance Scenarios**:
1. Schedule displays all 7 days with start/end times
2. Select day to edit start/end times
3. Invalid times (not 30-min boundary) shows error
4. Save shows confirmation
5. Circuit has own schedule
6. Modify circuit schedule affects only that circuit

### Tests for User Story 5

- [ ] T059 [P] [US5] Unit test for ScheduleModel and DayScheduleModel in `tests/unit/test_tui_schedule.py`
- [ ] T060 [P] [US5] Unit test for ScheduleScreen rendering in `tests/unit/test_tui_schedule.py`
- [ ] T061 [P] [US5] Unit test for 30-minute boundary validation in `tests/unit/test_tui_schedule.py`
- [ ] T062 [P] [US5] Integration test for schedule edit workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 5

- [ ] T063 [US5] Implement ScheduleModel, DayScheduleModel dataclasses in `buderus_wps_cli/tui/screens/schedule.py`

- [ ] T064 [US5] Implement ScheduleScreen with weekly grid display in `buderus_wps_cli/tui/screens/schedule.py`

- [ ] T065 [US5] Add day selection navigation (Up/Down arrows) in `buderus_wps_cli/tui/screens/schedule.py`

- [ ] T066 [US5] Implement time editing with HH:MM format in `buderus_wps_cli/tui/screens/schedule.py`

- [ ] T067 [US5] Add 30-minute boundary validation for times in `buderus_wps_cli/tui/screens/schedule.py`

- [ ] T068 [US5] Integrate with HotWaterController/CircuitController.get_schedule/set_schedule in `buderus_wps_cli/tui/screens/schedule.py`

- [ ] T069 [US5] Implement per-circuit schedule access in `buderus_wps_cli/tui/app.py`
  - Navigate to circuit → program → schedule
  - Each circuit reads/writes independent schedule

- [ ] T070 [US5] Wire schedule screen for program menu items in `buderus_wps_cli/tui/app.py`

**Checkpoint**: User Story 5 complete - can view and edit weekly schedules per circuit

---

## Phase 8: User Story 6 - Monitor Energy Statistics (Priority: P3)

**Goal**: Display energy consumption statistics (heat generated, aux heater kWh)

**Acceptance Scenarios**:
1. Navigate to Energy menu, see heat generated and aux heater consumption
2. Refresh updates values

### Tests for User Story 6

- [ ] T071 [P] [US6] Unit test for energy display rendering in `tests/unit/test_tui_screens.py`
- [ ] T072 [P] [US6] Integration test for energy read workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 6

- [ ] T073 [US6] Add energy statistics display to MenuScreen in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T074 [US6] Integrate with EnergyView from MenuAPI in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T075 [US6] Add refresh support for energy values in `buderus_wps_cli/tui/screens/menu.py`

**Checkpoint**: User Story 6 complete - energy statistics viewable

---

## Phase 9: User Story 7 - View Active Alarms (Priority: P3)

**Goal**: Display active alarms with code, description, timestamp; allow acknowledge

**Acceptance Scenarios**:
1. Active alarms listed with code, description, timestamp
2. No alarms shows "No active alarms"
3. Acknowledge sends command to heat pump

### Tests for User Story 7

- [ ] T076 [P] [US7] Unit test for alarm list rendering in `tests/unit/test_tui_screens.py`
- [ ] T077 [P] [US7] Unit test for acknowledge action in `tests/unit/test_tui_screens.py`
- [ ] T078 [P] [US7] Integration test for alarm workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 7

- [ ] T079 [US7] Add alarm list display in MenuScreen for Alarms menu in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T080 [US7] Display "No active alarms" when list is empty in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T081 [US7] Integrate with AlarmController from MenuAPI in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T082 [US7] Add acknowledge action for selected alarm in `buderus_wps_cli/tui/screens/menu.py`

**Checkpoint**: User Story 7 complete - alarms viewable and acknowledgeable

---

## Phase 10: User Story 8 - Configure Vacation Mode (Priority: P3)

**Goal**: Set/clear vacation mode with date entry and validation

**Acceptance Scenarios**:
1. View vacation status (active/inactive with dates)
2. Enter start/end dates with validation (end > start, not in past)
3. Clear vacation mode deactivates it

### Tests for User Story 8

- [ ] T083 [P] [US8] Unit test for vacation date entry in `tests/unit/test_tui_editor.py`
- [ ] T084 [P] [US8] Unit test for date validation in `tests/unit/test_tui_editor.py`
- [ ] T085 [P] [US8] Integration test for vacation workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 8

- [ ] T086 [US8] Add DATE value type to EditorScreen in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T087 [US8] Implement date input handling (YYYY-MM-DD format) in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T088 [US8] Add date validation (end after start, not in past) in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T089 [US8] Integrate with VacationController from MenuAPI in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T090 [US8] Add clear vacation action in `buderus_wps_cli/tui/screens/menu.py`

**Checkpoint**: User Story 8 complete - vacation mode configurable

---

## Phase 11: Edge Cases & Polish

**Purpose**: Handle edge cases and cross-cutting concerns

### Edge Case: Connection Loss

- [ ] T091 [P] Unit test for connection loss detection in `tests/unit/test_tui_app.py`
- [ ] T092 Detect connection loss on API call failure in `buderus_wps_cli/tui/app.py`
- [ ] T093 Show error with retry option, prevent data corruption in `buderus_wps_cli/tui/app.py`

### Edge Case: Invalid Input

- [ ] T094 [P] Unit test for non-numeric input rejection in `tests/unit/test_tui_editor.py`
- [ ] T095 Ignore non-digit keys in numeric editor in `buderus_wps_cli/tui/screens/editor.py`

### Edge Case: Terminal Resize

- [ ] T096 [P] Unit test for resize event handling in `tests/unit/test_tui_screens.py`
- [ ] T097 Handle KEY_RESIZE, recalculate layout in `buderus_wps_cli/tui/app.py`
- [ ] T098 Show warning if < 80x24 in `buderus_wps_cli/tui/app.py`

### Edge Case: Ctrl+C Exit

- [ ] T099 Implement graceful Ctrl+C and 'q' exit in `buderus_wps_cli/tui/app.py`
  - Catch KeyboardInterrupt
  - Disconnect from heat pump
  - Restore terminal state
  - Exit with code 0

### Edge Case: Missing/Invalid Config

- [ ] T106 [P] Unit test for missing config file in `tests/unit/test_tui_config.py`
- [ ] T107 Handle missing/malformed config with defaults in `buderus_wps/config.py`

---

## Phase 12: Final Validation

### Acceptance Test Suite

- [ ] T108 [US1] Acceptance tests in `tests/acceptance/tui/test_us1_dashboard.py` (4 scenarios)
- [ ] T109 [US2] Acceptance tests in `tests/acceptance/tui/test_us2_navigation.py` (4 scenarios)
- [ ] T110 [US3] Acceptance tests in `tests/acceptance/tui/test_us3_dhw_edit.py` (6 scenarios)
- [ ] T111 [US4] Acceptance tests in `tests/acceptance/tui/test_us4_circuits.py` (7 scenarios)
- [ ] T112 [US5] Acceptance tests in `tests/acceptance/tui/test_us5_schedules.py` (6 scenarios)
- [ ] T113 [US6] Acceptance tests in `tests/acceptance/tui/test_us6_energy.py` (2 scenarios)
- [ ] T114 [US7] Acceptance tests in `tests/acceptance/tui/test_us7_alarms.py` (3 scenarios)
- [ ] T115 [US8] Acceptance tests in `tests/acceptance/tui/test_us8_vacation.py` (3 scenarios)

### Documentation

- [ ] T116 Update quickstart.md with circuit configuration format
- [ ] T117 Validate all quickstart scenarios manually

---

## Task Summary

| Phase | Description | Tasks | Status |
|-------|-------------|-------|--------|
| 1 | Setup | 4 | ✅ Complete |
| 2 | Foundation | 12 | ✅ Complete |
| 2.5 | Circuit Config | 6 | Pending |
| 3 | US1 Dashboard | 10 | Pending |
| 4 | US2 Navigation | 12 | Pending |
| 5 | US3 DHW Edit | 12 | Pending |
| 6 | US4 Circuits | 8 | Pending |
| 7 | US5 Schedules | 12 | Pending |
| 8 | US6 Energy | 5 | Pending |
| 9 | US7 Alarms | 7 | Pending |
| 10 | US8 Vacation | 8 | Pending |
| 11 | Edge Cases | 11 | Pending |
| 12 | Final | 10 | Pending |

**Total**: 117 tasks (16 complete, 101 pending)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) ✅
    ↓
Phase 2 (Foundation) ✅
    ↓
Phase 2.5 (Circuit Config) ← NEW BLOCKER
    ↓
Phase 3 (US1 Dashboard) ← MVP
    ↓
Phase 4 (US2 Navigation)
    ↓
┌───────────────────────────────────┐
│ Phase 5 (US3)  Phase 6 (US4)      │  ← Can parallelize
│ Phase 7 (US5)                     │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ Phase 8 (US6)  Phase 9 (US7)      │  ← Can parallelize
│ Phase 10 (US8)                    │
└───────────────────────────────────┘
    ↓
Phase 11 (Edge Cases)
    ↓
Phase 12 (Final Validation)
```

### Key Blockers

1. **Phase 2.5 (Circuit Config)** must complete before Phase 3 can start
2. **Phase 3 (US1)** must complete before Phase 4 (US2)
3. **Phase 4 (US2)** must complete before Phases 5-10 (all require menu navigation)

---

## Notes

- [P] = Can run in parallel with other [P] tasks in same section
- [USx] = Maps to User Story x for traceability
- Write tests FIRST, verify they FAIL (TDD per Constitution IV)
- All temperatures via broadcast monitoring (FR-014)
- Dynamic circuit menus based on config (FR-020)
- Direct digit input, stay in edit until Enter/Escape (Clarification 2025-12-02)
