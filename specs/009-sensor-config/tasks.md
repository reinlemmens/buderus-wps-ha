# Tasks: Sensor Configuration and Installation Settings

**Input**: Design documents from `/specs/009-sensor-config/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: REQUIRED per Constitution Principle IV (Comprehensive Test Coverage)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add PyYAML dependency and create config module skeleton

- [ ] T001 Add PyYAML to dependencies in pyproject.toml
- [ ] T002 Create config module skeleton in buderus_wps/config.py with docstring and imports
- [ ] T003 [P] Create test file skeleton in tests/unit/test_config.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data classes and enums that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Implement SensorType enum in buderus_wps/config.py
- [ ] T005 [P] Implement CircuitType enum in buderus_wps/config.py
- [ ] T006 Implement SensorMapping dataclass with validation in buderus_wps/config.py
- [ ] T007 [P] Implement CircuitConfig dataclass with validation in buderus_wps/config.py
- [ ] T008 [P] Implement DHWConfig dataclass with has_access() method in buderus_wps/config.py
- [ ] T009 Implement InstallationConfig dataclass skeleton in buderus_wps/config.py
- [ ] T010 Implement _find_config_file() helper for config file search order in buderus_wps/config.py
- [ ] T011 Export config classes from buderus_wps/__init__.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Load Sensor Mappings from Configuration (Priority: P1) MVP

**Goal**: Load CAN broadcast-to-sensor mappings from central configuration

**Independent Test**: Load config file and verify (base, idx) tuples map to correct sensor names

### Tests for User Story 1

- [ ] T012 [P] [US1] Unit test: SensorMapping validation (valid/invalid base, idx) in tests/unit/test_config.py
- [ ] T013 [P] [US1] Unit test: get_default_sensor_map() returns expected mappings in tests/unit/test_config.py
- [ ] T014 [P] [US1] Unit test: load_config() with valid YAML file in tests/unit/test_config.py
- [ ] T015 [P] [US1] Unit test: load_config() with missing file returns defaults in tests/unit/test_config.py
- [ ] T016 [P] [US1] Unit test: load_config() with invalid YAML logs error, returns defaults in tests/unit/test_config.py
- [ ] T017 [P] [US1] Integration test: TUI uses shared config mappings in tests/integration/test_config_integration.py

### Implementation for User Story 1

- [ ] T018 [US1] Define DEFAULT_SENSOR_MAPPINGS constant with verified CAN addresses in buderus_wps/config.py
- [ ] T019 [US1] Implement get_default_sensor_map() function in buderus_wps/config.py
- [ ] T020 [US1] Implement get_default_config() function in buderus_wps/config.py
- [ ] T021 [US1] Implement _parse_sensor_mappings() helper for YAML parsing in buderus_wps/config.py
- [ ] T022 [US1] Implement load_config() function with file search and fallback in buderus_wps/config.py
- [ ] T023 [US1] Implement InstallationConfig.get_sensor_map() method in buderus_wps/config.py
- [ ] T024 [US1] Update TUI app.py to import TEMP_BROADCAST_MAP from config module in buderus_wps_cli/tui/app.py
- [ ] T025 [US1] Remove hardcoded TEMP_BROADCAST_MAP from buderus_wps_cli/tui/app.py

**Checkpoint**: Sensor mappings load from config file, TUI uses shared config

---

## Phase 4: User Story 2 - Configure Installation-Specific Circuit Layout (Priority: P2)

**Goal**: Define heating circuits with type and apartment assignment

**Independent Test**: Load config with circuit definitions, verify circuit metadata accessible via API

### Tests for User Story 2

- [ ] T026 [P] [US2] Unit test: CircuitConfig validation (valid/invalid number) in tests/unit/test_config.py
- [ ] T027 [P] [US2] Unit test: InstallationConfig.get_circuit() returns correct circuit in tests/unit/test_config.py
- [ ] T028 [P] [US2] Unit test: InstallationConfig.get_circuits_by_apartment() groups correctly in tests/unit/test_config.py
- [ ] T029 [P] [US2] Unit test: Default circuits when no config exists in tests/unit/test_config.py

### Implementation for User Story 2

- [ ] T030 [US2] Implement _parse_circuits() helper for YAML parsing in buderus_wps/config.py
- [ ] T031 [US2] Implement InstallationConfig.get_circuit() method in buderus_wps/config.py
- [ ] T032 [US2] Implement InstallationConfig.get_circuits_by_apartment() method in buderus_wps/config.py
- [ ] T033 [US2] Implement default circuit configuration in get_default_config() in buderus_wps/config.py
- [ ] T034 [US2] Integrate circuit parsing into load_config() in buderus_wps/config.py

**Checkpoint**: Circuit configuration loads and is queryable by number or apartment

---

## Phase 5: User Story 3 - Configure DHW Distribution (Priority: P2)

**Goal**: Specify which apartments receive domestic hot water

**Independent Test**: Load config with DHW settings, verify apartment access queries work correctly

### Tests for User Story 3

- [ ] T035 [P] [US3] Unit test: DHWConfig.has_access() returns true for listed apartment in tests/unit/test_config.py
- [ ] T036 [P] [US3] Unit test: DHWConfig.has_access() returns false for unlisted apartment in tests/unit/test_config.py
- [ ] T037 [P] [US3] Unit test: DHWConfig.has_access() returns true for all when apartments=None in tests/unit/test_config.py

### Implementation for User Story 3

- [ ] T038 [US3] Implement _parse_dhw() helper for YAML parsing in buderus_wps/config.py
- [ ] T039 [US3] Integrate DHW parsing into load_config() in buderus_wps/config.py

**Checkpoint**: DHW access can be queried per apartment

---

## Phase 6: User Story 4 - Custom Sensor Labels (Priority: P3)

**Goal**: Allow custom human-readable labels for sensors

**Independent Test**: Load config with custom labels, verify get_label() returns custom or default

### Tests for User Story 4

- [ ] T040 [P] [US4] Unit test: InstallationConfig.get_label() returns custom label when defined in tests/unit/test_config.py
- [ ] T041 [P] [US4] Unit test: InstallationConfig.get_label() returns default label when not defined in tests/unit/test_config.py

### Implementation for User Story 4

- [ ] T042 [US4] Define DEFAULT_SENSOR_LABELS constant in buderus_wps/config.py
- [ ] T043 [US4] Implement _parse_labels() helper for YAML parsing in buderus_wps/config.py
- [ ] T044 [US4] Implement InstallationConfig.get_label() method in buderus_wps/config.py
- [ ] T045 [US4] Integrate labels parsing into load_config() in buderus_wps/config.py

**Checkpoint**: Custom labels work, defaults used when not specified

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, documentation, and validation

- [ ] T046 [P] Create example config file at examples/buderus-wps.yaml
- [ ] T047 [P] Add acceptance tests for all user story scenarios in tests/acceptance/test_config_acceptance.py
- [ ] T048 Update TUI to use get_label() for temperature display in buderus_wps_cli/tui/app.py
- [ ] T049 Run all tests and verify coverage in tests/
- [ ] T050 Run quickstart.md validation scenarios manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Foundational
  - US2 (P2): Can start after Foundational (independent of US1)
  - US3 (P2): Can start after Foundational (independent of US1, US2)
  - US4 (P3): Can start after Foundational (independent of others)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - MVP standalone
- **User Story 2 (P2)**: No dependencies on US1 - independent
- **User Story 3 (P2)**: No dependencies on US1/US2 - independent
- **User Story 4 (P3)**: No dependencies on other stories - independent

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation follows: helpers → methods → integration
- Story complete before moving to next priority

### Parallel Opportunities

- Setup tasks T001-T003: T003 can run in parallel with T001-T002
- Foundational T004-T011: T005, T007, T008 can run in parallel after T004
- Once Foundational completes, ALL user stories can start in parallel
- Tests within each story can all run in parallel
- Different user stories can be worked on by different developers

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test: SensorMapping validation in tests/unit/test_config.py"
Task: "Unit test: get_default_sensor_map() in tests/unit/test_config.py"
Task: "Unit test: load_config() with valid YAML in tests/unit/test_config.py"
Task: "Unit test: load_config() missing file in tests/unit/test_config.py"
Task: "Unit test: load_config() invalid YAML in tests/unit/test_config.py"
Task: "Integration test: TUI uses shared config in tests/integration/test_config_integration.py"

# After tests written and failing, implementation is sequential
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T011)
3. Complete Phase 3: User Story 1 (T012-T025)
4. **STOP and VALIDATE**: Test sensor mapping loading independently
5. Deploy if ready - TUI now uses configurable mappings

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test → Deploy (MVP: configurable sensor mappings)
3. Add User Story 2 → Test → Deploy (circuits configurable)
4. Add User Story 3 → Test → Deploy (DHW distribution)
5. Add User Story 4 → Test → Deploy (custom labels)

### Parallel Team Strategy

With multiple developers after Foundational phase:
- Developer A: User Story 1 (sensor mappings)
- Developer B: User Story 2 (circuits)
- Developer C: User Story 3 (DHW) + User Story 4 (labels)

---

## Notes

- [P] tasks = different files or independent sections, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (TDD per Constitution)
- Commit after each task or logical group
- All YAML loading MUST use yaml.safe_load() (security requirement from research.md)
