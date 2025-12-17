# Tasks: Indefinite Last-Known-Good Data Caching Implementation

**Input**: Design documents from `/specs/016-indefinite-caching-implementation/`
**Prerequisites**: plan.md (required), spec.md (required)

**Organization**: Tasks are organized by implementation phase, following TDD approach (tests first).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: User Story 1 - Indefinite Data Retention
- Include exact file paths in descriptions

## Path Conventions

- **Integration**: `custom_components/buderus_wps/` at repository root
- **Tests**: `tests/` at repository root

---

## Phase 1: Test Implementation (TDD Approach)

**Purpose**: Write tests FIRST to verify indefinite caching behavior before implementing

**⚠️ CRITICAL**: Tests MUST fail before implementation begins

### Integration Tests

- [ ] T001 [P] [US1] Add test for indefinite caching after 10+ failures in tests/integration/test_ha_reconnection.py
- [ ] T002 [P] [US1] Add test for staleness attributes in entity base class in tests/integration/test_ha_reconnection.py

### Acceptance Tests

- [ ] T003 [US1] Update acceptance scenario 3 test in tests/acceptance/test_ha_us1_temperature.py to verify stale data retention

**Checkpoint**: All new/updated tests should FAIL at this point (expected behavior - implementation not done yet)

---

## Phase 2: Coordinator Implementation (Core Caching Logic)

**Purpose**: Remove failure threshold and implement indefinite caching

**Goal**: Coordinator always returns cached data when available, never "Unknown"

- [ ] T004 [US1] Remove `_stale_data_threshold` attribute initialization in custom_components/buderus_wps/coordinator.py (line 72)
- [ ] T005 [US1] Update `_async_update_data()` error handling to always return cached data in custom_components/buderus_wps/coordinator.py (lines 295-374)
- [ ] T006 [P] [US1] Add `get_data_age_seconds()` helper method in custom_components/buderus_wps/coordinator.py (after line 513)
- [ ] T007 [P] [US1] Add `is_data_stale()` helper method in custom_components/buderus_wps/coordinator.py (after line 513)

**Checkpoint**: Coordinator should now never return None after first successful read

---

## Phase 3: Entity Staleness Attributes

**Purpose**: Add metadata to all entities showing data freshness

**Goal**: All entities automatically inherit staleness attributes (age, timestamp, is_stale)

- [ ] T008 [US1] Add `extra_state_attributes` property to BuderusEntity class in custom_components/buderus_wps/entity.py
- [ ] T009 [US1] Import datetime module in custom_components/buderus_wps/entity.py for timestamp formatting

**Checkpoint**: All entities should now show staleness metadata in their attributes

---

## Phase 4: Test Validation

**Purpose**: Verify all tests pass (new and existing)

- [ ] T010 [P] [US1] Run new integration tests to verify indefinite caching: `pytest tests/integration/test_ha_reconnection.py -v`
- [ ] T011 [P] [US1] Run updated acceptance test: `pytest tests/acceptance/test_ha_us1_temperature.py::test_connection_lost_retains_stale_data -v`
- [ ] T012 [US1] Run all HA integration tests to ensure no regressions: `pytest tests/unit/test_ha_* tests/integration/test_ha_* tests/acceptance/test_ha_* -v`

**Checkpoint**: All tests should now PASS (implementation complete)

---

## Phase 5: Code Quality & Polish

**Purpose**: Ensure code quality standards are met

- [ ] T013 [P] Run type checking: `mypy custom_components/buderus_wps`
- [ ] T014 [P] Run linting: `ruff check custom_components/buderus_wps`
- [ ] T015 [P] Format code: `black custom_components/buderus_wps`
- [ ] T016 Verify all success criteria from spec.md are met

**Checkpoint**: All quality gates pass, ready for commit

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Tests)**: No dependencies - can start immediately
- **Phase 2 (Coordinator)**: Can start after Phase 1 tests are written and failing
- **Phase 3 (Entity Attributes)**: Can start after Phase 2 (needs coordinator helpers)
- **Phase 4 (Test Validation)**: Depends on Phases 2-3 completion
- **Phase 5 (Polish)**: Depends on Phase 4 completion

### Task Dependencies Within Phases

**Phase 1** (all parallel):
- T001, T002, T003 can all run in parallel (different test files or methods)

**Phase 2** (mostly parallel):
- T004, T005 must be done together (same method in coordinator)
- T006, T007 can run in parallel (different helper methods)
- T006, T007 can run in parallel with T004-T005 if working in different parts of file

**Phase 3** (sequential):
- T008 must come before T009 (T009 adds import needed by T008)

**Phase 4** (all parallel):
- T010, T011, T012 can run in parallel (different test commands)

**Phase 5** (all parallel):
- T013, T014, T015, T016 can all run in parallel

### Critical Path

The fastest path through the tasks (assuming single developer):

1. T001, T002, T003 (tests) - can do in parallel or sequentially
2. T004, T005 (coordinator threshold/error handling) - must do together
3. T006, T007 (coordinator helpers) - can do in parallel
4. T008, T009 (entity attributes) - sequential
5. T010, T011, T012 (validation) - can do in parallel
6. T013, T014, T015, T016 (polish) - can do in parallel

Total: ~8-10 distinct work items

---

## Parallel Opportunities

### Phase 1: All Tests in Parallel
```bash
# Terminal 1:
Task: "Add test for indefinite caching in tests/integration/test_ha_reconnection.py"

# Terminal 2:
Task: "Add test for staleness attributes in tests/integration/test_ha_reconnection.py"

# Terminal 3:
Task: "Update acceptance scenario 3 test in tests/acceptance/test_ha_us1_temperature.py"
```

### Phase 2: Coordinator Helpers in Parallel
```bash
# Terminal 1:
Task: "Add get_data_age_seconds() helper method"

# Terminal 2:
Task: "Add is_data_stale() helper method"
```

### Phase 4: All Validation in Parallel
```bash
# Terminal 1:
pytest tests/integration/test_ha_reconnection.py -v

# Terminal 2:
pytest tests/acceptance/test_ha_us1_temperature.py::test_connection_lost_retains_stale_data -v

# Terminal 3:
pytest tests/unit/test_ha_* tests/integration/test_ha_* tests/acceptance/test_ha_* -v
```

### Phase 5: All Quality Checks in Parallel
```bash
# Terminal 1:
mypy custom_components/buderus_wps

# Terminal 2:
ruff check custom_components/buderus_wps

# Terminal 3:
black custom_components/buderus_wps
```

---

## Implementation Strategy

### TDD Approach (Recommended)

1. **Write Tests First** (Phase 1)
   - Write integration test for indefinite caching
   - Write integration test for staleness attributes
   - Update acceptance test for scenario 3
   - **VERIFY**: All tests FAIL (expected)

2. **Implement Coordinator Changes** (Phase 2)
   - Remove threshold
   - Update error handling
   - Add helper methods
   - **VERIFY**: Integration tests start passing

3. **Implement Entity Attributes** (Phase 3)
   - Add extra_state_attributes property
   - **VERIFY**: Staleness attribute test passes

4. **Validate** (Phase 4)
   - Run all tests
   - **VERIFY**: All tests pass, no regressions

5. **Polish** (Phase 5)
   - Type check, lint, format
   - **VERIFY**: All quality gates pass

### Single-Pass Approach (Alternative)

If skipping TDD:

1. Complete Phase 2 (Coordinator) + Phase 3 (Entity Attributes)
2. Complete Phase 1 (Tests) - tests should now pass immediately
3. Complete Phase 4 (Validation)
4. Complete Phase 5 (Polish)

---

## Success Criteria Validation

From spec.md, verify these after implementation:

- [ ] **SC-001**: After 10 consecutive CAN bus failures, sensors still show last known values
  - Verified by: T010 (integration test)

- [ ] **SC-002**: Entity attributes show accurate staleness metadata (age, timestamp, boolean flag)
  - Verified by: T002, T011 (integration + acceptance tests)

- [ ] **SC-003**: All existing tests continue to pass
  - Verified by: T012 (full test suite)

- [ ] **SC-004**: New tests verify indefinite caching and staleness attributes
  - Verified by: T010, T011 (new test execution)

- [ ] **SC-005**: No memory leaks from indefinite cache retention
  - Verified by: Code review (cache is single BuderusData object)

---

## Functional Requirements Validation

From spec.md, verify these are implemented:

- [ ] **FR-001**: Coordinator removes 3-failure threshold - Implemented in T004
- [ ] **FR-002**: Coordinator always returns cached data when available - Implemented in T005
- [ ] **FR-003**: Coordinator provides get_data_age_seconds() helper - Implemented in T006
- [ ] **FR-004**: Coordinator provides is_data_stale() helper - Implemented in T007
- [ ] **FR-005**: Entity base class adds extra_state_attributes property - Implemented in T008
- [ ] **FR-006**: All sensor entities inherit staleness attributes - Automatic via T008
- [ ] **FR-007**: Tests verify indefinite caching (5+ failures) - Implemented in T001, T003
- [ ] **FR-008**: Tests verify staleness attributes - Implemented in T002, T003

---

## Notes

- **TDD Recommended**: Write tests first (Phase 1) to ensure correct behavior
- **Parallel Opportunities**: Many tasks can run in parallel (marked with [P])
- **No Breaking Changes**: Existing sensor entities require no modifications
- **Memory Safety**: Cache is single BuderusData object (~1KB), negligible impact
- **Independent Verification**: Each phase has a checkpoint for validation
- **Total Tasks**: 16 tasks across 5 phases
- **Estimated Effort**: 2-4 hours for single developer following TDD approach

---

## Acceptance Scenarios Mapping

From spec.md User Story acceptance scenarios:

1. **Scenario 1**: Sensors continue showing last values after 5+ failures
   - **Tests**: T001 (integration test with 10+ failures)
   - **Implementation**: T005 (always return cached data)

2. **Scenario 2**: Sensor attributes show staleness metadata
   - **Tests**: T002 (staleness attributes test)
   - **Implementation**: T008 (extra_state_attributes property)

3. **Scenario 3**: Fresh data updates when communication recovers
   - **Tests**: T003 (updated acceptance test)
   - **Implementation**: Already works, just need to verify

4. **Scenario 4**: Sensors show "unavailable" before first read
   - **Tests**: Covered by existing tests
   - **Implementation**: No change needed (existing behavior)

All acceptance scenarios are covered by the implementation plan.
