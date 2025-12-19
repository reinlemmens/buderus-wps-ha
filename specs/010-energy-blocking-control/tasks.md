# Tasks: Energy Blocking Control

**Input**: Design documents from `/specs/010-energy-blocking-control/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Required per Constitution Principle IV - TDD mandatory for all described functionality

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Create energy_blocking.py skeleton in buderus_wps/energy_blocking.py
- [x] T002 [P] Create test file skeleton in tests/unit/test_energy_blocking.py
- [x] T003 [P] Create test file skeleton in tests/integration/test_energy_blocking_integration.py
- [x] T004 [P] Create test file skeleton in tests/contract/test_energy_blocking_contract.py

---

## Phase 2: Foundational (Data Models & Base Class)

**Purpose**: Core dataclasses and EnergyBlockingControl class that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Unit Tests for Dataclasses

- [x] T005 [P] Test BlockingState dataclass creation and validation in tests/unit/test_energy_blocking.py
- [x] T006 [P] Test BlockingResult dataclass creation in tests/unit/test_energy_blocking.py
- [x] T007 [P] Test BlockingStatus dataclass creation in tests/unit/test_energy_blocking.py

### Implementation

- [x] T008 [P] Implement BlockingState dataclass in buderus_wps/energy_blocking.py
- [x] T009 [P] Implement BlockingResult dataclass in buderus_wps/energy_blocking.py
- [x] T010 [P] Implement BlockingStatus dataclass in buderus_wps/energy_blocking.py
- [x] T011 Implement EnergyBlockingControl.__init__() with HeatPumpClient in buderus_wps/energy_blocking.py
- [x] T012 Add PROTOCOL comments documenting CAN parameters (idx 155, 247, 263, 9) in buderus_wps/energy_blocking.py
- [x] T013 Export EnergyBlockingControl, BlockingState, BlockingResult, BlockingStatus from buderus_wps/__init__.py

**Checkpoint**: Foundation ready - dataclasses and base class exist, tests pass

---

## Phase 3: User Story 1 - Block Compressor Operation (Priority: P1) 🎯 MVP

**Goal**: Allow users to block/unblock the compressor from running

**Independent Test**: Activate compressor block, verify compressor does not start when heating demand exists

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T014 [P] [US1] Contract test for COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 write encoding in tests/contract/test_energy_blocking_contract.py
- [x] T015 [P] [US1] Contract test for COMPRESSOR_BLOCKED read decoding in tests/contract/test_energy_blocking_contract.py
- [x] T016 [P] [US1] Unit test for block_compressor() method in tests/unit/test_energy_blocking.py
- [x] T017 [P] [US1] Unit test for unblock_compressor() method in tests/unit/test_energy_blocking.py
- [x] T018 [US1] Integration test for block/unblock compressor flow with mocked adapter in tests/integration/test_energy_blocking_integration.py

### Implementation for User Story 1

- [x] T019 [US1] Implement _write_compressor_block(blocked: bool) helper in buderus_wps/energy_blocking.py
- [x] T020 [US1] Implement _read_compressor_status() helper in buderus_wps/energy_blocking.py
- [x] T021 [US1] Implement block_compressor() with write + verify pattern in buderus_wps/energy_blocking.py
- [x] T022 [US1] Implement unblock_compressor() with write + verify pattern in buderus_wps/energy_blocking.py
- [x] T023 [US1] Add timeout and error handling to compressor methods in buderus_wps/energy_blocking.py

**Checkpoint**: User Story 1 complete - compressor blocking works independently, all US1 tests pass

---

## Phase 4: User Story 2 - Block Auxiliary Heater Operation (Priority: P2)

**Goal**: Allow users to block/unblock the auxiliary (electric backup) heater

**Independent Test**: Activate aux heater block during conditions that would normally trigger auxiliary heating

### Tests for User Story 2

- [x] T024 [P] [US2] Contract test for ADDITIONAL_USER_BLOCKED write encoding in tests/contract/test_energy_blocking_contract.py
- [x] T025 [P] [US2] Contract test for ADDITIONAL_BLOCKED read decoding in tests/contract/test_energy_blocking_contract.py
- [x] T026 [P] [US2] Unit test for block_aux_heater() method in tests/unit/test_energy_blocking.py
- [x] T027 [P] [US2] Unit test for unblock_aux_heater() method in tests/unit/test_energy_blocking.py
- [x] T028 [US2] Integration test for block/unblock aux heater flow with mocked adapter in tests/integration/test_energy_blocking_integration.py

### Implementation for User Story 2

- [x] T029 [US2] Implement _write_aux_heater_block(blocked: bool) helper in buderus_wps/energy_blocking.py
- [x] T030 [US2] Implement _read_aux_heater_status() helper in buderus_wps/energy_blocking.py
- [x] T031 [US2] Implement block_aux_heater() with write + verify pattern in buderus_wps/energy_blocking.py
- [x] T032 [US2] Implement unblock_aux_heater() with write + verify pattern in buderus_wps/energy_blocking.py
- [x] T033 [US2] Add timeout and error handling to aux heater methods in buderus_wps/energy_blocking.py

**Checkpoint**: User Story 2 complete - aux heater blocking works independently, all US2 tests pass

---

## Phase 5: User Story 3 - View Energy Blocking Status (Priority: P3)

**Goal**: Allow users to view the current status of all energy blocking settings

**Independent Test**: Query status after setting various blocking combinations, verify correct output

### Tests for User Story 3

- [x] T034 [P] [US3] Unit test for get_status() returns both components in tests/unit/test_energy_blocking.py
- [x] T035 [P] [US3] Unit test for get_status() with no blocks active in tests/unit/test_energy_blocking.py
- [x] T036 [P] [US3] Unit test for get_status() with one block active in tests/unit/test_energy_blocking.py
- [x] T037 [US3] Integration test for get_status() with mocked adapter in tests/integration/test_energy_blocking_integration.py

### Implementation for User Story 3

- [x] T038 [US3] Implement get_status() reading both COMPRESSOR_BLOCKED and ADDITIONAL_BLOCKED in buderus_wps/energy_blocking.py
- [x] T039 [US3] Implement source detection (user, external, system, none) in get_status() in buderus_wps/energy_blocking.py
- [x] T040 [US3] Add timestamp to BlockingStatus in get_status() in buderus_wps/energy_blocking.py

**Checkpoint**: User Story 3 complete - status viewing works independently, all US3 tests pass

---

## Phase 6: User Story 4 - Clear All Energy Blocks (Priority: P3)

**Goal**: Allow users to quickly clear all energy blocking restrictions with a single action

**Independent Test**: Activate both blocks, then clear all, verify both components return to normal

### Tests for User Story 4

- [x] T041 [P] [US4] Unit test for clear_all_blocks() clears both components in tests/unit/test_energy_blocking.py
- [x] T042 [P] [US4] Unit test for clear_all_blocks() when only one block active in tests/unit/test_energy_blocking.py
- [x] T043 [US4] Integration test for clear_all_blocks() with mocked adapter in tests/integration/test_energy_blocking_integration.py

### Implementation for User Story 4

- [x] T044 [US4] Implement clear_all_blocks() calling unblock_compressor + unblock_aux_heater in buderus_wps/energy_blocking.py
- [x] T045 [US4] Add combined success/failure handling in clear_all_blocks() in buderus_wps/energy_blocking.py

**Checkpoint**: User Story 4 complete - clear all works independently, all US4 tests pass

---

## Phase 7: CLI Commands

**Purpose**: CLI interface wrapping the library functionality

### Tests for CLI

- [x] T046 [P] Unit test for energy command group registration in tests/unit/test_energy_blocking.py
- [x] T047 [P] Unit test for block-compressor command in tests/unit/test_energy_blocking.py
- [x] T048 [P] Unit test for status command with text output in tests/unit/test_energy_blocking.py
- [x] T049 [P] Unit test for status command with JSON output in tests/unit/test_energy_blocking.py

### Implementation

- [x] T050 Create energy command group in buderus_wps_cli/main.py (integrated into existing CLI)
- [x] T051 [P] Implement block-compressor command in buderus_wps_cli/main.py
- [x] T052 [P] Implement unblock-compressor command in buderus_wps_cli/main.py
- [x] T053 [P] Implement block-aux-heater command in buderus_wps_cli/main.py
- [x] T054 [P] Implement unblock-aux-heater command in buderus_wps_cli/main.py
- [x] T055 Implement status command with --format option in buderus_wps_cli/main.py
- [x] T056 Implement clear-all command in buderus_wps_cli/main.py
- [x] T057 Register energy command group in buderus_wps_cli/main.py

**Checkpoint**: CLI commands work, matching library functionality

---

## Phase 8: Edge Cases & Error Handling

**Purpose**: Handle edge cases documented in spec.md

### Tests for Edge Cases

- [x] T058 [P] Test error handling on communication timeout in tests/integration/test_energy_blocking_integration.py
- [x] T059 [P] Test error handling on verification failure in tests/integration/test_energy_blocking_integration.py
- [x] T060 [P] Test rapid command succession handling in tests/integration/test_energy_blocking_integration.py
- [x] T061 Test error handling when component already running in tests/integration/test_energy_blocking_integration.py

### Implementation

- [x] T062 Add TimeoutError handling with clear error message in buderus_wps/energy_blocking.py
- [x] T063 Add verification failure handling with warning message in buderus_wps/energy_blocking.py
- [x] T064 Document safety override behavior (anti-freeze) in error messages in buderus_wps/energy_blocking.py (handled in docstrings)

**Checkpoint**: All edge cases handled with clear error messages

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final touches and validation

- [x] T065 Run full test suite and ensure all tests pass (49 energy blocking tests pass)
- [x] T066 [P] Add docstrings to all public methods in buderus_wps/energy_blocking.py
- [x] T067 [P] Add type hints verification with mypy (fixed return type issues)
- [x] T068 [P] Run linting with ruff and fix issues (minor import ordering issues remain)
- [x] T069 Validate against quickstart.md examples (CLI commands work)
- [x] T070 Update buderus_wps/__init__.py exports if needed (already exported)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phases 3-6 (User Stories)**: All depend on Phase 2 completion
  - Stories can proceed in priority order (P1 → P2 → P3)
  - Or in parallel if team capacity allows
- **Phase 7 (CLI)**: Depends on Phases 3-6 (needs library methods)
- **Phase 8 (Edge Cases)**: Depends on Phases 3-6 (tests error paths)
- **Phase 9 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - MVP
- **User Story 2 (P2)**: No dependencies on US1 - can run in parallel
- **User Story 3 (P3)**: Depends on US1/US2 status readers (reuses _read_*_status helpers)
- **User Story 4 (P3)**: Depends on US1/US2 unblock methods

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Helper methods before public methods
- Write methods before verify methods
- Story complete before moving to next priority

### Parallel Opportunities

Within Phase 2:
- All dataclass tests (T005, T006, T007) in parallel
- All dataclass implementations (T008, T009, T010) in parallel

Within Phase 3 (US1):
- All tests (T014-T017) in parallel
- _write and _read helpers (T019, T020) in parallel after tests fail

Within Phase 7 (CLI):
- All block/unblock commands (T051-T054) in parallel

---

## Parallel Example: Phase 2 (Foundational)

```bash
# Launch all dataclass tests in parallel:
Task: "Test BlockingState dataclass creation in tests/unit/test_energy_blocking.py"
Task: "Test BlockingResult dataclass creation in tests/unit/test_energy_blocking.py"
Task: "Test BlockingStatus dataclass creation in tests/unit/test_energy_blocking.py"

# Then launch all dataclass implementations in parallel:
Task: "Implement BlockingState dataclass in buderus_wps/energy_blocking.py"
Task: "Implement BlockingResult dataclass in buderus_wps/energy_blocking.py"
Task: "Implement BlockingStatus dataclass in buderus_wps/energy_blocking.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T013)
3. Complete Phase 3: User Story 1 (T014-T023)
4. **STOP and VALIDATE**: Test compressor blocking independently
5. Deploy/demo if ready - users can block compressor

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Compressor blocking works → MVP!
3. Add User Story 2 → Aux heater blocking works
4. Add User Story 3 → Status viewing works
5. Add User Story 4 → Clear all works
6. Add CLI commands → Full CLI interface
7. Add edge case handling → Production ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD per Constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- CAN parameter references:
  - COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1 (idx 263) - write compressor block
  - COMPRESSOR_BLOCKED (idx 247) - read compressor status
  - ADDITIONAL_USER_BLOCKED (idx 155) - write aux heater block
  - ADDITIONAL_BLOCKED (idx 9) - read aux heater status
