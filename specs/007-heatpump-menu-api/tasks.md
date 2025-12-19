# Tasks: Heat Pump Menu API

**Input**: Design documents from `/specs/007-heatpump-menu-api/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: REQUIRED per constitution (TDD mandatory, 100% coverage for described functionality)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US9)
- Include exact file paths in descriptions

## Path Conventions
- Source: `buderus_wps/` at repository root
- Tests: `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/acceptance/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and new module structure

- [x] T001 Create new module files per plan structure in buderus_wps/
- [x] T002 [P] Create exception classes in buderus_wps/exceptions.py (extend existing)
- [x] T003 [P] Create enumeration types in buderus_wps/enums.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 [P] Create ScheduleSlot dataclass in buderus_wps/schedule_codec.py
- [x] T005 [P] Create WeeklySchedule dataclass in buderus_wps/schedule_codec.py
- [x] T006 [P] Create VacationPeriod dataclass in buderus_wps/menu_api.py
- [x] T007 [P] Create Alarm and AlarmEntry dataclasses in buderus_wps/menu_api.py
- [x] T008 [P] Create StatusSnapshot dataclass in buderus_wps/menu_api.py
- [x] T009 [P] Create MenuItem dataclass in buderus_wps/menu_structure.py
- [x] T010 Implement ScheduleCodec.time_to_slot() in buderus_wps/schedule_codec.py
- [x] T011 Implement ScheduleCodec.slot_to_time() in buderus_wps/schedule_codec.py
- [x] T012 Implement ScheduleCodec.encode() in buderus_wps/schedule_codec.py
- [x] T013 Implement ScheduleCodec.decode() in buderus_wps/schedule_codec.py
- [x] T014 Implement ScheduleCodec.get_sw2_read_index() for odd-index fix in buderus_wps/schedule_codec.py
- [x] T015 [P] Contract test for schedule encoding in tests/contract/test_schedule_encoding.py
- [x] T016 [P] Unit tests for ScheduleCodec in tests/unit/test_schedule_codec.py
- [x] T017 Define menu hierarchy constants in buderus_wps/menu_structure.py (parameter-to-menu mappings)
- [x] T018 Create MenuAPI base class with client reference in buderus_wps/menu_api.py
- [x] T019 Update buderus_wps/__init__.py with new exports

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Read Current System Status (Priority: P1) 🎯 MVP

**Goal**: Read temperatures and operational status from heat pump dashboard

**Independent Test**: Call API to read 4 temperatures + status, verify values match physical display

### Tests for User Story 1

- [x] T020 [P] [US1] Unit test for StatusView in tests/unit/test_menu_api.py
- [x] T021 [P] [US1] Integration test for status reading with mocked HeatPumpClient in tests/integration/test_menu_api_integration.py
- [x] T022 [P] [US1] Acceptance test for US1 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 1

- [x] T023 [P] [US1] Create parameter mappings for temperature parameters (OUTDOOR_TEMP, SUPPLY_TEMP, etc.) in buderus_wps/menu_structure.py
- [x] T024 [US1] Implement StatusView class with temperature properties in buderus_wps/menu_api.py
- [x] T025 [US1] Implement StatusView.operating_mode property in buderus_wps/menu_api.py
- [x] T026 [US1] Implement StatusView.compressor_running and compressor_hours in buderus_wps/menu_api.py
- [x] T027 [US1] Implement StatusView.read_all() batch operation (<2 sec) in buderus_wps/menu_api.py
- [x] T028 [US1] Wire MenuAPI.status property to StatusView in buderus_wps/menu_api.py

**Checkpoint**: User Story 1 complete - can read all status/temperatures independently

---

## Phase 4: User Story 2 - Navigate Menu Structure (Priority: P1)

**Goal**: Explore available settings via hierarchical menu navigation

**Independent Test**: List menu items and compare against user manual Table 3

### Tests for User Story 2

- [x] T029 [P] [US2] Unit test for MenuItem and MenuNavigator in tests/unit/test_menu_structure.py
- [x] T030 [P] [US2] Integration test for menu navigation in tests/integration/test_menu_api_integration.py
- [x] T031 [P] [US2] Acceptance test for US2 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 2

- [x] T032 [P] [US2] Define complete menu hierarchy tree in buderus_wps/menu_structure.py
- [x] T033 [US2] Implement MenuNavigator class with navigate() method in buderus_wps/menu_api.py
- [x] T034 [US2] Implement MenuNavigator.items() and up() methods in buderus_wps/menu_api.py
- [x] T035 [US2] Implement MenuNavigator.get_value() and set_value() in buderus_wps/menu_api.py
- [x] T036 [US2] Add help/description text for menu items in buderus_wps/menu_structure.py
- [x] T037 [US2] Wire MenuAPI.menu property to MenuNavigator in buderus_wps/menu_api.py

**Checkpoint**: User Stories 1 AND 2 complete - status reading and menu navigation work

---

## Phase 5: User Story 3 - Hot Water Settings (Priority: P2)

**Goal**: Read and modify DHW temperature and settings

**Independent Test**: Read DHW temp, modify within 20-65 range, verify change persists

### Tests for User Story 3

- [x] T038 [P] [US3] Unit test for HotWaterController in tests/unit/test_menu_api.py
- [x] T039 [P] [US3] Integration test for DHW operations in tests/integration/test_menu_api_integration.py
- [x] T040 [P] [US3] Acceptance test for US3 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 3

- [x] T041 [P] [US3] Create DHW parameter mappings (DHW_SETTEMP, etc.) in buderus_wps/menu_structure.py
- [x] T042 [US3] Implement HotWaterController class with temperature property in buderus_wps/menu_api.py
- [x] T043 [US3] Implement HotWaterController.extra_duration and stop_temperature in buderus_wps/menu_api.py
- [x] T044 [US3] Implement HotWaterController.program_mode property in buderus_wps/menu_api.py
- [x] T045 [US3] Add validation for temperature range (20-65) with ValidationError in buderus_wps/menu_api.py
- [x] T046 [US3] Wire MenuAPI.hot_water property to HotWaterController in buderus_wps/menu_api.py

**Checkpoint**: User Story 3 complete - can control DHW temperature settings

---

## Phase 6: User Story 4 - Weekly Schedules (Priority: P2)

**Goal**: View and modify weekly heating and DHW schedules

**Independent Test**: Read DHW P1 Monday schedule, modify times, verify change

### Tests for User Story 4

- [x] T047 [P] [US4] Unit test for schedule read/write in tests/unit/test_menu_api.py
- [x] T048 [P] [US4] Integration test for schedule operations in tests/integration/test_menu_api_integration.py
- [x] T049 [P] [US4] Acceptance test for US4 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 4

- [x] T050 [P] [US4] Create DHW schedule parameter mappings (sw2 format, odd indices) in buderus_wps/menu_structure.py
- [x] T051 [US4] Implement HotWaterController.get_schedule() using sw2 decoder in buderus_wps/menu_api.py
- [x] T052 [US4] Implement HotWaterController.set_schedule() with 30-min validation in buderus_wps/menu_api.py
- [x] T053 [US4] Add room schedule parameter mappings (sw1 format) in buderus_wps/menu_structure.py
- [x] T054 [US4] Implement Circuit.get_schedule() using sw1 decoder in buderus_wps/menu_api.py
- [x] T055 [US4] Implement Circuit.set_schedule() in buderus_wps/menu_api.py

**Checkpoint**: User Story 4 complete - can read/write weekly schedules

---

## Phase 7: User Story 5 - Control Operating Modes (Priority: P2)

**Goal**: Switch program modes and summer/winter settings

**Independent Test**: Read current mode, switch to different mode, verify change

### Tests for User Story 5

- [x] T056 [P] [US5] Unit test for program mode control in tests/unit/test_menu_api.py
- [x] T057 [P] [US5] Integration test for mode switching in tests/integration/test_menu_api_integration.py
- [x] T058 [P] [US5] Acceptance test for US5 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 5

- [x] T059 [P] [US5] Create program mode parameter mappings in buderus_wps/menu_structure.py
- [x] T060 [US5] Implement Circuit.program_mode property with RoomProgramMode enum in buderus_wps/menu_api.py
- [x] T061 [US5] Implement Circuit.summer_mode and summer_threshold properties in buderus_wps/menu_api.py
- [x] T062 [US5] Add program mode validation in buderus_wps/menu_api.py

**Checkpoint**: User Story 5 complete - can control operating modes

---

## Phase 8: User Story 9 - Vacation Mode (Priority: P2)

**Goal**: Configure vacation mode for circuits and DHW

**Independent Test**: Set vacation dates, verify reduced operation, clear vacation

### Tests for User Story 9

- [x] T063 [P] [US9] Unit test for VacationController in tests/unit/test_menu_api.py
- [x] T064 [P] [US9] Integration test for vacation mode in tests/integration/test_menu_api_integration.py
- [x] T065 [P] [US9] Acceptance test for US9 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 9

- [x] T066 [P] [US9] Create vacation parameter mappings in buderus_wps/menu_structure.py
- [x] T067 [US9] Implement VacationController class in buderus_wps/menu_api.py
- [x] T068 [US9] Implement VacationController.get_circuit() and set_circuit() in buderus_wps/menu_api.py
- [x] T069 [US9] Implement VacationController.clear_circuit() in buderus_wps/menu_api.py
- [x] T070 [US9] Implement VacationController.hot_water property and methods in buderus_wps/menu_api.py
- [x] T071 [US9] Wire MenuAPI.vacation property to VacationController in buderus_wps/menu_api.py

**Checkpoint**: User Story 9 complete - can configure vacation mode

---

## Phase 9: User Story 6 - Energy Statistics (Priority: P3)

**Goal**: Monitor energy consumption and heat production

**Independent Test**: Read energy values, compare against physical display Energy menu

### Tests for User Story 6

- [x] T072 [P] [US6] Unit test for EnergyView in tests/unit/test_menu_api.py
- [x] T073 [P] [US6] Integration test for energy reading in tests/integration/test_menu_api_integration.py
- [x] T074 [P] [US6] Acceptance test for US6 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 6

- [x] T075 [P] [US6] Create energy parameter mappings in buderus_wps/menu_structure.py
- [x] T076 [US6] Implement EnergyView class in buderus_wps/menu_api.py
- [x] T077 [US6] Wire MenuAPI.energy property to EnergyView in buderus_wps/menu_api.py

**Checkpoint**: User Story 6 complete - can read energy statistics

---

## Phase 10: User Story 7 - Alarms (Priority: P3)

**Goal**: Read alarm log and acknowledge/clear alarms

**Independent Test**: Read alarm log, acknowledge alarm, verify status change

### Tests for User Story 7

- [x] T078 [P] [US7] Unit test for AlarmController in tests/unit/test_menu_api.py
- [x] T079 [P] [US7] Integration test for alarm operations in tests/integration/test_menu_api_integration.py
- [x] T080 [P] [US7] Acceptance test for US7 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 7

- [x] T081 [P] [US7] Create alarm parameter mappings in buderus_wps/menu_structure.py
- [x] T082 [US7] Implement AlarmController class with active_alarms property in buderus_wps/menu_api.py
- [x] T083 [US7] Implement AlarmController.alarm_log and info_log properties in buderus_wps/menu_api.py
- [x] T084 [US7] Implement AlarmController.acknowledge() method in buderus_wps/menu_api.py
- [x] T085 [US7] Implement AlarmController.clear() with clearable check in buderus_wps/menu_api.py
- [x] T086 [US7] Wire MenuAPI.alarms property to AlarmController in buderus_wps/menu_api.py

**Checkpoint**: User Story 7 complete - can manage alarms

---

## Phase 11: User Story 8 - Multi-Circuit Configuration (Priority: P3)

**Goal**: Access and configure multiple heating circuits (1-4)

**Independent Test**: List circuits, read settings for each, verify circuit-specific values

### Tests for User Story 8

- [x] T087 [P] [US8] Unit test for Circuit class in tests/unit/test_menu_api.py
- [x] T088 [P] [US8] Integration test for multi-circuit operations in tests/integration/test_menu_api_integration.py
- [x] T089 [P] [US8] Acceptance test for US8 scenarios in tests/acceptance/test_user_stories.py

### Implementation for User Story 8

- [x] T090 [P] [US8] Create circuit-specific parameter mappings (_C1, _C2, etc.) in buderus_wps/menu_structure.py
- [x] T091 [US8] Implement Circuit class with number and circuit_type properties in buderus_wps/menu_api.py
- [x] T092 [US8] Implement Circuit temperature and setpoint properties in buderus_wps/menu_api.py
- [x] T093 [US8] Implement MenuAPI.get_circuit() with CircuitNotAvailableError in buderus_wps/menu_api.py
- [x] T094 [US8] Add circuit availability detection (which circuits are configured) in buderus_wps/menu_api.py

**Checkpoint**: User Story 8 complete - can access all configured circuits

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Integration, documentation, and final validation

- [x] T095 [P] Full acceptance test suite covering all 9 user stories in tests/acceptance/test_user_stories.py
- [x] T096 [P] Validate quickstart.md examples work correctly
- [x] T097 Add docstrings and type hints to all public methods in buderus_wps/menu_api.py
- [x] T098 Update CLAUDE.md with feature 007 context
- [x] T099 Run full test suite and verify 100% coverage for new code
- [x] T100 Performance validation: read_all() <2 seconds, navigation <5 seconds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phases 3-11)**: All depend on Foundational phase
  - Stories can proceed in parallel if staffed
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 12)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Priority | Depends On | Notes |
|-------|----------|------------|-------|
| US1 | P1 | Foundational | MVP - Status reading |
| US2 | P1 | Foundational | Menu navigation |
| US3 | P2 | Foundational | DHW control |
| US4 | P2 | Foundational, US3 (partial) | Uses HotWaterController |
| US5 | P2 | Foundational | Mode control |
| US9 | P2 | Foundational | Vacation mode |
| US6 | P3 | Foundational | Energy stats |
| US7 | P3 | Foundational | Alarms |
| US8 | P3 | Foundational, US4, US5 | Uses Circuit class |

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Parameter mappings before controller implementation
3. Controller implementation before MenuAPI wiring
4. Integration tests verify correct behavior

### Parallel Opportunities

**Phase 2 (Foundational)**:
```
Parallel Group 1: T004, T005, T006, T007, T008, T009 (all dataclasses)
Parallel Group 2: T015, T016 (tests, after T010-T014)
```

**User Story Tests (within each story)**:
```
All test tasks marked [P] can run in parallel
Example US1: T020, T021, T022 can all start together
```

**Cross-Story Parallelism**:
```
After Foundational complete:
- Team A: US1 (P1)
- Team B: US2 (P1)
- Team C: US3 (P2) - can start after US1/US2 if single developer
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (Status Reading)
4. **STOP and VALIDATE**: Test status reading independently
5. Deploy/demo MVP

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Test → MVP! (can read temperatures)
3. US2 → Test → Enhanced (menu navigation)
4. US3 → Test → DHW control
5. US4 → Test → Schedule management
6. US5, US9 → Test → Mode and vacation control
7. US6, US7, US8 → Test → Full feature set
8. Polish → Production ready

### Single Developer Strategy

Recommended order for sequential implementation:
1. Phase 1-2: Setup + Foundational
2. US1 (P1): Foundation feature
3. US2 (P1): Menu navigation
4. US3 (P2): Hot water basics
5. US4 (P2): Schedules (builds on US3)
6. US5 (P2): Operating modes
7. US9 (P2): Vacation mode
8. US8 (P3): Multi-circuit (uses US4/US5)
9. US6 (P3): Energy (simple read-only)
10. US7 (P3): Alarms (last due to complexity)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story
- Each story independently completable and testable
- TDD required: verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- sw2 odd-index (+1) for DHW schedule reads (research.md)
- 30-minute boundary validation for DHW schedules
