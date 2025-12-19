# Tasks: CLI Broadcast Read Fallback

**Input**: Design documents from `/specs/012-broadcast-read-fallback/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Required per constitution (Principle IV: Comprehensive Test Coverage)

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story reference (US1, US2, US3)
- Exact file paths included

---

## Phase 1: Setup

**Purpose**: Prepare the project for feature implementation

- [x] T001 Review existing BroadcastMonitor implementation in buderus_wps/broadcast_monitor.py
- [x] T002 Review existing cmd_read() implementation in buderus_wps_cli/main.py
- [x] T003 Review existing test patterns in tests/unit/test_cli.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure needed by ALL user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add PARAM_TO_BROADCAST mapping dictionary in buderus_wps/broadcast_monitor.py
- [x] T005 Add get_broadcast_for_param() lookup function in buderus_wps/broadcast_monitor.py
- [x] T006 Add is_temperature_param() helper function in buderus_wps/broadcast_monitor.py
- [x] T007 [P] Add unit tests for PARAM_TO_BROADCAST mapping in tests/unit/test_broadcast_monitor.py
- [x] T008 [P] Add unit tests for get_broadcast_for_param() in tests/unit/test_broadcast_monitor.py

**Checkpoint**: Foundation ready - mapping infrastructure complete, user story implementation can begin

---

## Phase 3: User Story 1 - Explicit Broadcast Read (Priority: P1) 🎯 MVP

**Goal**: Users can explicitly read temperature parameters from broadcast traffic using `--broadcast` flag

**Independent Test**: Run `wps-cli read GT2_TEMP --broadcast` and verify temperature value is returned

### Tests for User Story 1

**NOTE: Write tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US1] Add unit test for --broadcast argument parsing in tests/unit/test_cli.py
- [x] T010 [P] [US1] Add unit test for --duration argument parsing in tests/unit/test_cli.py
- [x] T011 [P] [US1] Add contract test for broadcast read output format in tests/contract/test_broadcast_read_contract.py
- [x] T012 [US1] Add integration test for broadcast read with mock adapter in tests/integration/test_broadcast_read.py

### Implementation for User Story 1

- [x] T013 [US1] Add --broadcast argument to read subparser in buderus_wps_cli/main.py
- [x] T014 [US1] Add --duration argument to read subparser in buderus_wps_cli/main.py (default: 5.0)
- [x] T015 [US1] Implement read_from_broadcast() helper function in buderus_wps_cli/main.py
- [x] T016 [US1] Modify cmd_read() to handle --broadcast flag in buderus_wps_cli/main.py
- [x] T017 [US1] Add error handling for parameter not found in broadcast in buderus_wps_cli/main.py
- [x] T018 [US1] Add acceptance test for AS1.1 (basic broadcast read) in tests/acceptance/test_broadcast_read_acceptance.py
- [x] T019 [US1] Add acceptance test for AS1.2 (broadcast read with custom duration) in tests/acceptance/test_broadcast_read_acceptance.py
- [x] T020 [US1] Add acceptance test for AS1.3 (broadcast timeout error) in tests/acceptance/test_broadcast_read_acceptance.py

**Checkpoint**: User Story 1 complete - explicit broadcast read fully functional

---

## Phase 4: User Story 2 - Automatic Fallback (Priority: P2)

**Goal**: Read command automatically falls back to broadcast when RTR returns invalid data

**Independent Test**: Run `wps-cli read GT2_TEMP` (no flag) and verify automatic fallback occurs for 1-byte response

### Tests for User Story 2

- [x] T021 [P] [US2] Add unit test for is_invalid_rtr_response() in tests/unit/test_cli.py
- [x] T022 [P] [US2] Add unit test for --no-fallback argument parsing in tests/unit/test_cli.py
- [x] T023 [US2] Add integration test for automatic fallback behavior in tests/integration/test_broadcast_read.py
- [x] T024 [US2] Add integration test for --no-fallback disabling fallback in tests/integration/test_broadcast_read.py

### Implementation for User Story 2

- [x] T025 [US2] Implement is_invalid_rtr_response() function in buderus_wps_cli/main.py
- [x] T026 [US2] Add --no-fallback argument to read subparser in buderus_wps_cli/main.py
- [x] T027 [US2] Modify cmd_read() to detect invalid RTR response in buderus_wps_cli/main.py
- [x] T028 [US2] Modify cmd_read() to trigger automatic broadcast fallback in buderus_wps_cli/main.py
- [x] T029 [US2] Add warning message when fallback is triggered in buderus_wps_cli/main.py
- [x] T030 [US2] Add warning message when fallback fails in buderus_wps_cli/main.py
- [x] T031 [US2] Add acceptance test for AS2.1 (auto fallback on invalid RTR) in tests/acceptance/test_broadcast_read_acceptance.py
- [x] T032 [US2] Add acceptance test for AS2.2 (no fallback for valid RTR) in tests/acceptance/test_broadcast_read_acceptance.py
- [x] T033 [US2] Add acceptance test for AS2.3 (fallback failure with warning) in tests/acceptance/test_broadcast_read_acceptance.py

**Checkpoint**: User Story 2 complete - automatic fallback working

---

## Phase 5: User Story 3 - Source Indication (Priority: P3)

**Goal**: Output indicates data source (RTR or broadcast) for debugging

**Independent Test**: Run reads with different modes and verify source is shown in output

### Tests for User Story 3

- [x] T034 [P] [US3] Add unit test for text output with source field in tests/unit/test_cli.py
- [x] T035 [P] [US3] Add unit test for JSON output with source field in tests/unit/test_cli.py
- [x] T036 [US3] Add contract test for JSON source field format in tests/contract/test_broadcast_read_contract.py

### Implementation for User Story 3

- [x] T037 [US3] Modify cmd_read() text output to include source in buderus_wps_cli/main.py
- [x] T038 [US3] Modify cmd_read() JSON output to include source field in buderus_wps_cli/main.py
- [x] T039 [US3] Add acceptance test for AS3.1 (RTR source indication) in tests/acceptance/test_broadcast_read_acceptance.py
- [x] T040 [US3] Add acceptance test for AS3.2 (broadcast source indication) in tests/acceptance/test_broadcast_read_acceptance.py
- [x] T041 [US3] Add acceptance test for AS3.3 (JSON source field) in tests/acceptance/test_broadcast_read_acceptance.py

**Checkpoint**: User Story 3 complete - source indication in all output formats

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, documentation, and cleanup

- [ ] T042 [P] Add edge case test for non-temperature params with --broadcast in tests/integration/test_broadcast_read.py
- [ ] T043 [P] Add edge case test for connection timeout during broadcast in tests/integration/test_broadcast_read.py
- [ ] T044 [P] Add edge case test for multiple broadcast values (use most recent) in tests/integration/test_broadcast_read.py
- [x] T045 Verify all tests pass with `pytest tests/`
- [ ] T046 Run type checking with `mypy buderus_wps buderus_wps_cli`
- [ ] T047 Run linting with `ruff check buderus_wps buderus_wps_cli`
- [x] T048 Update CLI help text in buderus_wps_cli/main.py if needed
- [x] T049 Test on physical hardware (rpiheatpump.local) if available

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup (T001-T003)
    ↓
Phase 2: Foundational (T004-T008) ← BLOCKS all user stories
    ↓
┌───────────────────────────────────────────────────────┐
│ User Stories can proceed in priority order:           │
│   Phase 3: US1 (T009-T020) ← MVP                     │
│      ↓                                                │
│   Phase 4: US2 (T021-T033) ← depends on US1 impl     │
│      ↓                                                │
│   Phase 5: US3 (T034-T041)                           │
└───────────────────────────────────────────────────────┘
    ↓
Phase 6: Polish (T042-T049)
```

### User Story Dependencies

- **US1 (Explicit Broadcast)**: Can start after Phase 2 - No dependencies on other stories
- **US2 (Automatic Fallback)**: Uses read_from_broadcast() from US1, but is independently testable
- **US3 (Source Indication)**: Can be implemented alongside US1/US2, independently testable

### Within Each User Story

1. Tests MUST be written and FAIL before implementation
2. Argument parsing before logic implementation
3. Helper functions before main cmd_read() modifications
4. Acceptance tests verify story is complete

### Parallel Opportunities

**Phase 2 Parallelism**:
```
T004 + T005 + T006 (sequential - same file)
T007 || T008 (parallel - independent tests)
```

**US1 Test Parallelism**:
```
T009 || T010 || T011 (parallel - different test files/functions)
```

**US2 Test Parallelism**:
```
T021 || T022 (parallel - different test functions)
```

**US3 Test Parallelism**:
```
T034 || T035 (parallel - different test functions)
```

**Phase 6 Parallelism**:
```
T042 || T043 || T044 (parallel - independent edge case tests)
```

---

## Parallel Example: User Story 1 Tests

```bash
# Launch all US1 tests together (write first, should fail):
Task: T009 "Add unit test for --broadcast argument parsing"
Task: T010 "Add unit test for --duration argument parsing"
Task: T011 "Add contract test for broadcast read output format"
# Then T012 (depends on mocking infrastructure)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (review existing code)
2. Complete Phase 2: Foundational (mapping infrastructure)
3. Complete Phase 3: User Story 1 (explicit --broadcast flag)
4. **STOP and VALIDATE**: Test `wps-cli read GT2_TEMP --broadcast` on real hardware
5. Deploy if ready - users can now get accurate temperature readings

### Incremental Delivery

1. Setup + Foundational → Infrastructure ready
2. Add US1 → Test with --broadcast → MVP complete!
3. Add US2 → Test automatic fallback → Enhanced UX
4. Add US3 → Test source indication → Full feature

### Suggested MVP Scope

**Minimum viable feature = Phase 1 + Phase 2 + Phase 3 (US1)**

This provides:
- Users can explicitly read temperatures from broadcast
- Solves the core problem of invalid RTR responses
- Clear, simple usage: `wps-cli read GT2_TEMP --broadcast`

---

## Notes

- All modifications concentrate on buderus_wps_cli/main.py and buderus_wps/broadcast_monitor.py
- Existing BroadcastMonitor.collect() is reused - no library changes needed
- Tests use existing mock patterns from tests/unit/test_cli.py
- Constitution requires TDD - write tests before implementation
- Commit after each task or logical group
- Each checkpoint validates story independence
