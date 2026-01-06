# Tasks: DHW Setpoint Temperature Parameter

**Input**: Design documents from `/specs/017-dhw-setpoint-temp/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1, US2, US3, US4)
- File paths are absolute from repository root

---

## Phase 1: Setup

**Purpose**: Verify prerequisites are in place (no new setup needed)

- [x] T001 Verify `DHW_CALCULATED_SETPOINT_TEMP` exists in buderus_wps/parameter_defaults.py at idx 385

**Note**: Parameter already defined. No additional setup required.

---

## Phase 2: Foundational (Coordinator Infrastructure)

**Purpose**: Add data model field and coordinator methods that both US1 and US2 depend on

**⚠️ CRITICAL**: US1/US2 implementation cannot begin until this phase is complete

- [x] T002 Add `dhw_setpoint: float | None` field to `BuderusData` dataclass in custom_components/buderus_wps/coordinator.py
- [x] T003 Add DHW setpoint read logic to `_sync_fetch_data()` method in custom_components/buderus_wps/coordinator.py
- [x] T004 Add `async_set_dhw_setpoint()` and `_sync_set_dhw_setpoint()` methods to coordinator in custom_components/buderus_wps/coordinator.py

**Checkpoint**: Coordinator can now read and write DHW setpoint - entity can be implemented

---

## Phase 3: User Story 1 & 2 - View and Adjust DHW Setpoint (Priority: P1) MVP

**Goal**: Users can view and adjust the DHW setpoint temperature from Home Assistant

**Independent Test**: Connect to heat pump, verify entity shows correct value, change value via HA slider, verify heat pump accepts new setpoint

**Note**: US1 (View) and US2 (Adjust) are implemented together as a single Number entity with both read and write capability.

### Implementation for User Stories 1 & 2

- [x] T005 [US1][US2] Create `BuderusDHWSetpointNumber` entity class in custom_components/buderus_wps/number.py
- [x] T006 [US1][US2] Register `BuderusDHWSetpointNumber` in `async_setup_entry()` in custom_components/buderus_wps/number.py
- [x] T007 [US1][US2] Add `ICON_WATER_THERMOMETER` constant if not present in custom_components/buderus_wps/const.py

### Tests for User Stories 1 & 2

- [x] T008 [P] [US1][US2] Add unit tests for `BuderusDHWSetpointNumber` properties in tests/unit/test_ha_number.py
- [x] T009 [P] [US1][US2] Add coordinator method tests in tests/unit/test_coordinator.py (if exists) or tests/integration/

**Checkpoint**: DHW Setpoint Temperature entity is visible in HA and accepts value changes

---

## Phase 4: User Story 3 - CLI Read/Write (Priority: P2)

**Goal**: Developers can read and write DHW setpoint via CLI commands

**Independent Test**: Run `buderus-wps read DHW_CALCULATED_SETPOINT_TEMP` and `buderus-wps write DHW_CALCULATED_SETPOINT_TEMP 52.0`

**Note**: NO NEW CODE REQUIRED - existing CLI infrastructure already supports reading/writing any parameter defined in parameter_defaults.py

### Verification for User Story 3

- [ ] T010 [US3] Verify CLI read works: `python -m buderus_wps.cli read DHW_CALCULATED_SETPOINT_TEMP`
- [ ] T011 [US3] Verify CLI write works: `python -m buderus_wps.cli write DHW_CALCULATED_SETPOINT_TEMP 52.0`
- [ ] T012 [P] [US3] Add CLI usage example to specs/017-dhw-setpoint-temp/quickstart.md

**Checkpoint**: CLI commands work for DHW setpoint parameter

---

## Phase 5: User Story 4 - Automation Support (Priority: P2)

**Goal**: Users can include DHW setpoint in Home Assistant automations

**Independent Test**: Create automation that changes setpoint based on time, verify it triggers correctly

**Note**: NO NEW CODE REQUIRED - Home Assistant automations work automatically with any Number entity

### Verification for User Story 4

- [ ] T013 [US4] Verify entity appears in automation action dropdown for `number.set_value` service
- [ ] T014 [US4] Verify entity state is accessible in automation conditions and templates
- [ ] T015 [P] [US4] Add automation example to specs/017-dhw-setpoint-temp/quickstart.md

**Checkpoint**: Automations can control DHW setpoint

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [x] T016 [P] Run full test suite: `pytest tests/unit/test_ha_number.py -v`
- [x] T017 [P] Run ruff linting: `ruff check custom_components/buderus_wps/`
- [x] T018 Update specs/017-dhw-setpoint-temp/spec.md status from "Draft" to "Complete"
- [x] T019 Validate against quickstart.md verification checklist

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────────┐
                                ▼
Phase 2: Foundational ──────────┤ (BLOCKS all user stories)
                                ▼
Phase 3: US1+US2 (P1) ──────────┤ (MVP - read/write entity)
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            Phase 4: US3   Phase 5: US4   Phase 6: Polish
            (verification) (verification) (can start after US1+US2)
```

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US1+US2 | Phase 2 (Foundational) | None - must complete first |
| US3 | US1+US2 complete | US4, Phase 6 |
| US4 | US1+US2 complete | US3, Phase 6 |

### Within Phase 3 (US1+US2)

```
T005 (entity class) → T006 (register entity)
                   ↘
T007 (const)        → independent
                   ↘
T008, T009 (tests)  → can run after T005, T006
```

### Parallel Opportunities

**After Phase 2 completes**:
- T005, T007 can run in parallel (different files)
- T008, T009 can run in parallel (different test files)

**After Phase 3 completes**:
- T010-T012 (US3), T013-T015 (US4), T016-T019 (Polish) can all run in parallel

---

## Parallel Example: Phase 3

```bash
# Launch entity implementation tasks in parallel:
Task: "Create BuderusDHWSetpointNumber entity class in custom_components/buderus_wps/number.py"
Task: "Add ICON_WATER_THERMOMETER constant if not present in custom_components/buderus_wps/const.py"

# After entity created, launch tests in parallel:
Task: "Add unit tests for BuderusDHWSetpointNumber in tests/unit/test_ha_number.py"
Task: "Add coordinator method tests in tests/unit/test_coordinator.py"
```

---

## Implementation Strategy

### MVP First (US1+US2 Only)

1. Complete Phase 1: Setup (verify parameter exists)
2. Complete Phase 2: Foundational (coordinator changes)
3. Complete Phase 3: US1+US2 (entity implementation)
4. **STOP and VALIDATE**: Test entity in HA manually
5. Deploy if ready - users can view and adjust DHW setpoint

### Full Feature

1. MVP above
2. Phase 4: Verify CLI works (no code needed)
3. Phase 5: Verify automations work (no code needed)
4. Phase 6: Polish and documentation

### Effort Estimate

| Phase | Tasks | New Code Lines | Notes |
|-------|-------|----------------|-------|
| Phase 1 | 1 | 0 | Verification only |
| Phase 2 | 3 | ~25 | Dataclass + coordinator methods |
| Phase 3 | 5 | ~35 | Entity class + registration + tests |
| Phase 4 | 3 | 0 | Verification only |
| Phase 5 | 3 | 0 | Verification only |
| Phase 6 | 4 | 0 | Validation and docs |

**Total**: 19 tasks, ~60 lines of new code

---

## Notes

- [P] tasks = different files, no dependencies
- [US1][US2] = task serves both user stories (they share the entity)
- US3 and US4 require no new code - just verification
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
