# Tasks: Terminal Menu UI

**Input**: Design documents from `/specs/008-terminal-menu-ui/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Required per constitution (TDD mandatory, 100% coverage for described functionality)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **CLI Package**: `buderus_wps_cli/tui/` (new TUI module)
- **Screens**: `buderus_wps_cli/tui/screens/`
- **Widgets**: `buderus_wps_cli/tui/widgets/`
- **Tests**: `tests/unit/test_tui_*.py`, `tests/integration/test_tui_integration.py`, `tests/acceptance/test_tui_acceptance.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and TUI module structure

- [x] T001 Create TUI package structure: `buderus_wps_cli/tui/__init__.py`
- [x] T002 [P] Create screens subpackage: `buderus_wps_cli/tui/screens/__init__.py`
- [x] T003 [P] Create widgets subpackage: `buderus_wps_cli/tui/widgets/__init__.py`
- [x] T004 Add `buderus-tui` CLI entry point in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundation

- [x] T005 [P] Unit test for AppState and ConnectionState in `tests/unit/test_tui_state.py`
- [x] T006 [P] Unit test for keyboard handling in `tests/unit/test_tui_keyboard.py`
- [x] T007 [P] Unit test for base screen class in `tests/unit/test_tui_screens.py`

### Implementation for Foundation

- [x] T008 Implement AppState, ConnectionState, ScreenType enums in `buderus_wps_cli/tui/state.py`
- [x] T009 Implement keyboard key mapping and action dispatch in `buderus_wps_cli/tui/keyboard.py`
- [x] T010 Implement base Screen class with curses wrapper in `buderus_wps_cli/tui/screens/base.py`
- [x] T011 Implement ErrorInfo and ErrorType in `buderus_wps_cli/tui/state.py`
- [x] T012 Implement StatusBar widget in `buderus_wps_cli/tui/widgets/status_bar.py`
- [x] T013 [P] Implement Breadcrumb widget in `buderus_wps_cli/tui/widgets/breadcrumb.py`
- [x] T014 [P] Implement HelpBar widget in `buderus_wps_cli/tui/widgets/help_bar.py`
- [x] T015 Create main application entry point with curses.wrapper in `buderus_wps_cli/tui/app.py`
- [x] T016 Implement connection to MenuAPI in `buderus_wps_cli/tui/app.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - View System Status Dashboard (Priority: P1) 🎯 MVP

**Goal**: Display a status dashboard showing current temperatures and system status on startup

**Independent Test**: Launch application with mock MenuAPI, verify dashboard displays outdoor temp, supply temp, DHW temp, operating mode, and compressor status

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [P] [US1] Unit test for DashboardModel in `tests/unit/test_tui_dashboard.py`
- [ ] T018 [P] [US1] Unit test for DashboardScreen rendering in `tests/unit/test_tui_dashboard.py`
- [ ] T019 [P] [US1] Integration test for dashboard with mocked MenuAPI in `tests/integration/test_tui_integration.py`

### Implementation for User Story 1

- [ ] T020 [US1] Implement DashboardModel dataclass in `buderus_wps_cli/tui/screens/dashboard.py`
- [ ] T021 [US1] Implement DashboardScreen with curses rendering in `buderus_wps_cli/tui/screens/dashboard.py`
- [ ] T022 [US1] Integrate DashboardScreen with StatusView from MenuAPI in `buderus_wps_cli/tui/screens/dashboard.py`
- [ ] T023 [US1] Implement manual refresh ('r' key) handler in `buderus_wps_cli/tui/screens/dashboard.py`
- [ ] T024 [US1] Add connection error display with troubleshooting hints in `buderus_wps_cli/tui/screens/dashboard.py`
- [ ] T025 [US1] Wire dashboard as startup screen in `buderus_wps_cli/tui/app.py`

**Checkpoint**: User Story 1 complete - dashboard displays status, manual refresh works

---

## Phase 4: User Story 2 - Navigate Menu Structure (Priority: P1)

**Goal**: Navigate through menus using arrow keys with breadcrumb display

**Independent Test**: Use arrow keys to navigate from main menu to Hot Water > Temperature, verify correct items are highlighted

### Tests for User Story 2

- [ ] T026 [P] [US2] Unit test for MenuModel and MenuItemModel in `tests/unit/test_tui_menu.py`
- [ ] T027 [P] [US2] Unit test for NavigationState in `tests/unit/test_tui_menu.py`
- [ ] T028 [P] [US2] Unit test for MenuScreen rendering and navigation in `tests/unit/test_tui_menu.py`
- [ ] T029 [P] [US2] Integration test for menu navigation workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 2

- [ ] T030 [US2] Implement MenuModel and MenuItemModel dataclasses in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T031 [US2] Implement NavigationState with path tracking in `buderus_wps_cli/tui/state.py`
- [ ] T032 [US2] Implement MenuScreen with arrow key navigation in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T033 [US2] Integrate MenuScreen with MenuNavigator from MenuAPI in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T034 [US2] Implement breadcrumb display using Breadcrumb widget in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T035 [US2] Add Enter/Escape/Backspace navigation handlers in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T036 [US2] Wire menu screen transition from dashboard (Enter key) in `buderus_wps_cli/tui/app.py`

**Checkpoint**: User Stories 1 AND 2 complete - can view dashboard and navigate full menu structure

---

## Phase 5: User Story 3 - Adjust Hot Water Temperature (Priority: P2)

**Goal**: Edit DHW temperature setpoint with validation

**Independent Test**: Navigate to Hot Water > Temperature, change value, verify validation and write

### Tests for User Story 3

- [ ] T037 [P] [US3] Unit test for EditorModel and ValueType in `tests/unit/test_tui_editor.py`
- [ ] T038 [P] [US3] Unit test for EditorScreen rendering and input handling in `tests/unit/test_tui_editor.py`
- [ ] T039 [P] [US3] Unit test for numeric validation in EditorScreen in `tests/unit/test_tui_editor.py`
- [ ] T040 [P] [US3] Integration test for temperature edit workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 3

- [ ] T041 [US3] Implement EditorModel dataclass with ValueType enum in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T042 [US3] Implement InputField widget for text entry in `buderus_wps_cli/tui/widgets/input_field.py`
- [ ] T043 [US3] Implement EditorScreen with numeric input handling in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T044 [US3] Add validation for min/max range (20-65 for DHW temp) in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T045 [US3] Implement write confirmation display in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T046 [US3] Integrate EditorScreen with HotWaterController from MenuAPI in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T047 [US3] Wire editor transition from menu for writable items in `buderus_wps_cli/tui/app.py`

**Checkpoint**: User Story 3 complete - can edit temperature values with validation

---

## Phase 6: User Story 4 - View and Edit Weekly Schedules (Priority: P2)

**Goal**: Display and modify weekly schedules with 30-minute boundary validation

**Independent Test**: Navigate to Programs > DHW Program 1, view schedule, modify times

### Tests for User Story 4

- [ ] T048 [P] [US4] Unit test for ScheduleModel and DayScheduleModel in `tests/unit/test_tui_schedule.py`
- [ ] T049 [P] [US4] Unit test for ScheduleScreen rendering in `tests/unit/test_tui_schedule.py`
- [ ] T050 [P] [US4] Unit test for 30-minute boundary validation in `tests/unit/test_tui_schedule.py`
- [ ] T051 [P] [US4] Integration test for schedule edit workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 4

- [ ] T052 [US4] Implement ScheduleModel, DayScheduleModel dataclasses in `buderus_wps_cli/tui/screens/schedule.py`
- [ ] T053 [US4] Implement ScheduleScreen with weekly grid display in `buderus_wps_cli/tui/screens/schedule.py`
- [ ] T054 [US4] Add day selection navigation (Up/Down arrows) in `buderus_wps_cli/tui/screens/schedule.py`
- [ ] T055 [US4] Implement time editing with HH:MM format in `buderus_wps_cli/tui/screens/schedule.py`
- [ ] T056 [US4] Add 30-minute boundary validation for times in `buderus_wps_cli/tui/screens/schedule.py`
- [ ] T057 [US4] Integrate with HotWaterController.get_schedule/set_schedule in `buderus_wps_cli/tui/screens/schedule.py`
- [ ] T058 [US4] Wire schedule screen for program menu items in `buderus_wps_cli/tui/app.py`

**Checkpoint**: User Story 4 complete - can view and edit weekly schedules

---

## Phase 7: User Story 5 - Monitor Energy Statistics (Priority: P3)

**Goal**: Display energy consumption statistics (heat generated, aux heater kWh)

**Independent Test**: Navigate to Energy menu, verify kWh values displayed

### Tests for User Story 5

- [ ] T059 [P] [US5] Unit test for energy display rendering in `tests/unit/test_tui_screens.py`
- [ ] T060 [P] [US5] Integration test for energy read workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 5

- [ ] T061 [US5] Add energy statistics display to MenuScreen leaf nodes in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T062 [US5] Integrate with EnergyView from MenuAPI in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T063 [US5] Add refresh support for energy values in `buderus_wps_cli/tui/screens/menu.py`

**Checkpoint**: User Story 5 complete - energy statistics viewable

---

## Phase 8: User Story 6 - View Active Alarms (Priority: P3)

**Goal**: Display active alarms with code, description, timestamp; allow acknowledge

**Independent Test**: Navigate to Alarms, verify alarm list or "No active alarms" message

### Tests for User Story 6

- [ ] T064 [P] [US6] Unit test for alarm list rendering in `tests/unit/test_tui_screens.py`
- [ ] T065 [P] [US6] Unit test for acknowledge action in `tests/unit/test_tui_screens.py`
- [ ] T066 [P] [US6] Integration test for alarm workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 6

- [ ] T067 [US6] Add alarm list display in MenuScreen for Alarms menu in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T068 [US6] Display "No active alarms" when list is empty in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T069 [US6] Integrate with AlarmController from MenuAPI in `buderus_wps_cli/tui/screens/menu.py`
- [ ] T070 [US6] Add acknowledge action for selected alarm in `buderus_wps_cli/tui/screens/menu.py`

**Checkpoint**: User Story 6 complete - alarms viewable and acknowledgeable

---

## Phase 9: User Story 7 - Configure Vacation Mode (Priority: P3)

**Goal**: Set/clear vacation mode with date entry and validation

**Independent Test**: Navigate to Vacation, set start/end dates, verify activation

### Tests for User Story 7

- [ ] T071 [P] [US7] Unit test for vacation date entry in `tests/unit/test_tui_editor.py`
- [ ] T072 [P] [US7] Unit test for date validation (end > start, not in past) in `tests/unit/test_tui_editor.py`
- [ ] T073 [P] [US7] Integration test for vacation workflow in `tests/integration/test_tui_integration.py`

### Implementation for User Story 7

- [ ] T074 [US7] Add DATE value type to EditorScreen in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T075 [US7] Implement date input handling (YYYY-MM-DD format) in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T076 [US7] Add date validation (end after start, not in past) in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T077 [US7] Integrate with VacationController from MenuAPI in `buderus_wps_cli/tui/screens/editor.py`
- [ ] T078 [US7] Add clear vacation action in `buderus_wps_cli/tui/screens/menu.py`

**Checkpoint**: User Story 7 complete - vacation mode configurable

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T079 [P] Add terminal resize handling (KEY_RESIZE) in `buderus_wps_cli/tui/app.py`
- [ ] T080 [P] Add minimum terminal size warning (80x24) in `buderus_wps_cli/tui/app.py`
- [ ] T081 [P] Implement graceful Ctrl+C and 'q' exit in `buderus_wps_cli/tui/app.py`
- [ ] T082 [P] Add connection timeout retry prompt in `buderus_wps_cli/tui/app.py`
- [ ] T083 Acceptance test with pexpect for full user journey in `tests/acceptance/test_tui_acceptance.py`
- [ ] T084 [P] Add --read-only CLI flag to disable writes in `buderus_wps_cli/tui/app.py`
- [ ] T085 [P] Add --verbose CLI flag for debug logging in `buderus_wps_cli/tui/app.py`
- [ ] T086 Run quickstart.md validation scenarios manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 - implement US1 first (dashboard) then US2 (navigation)
  - US3 and US4 are P2 - depend on US2 (menu navigation)
  - US5, US6, US7 are P3 - depend on US2 (menu navigation)
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Dashboard - No dependencies on other stories
- **User Story 2 (P1)**: Menu Navigation - Integrates with US1 (transition from dashboard)
- **User Story 3 (P2)**: Temperature Edit - Requires US2 (menu navigation to reach item)
- **User Story 4 (P2)**: Schedules - Requires US2 (menu navigation to reach schedules)
- **User Story 5 (P3)**: Energy - Requires US2 (menu navigation)
- **User Story 6 (P3)**: Alarms - Requires US2 (menu navigation)
- **User Story 7 (P3)**: Vacation - Requires US2, US3 (navigation + editor for dates)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/dataclasses first
- Screen implementation second
- MenuAPI integration third
- App wiring last
- Story complete before moving to next priority

### Parallel Opportunities

- Setup tasks T002, T003 can run in parallel
- Foundational tests T005, T006, T007 can run in parallel
- Foundational widgets T012, T013, T014 can run in parallel
- US1 tests T017, T018, T019 can run in parallel
- US2 tests T026, T027, T028, T029 can run in parallel
- US3 tests T037, T038, T039, T040 can run in parallel
- US4 tests T048, T049, T050, T051 can run in parallel
- Polish tasks T079, T080, T081, T082, T084, T085 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for DashboardModel in tests/unit/test_tui_dashboard.py"
Task: "Unit test for DashboardScreen rendering in tests/unit/test_tui_dashboard.py"
Task: "Integration test for dashboard with mocked MenuAPI in tests/integration/test_tui_integration.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T016)
3. Complete Phase 3: User Story 1 - Dashboard (T017-T025)
4. **STOP and VALIDATE**: Test dashboard independently with mock MenuAPI
5. Deploy/demo if ready - can view heat pump status!

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (Dashboard) → Test → MVP with status viewing!
3. Add User Story 2 (Navigation) → Test → Can browse full menu structure
4. Add User Story 3 (Temperature Edit) → Test → Can modify DHW temp
5. Add User Story 4 (Schedules) → Test → Can manage weekly schedules
6. Add User Stories 5-7 → Test → Full feature parity
7. Polish → Production ready

### Suggested MVP Scope

**Minimum Viable Product**: User Story 1 (Dashboard) only
- User can view heat pump status (temperatures, operating mode, compressor)
- Manual refresh with 'r' key
- Clean exit with 'q'
- Provides immediate value for monitoring use case

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD per constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Use curses.wrapper for proper terminal cleanup on exit
- Mock curses.stdscr in unit tests to avoid terminal dependency
