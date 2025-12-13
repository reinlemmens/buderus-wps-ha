# Tasks: Home Assistant Integration

**Input**: Design documents from `/specs/011-ha-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required per constitution (Principle IV: Comprehensive Test Coverage)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions
- **Integration code**: `custom_components/buderus_wps/`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/acceptance/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the codebase for modifications and establish test infrastructure

- [x] T001 Create test directory structure for HA integration tests in tests/unit/, tests/integration/, tests/acceptance/
- [x] T002 [P] Create pytest fixtures for mocking HA and buderus_wps library in tests/conftest.py
- [x] T003 [P] Add pytest-asyncio to test dependencies in pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure changes that MUST be complete before ANY user story can be finalized

**⚠️ CRITICAL**: These changes affect ALL entities and must be done first

- [x] T004 Update device name from "Buderus WPS Heat Pump" to "Heat Pump" in custom_components/buderus_wps/entity.py
- [x] T005 Add scan_interval validation (range 10-300) in custom_components/buderus_wps/__init__.py
- [x] T006 Add exponential backoff constants (BACKOFF_INITIAL=5, BACKOFF_MAX=120) in custom_components/buderus_wps/const.py
- [x] T007 Implement exponential backoff reconnection logic in custom_components/buderus_wps/coordinator.py
- [x] T008 Update BuderusData dataclass to change dhw_extra_active to dhw_extra_duration (int) in custom_components/buderus_wps/coordinator.py
- [x] T009 Update _sync_fetch_data to read DHW extra as duration instead of boolean in custom_components/buderus_wps/coordinator.py
- [x] T010 Add async_set_dhw_extra_duration method (replaces async_set_dhw_extra) in custom_components/buderus_wps/coordinator.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Monitor Heat Pump Temperatures (Priority: P1) 🎯 MVP

**Goal**: Five temperature sensors appear in HA with accurate readings from heat pump

**Independent Test**: Add integration, verify 5 temperature sensors appear with °C readings

### Tests for User Story 1

- [x] T011 [P] [US1] Unit test for temperature sensor entity in tests/unit/test_ha_sensor.py
- [x] T012 [P] [US1] Integration test for sensor data flow in tests/integration/test_ha_temperature.py
- [x] T013 [P] [US1] Acceptance test: 5 sensors appear on startup in tests/acceptance/test_ha_us1_temperature.py
- [x] T014 [P] [US1] Acceptance test: sensors show unavailable on disconnect in tests/acceptance/test_ha_us1_temperature.py

### Implementation for User Story 1

- [x] T015 [US1] Update SENSOR_NAMES with "Heat Pump" prefixed names in custom_components/buderus_wps/const.py
- [x] T016 [US1] Update BuderusTemperatureSensor._attr_name to use prefixed names in custom_components/buderus_wps/sensor.py
- [x] T017 [US1] Verify sensor device_class, unit, state_class are correct in custom_components/buderus_wps/sensor.py

**Checkpoint**: User Story 1 complete - 5 temperature sensors with "Heat Pump X Temperature" names

---

## Phase 4: User Story 2 - View Compressor Status (Priority: P1)

**Goal**: Binary sensor shows compressor running/stopped status in HA

**Independent Test**: Observe binary sensor state while heat pump cycles

### Tests for User Story 2

- [x] T018 [P] [US2] Unit test for compressor binary sensor entity in tests/unit/test_ha_binary_sensor.py
- [x] T019 [P] [US2] Integration test for compressor state updates in tests/integration/test_ha_compressor.py
- [x] T020 [P] [US2] Acceptance test: compressor shows Running/Stopped in tests/acceptance/test_ha_us2_compressor.py

### Implementation for User Story 2

- [x] T021 [US2] Update BuderusCompressorSensor._attr_name to "Compressor" (device prefixes it) in custom_components/buderus_wps/binary_sensor.py
- [x] T022 [US2] Verify device_class is BinarySensorDeviceClass.RUNNING in custom_components/buderus_wps/binary_sensor.py

**Checkpoint**: User Story 2 complete - compressor binary sensor with "Heat Pump Compressor" name

---

## Phase 5: User Story 3 - Control Energy Blocking (Priority: P2)

**Goal**: Switch entity to enable/disable energy blocking via HA

**Independent Test**: Toggle switch and verify heat pump stops/resumes heating

### Tests for User Story 3

- [x] T023 [P] [US3] Unit test for energy block switch entity in tests/unit/test_ha_switch.py
- [x] T024 [P] [US3] Integration test for energy blocking commands in tests/integration/test_ha_energy_block.py
- [x] T025 [P] [US3] Acceptance test: switch toggles blocking in tests/acceptance/test_ha_us3_energy_block.py
- [x] T026 [P] [US3] Acceptance test: switch reflects current state on load in tests/acceptance/test_ha_us3_energy_block.py

### Implementation for User Story 3

- [x] T027 [US3] Update BuderusEnergyBlockSwitch._attr_name to "Energy Block" in custom_components/buderus_wps/switch.py
- [x] T028 [US3] Remove BuderusDHWExtraSwitch class from custom_components/buderus_wps/switch.py
- [x] T029 [US3] Update async_setup_platform to only register energy block switch in custom_components/buderus_wps/switch.py

**Checkpoint**: User Story 3 complete - energy block switch with "Heat Pump Energy Block" name

---

## Phase 6: User Story 4 - Control DHW Extra Production (Priority: P2)

**Goal**: Number entity (0-24 hours) to set DHW extra production duration

**Independent Test**: Set duration and observe DHW temperature increase

### Tests for User Story 4

- [x] T030 [P] [US4] Unit test for DHW extra number entity in tests/unit/test_ha_number.py
- [x] T031 [P] [US4] Integration test for DHW extra duration commands in tests/integration/test_ha_dhw_extra.py
- [x] T032 [P] [US4] Acceptance test: setting duration starts production in tests/acceptance/test_ha_us4_dhw_extra.py
- [x] T033 [P] [US4] Acceptance test: setting 0 stops production in tests/acceptance/test_ha_us4_dhw_extra.py
- [x] T034 [P] [US4] Acceptance test: slider shows remaining duration in tests/acceptance/test_ha_us4_dhw_extra.py

### Implementation for User Story 4

- [x] T035 [US4] Create BuderusDHWExtraDurationNumber entity class in custom_components/buderus_wps/number.py
- [x] T036 [US4] Set NumberEntity attributes: min=0, max=24, step=1, unit="h", mode=SLIDER in custom_components/buderus_wps/number.py
- [x] T037 [US4] Implement native_value property to return coordinator.data.dhw_extra_duration in custom_components/buderus_wps/number.py
- [x] T038 [US4] Implement async_set_native_value to call coordinator.async_set_dhw_extra_duration in custom_components/buderus_wps/number.py
- [x] T039 [US4] Create async_setup_platform for number platform in custom_components/buderus_wps/number.py
- [x] T040 [US4] Add Platform.NUMBER to PLATFORMS list in custom_components/buderus_wps/__init__.py

**Checkpoint**: User Story 4 complete - DHW extra number with "Heat Pump DHW Extra Duration" name

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge case handling, documentation, and final validation

- [x] T041 [P] Test exponential backoff reconnection logic in tests/integration/test_ha_reconnection.py
- [x] T042 [P] Test scan_interval validation (reject <10 or >300) in tests/unit/test_ha_config.py
- [x] T043 [P] Update select entity names with "Heat Pump" prefix in custom_components/buderus_wps/select.py
- [x] T044 Verify all entities have correct icons (mdi:*) in custom_components/buderus_wps/
- [x] T045 Run all tests and ensure 100% pass rate (117 passed)
- [x] T046 [P] Update manifest.json version to 0.2.0 in custom_components/buderus_wps/manifest.json
- [x] T047 Validate quickstart.md instructions work end-to-end

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phases 3-6 (User Stories)**: All depend on Phase 2 completion
  - US1 and US2 can run in parallel (both P1)
  - US3 and US4 can run in parallel (both P2)
  - Or run sequentially: US1 → US2 → US3 → US4
- **Phase 7 (Polish)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 2 (Foundational)
       │
       ├───────────┬───────────┐
       ▼           ▼           │
     US1 ◄───► US2            │
  (P1: Temp)  (P1: Compressor) │
       │           │           │
       └─────┬─────┘           │
             │                 │
       ├─────┴─────┐           │
       ▼           ▼           │
     US3 ◄───► US4 ◄──────────┘
  (P2: Block) (P2: DHW)
```

All user stories are independently testable after Phase 2.

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Implementation tasks follow test tasks
3. Story complete when all tests pass

### Parallel Opportunities

**Phase 1**: T002 and T003 can run in parallel
**Phase 2**: T004-T010 must be sequential (same files)
**Phase 3 (US1)**: T011-T014 tests can run in parallel, then T015-T017
**Phase 4 (US2)**: T018-T020 tests can run in parallel, then T021-T022
**Phase 5 (US3)**: T023-T026 tests can run in parallel, then T027-T029
**Phase 6 (US4)**: T030-T034 tests can run in parallel, then T035-T040
**Phase 7**: T041-T043 and T046 can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for temperature sensor entity in tests/unit/test_ha_sensor.py"
Task: "Integration test for sensor data flow in tests/integration/test_ha_temperature.py"
Task: "Acceptance test: 5 sensors appear on startup in tests/acceptance/test_ha_us1_temperature.py"
Task: "Acceptance test: sensors show unavailable on disconnect in tests/acceptance/test_ha_us1_temperature.py"

# After tests written and failing, implement sequentially:
Task: "Update SENSOR_NAMES with Heat Pump prefixed names in custom_components/buderus_wps/const.py"
Task: "Update BuderusTemperatureSensor._attr_name to use prefixed names in custom_components/buderus_wps/sensor.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T010)
3. Complete Phase 3: User Story 1 (T011-T017)
4. Complete Phase 4: User Story 2 (T018-T022)
5. **STOP and VALIDATE**: Test temperature sensors + compressor independently
6. Deploy/demo if ready

### Full Implementation

1. Complete Setup + Foundational
2. Add User Story 1 → Test independently ✓
3. Add User Story 2 → Test independently ✓
4. Add User Story 3 → Test independently ✓
5. Add User Story 4 → Test independently ✓
6. Complete Polish phase
7. Full validation with quickstart.md

### Parallel Team Strategy

With 2 developers after Foundational:

- Developer A: US1 (P1 Temperature) → US3 (P2 Energy Block)
- Developer B: US2 (P1 Compressor) → US4 (P2 DHW Extra)

---

## Notes

- [P] tasks = different files, no dependencies
- [US#] label maps task to specific user story
- TDD required: write tests first, ensure they fail, then implement
- Existing code is being modified, not created from scratch
- DHW extra is the major change (switch → number entity)
- Entity naming change affects all entities
- Exponential backoff is infrastructure, not user-story-specific
- Commit after each task or logical group
- Run `pytest` after each user story phase completion
