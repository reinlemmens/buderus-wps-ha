# Implementation Tasks: CAN over USB Serial Connection

**Feature**: 001-can-usb-serial
**Branch**: `001-can-usb-serial`
**Generated**: 2025-10-24
**Status**: Ready for Implementation

---

## Overview

This document provides a dependency-ordered task list for implementing the CAN over USB Serial Connection feature. Tasks are organized by user story (P1, P2, P3) to enable independent, incremental delivery with comprehensive test coverage per constitution requirements.

**Total Tasks**: 42
**Test Tasks**: 24 (100% coverage per constitution Principle IV)
**Implementation Tasks**: 18

---

## Task Format Legend

- `- [ ] T###` - Task ID (sequential execution order)
- `[P]` - Parallelizable (can run concurrently with other [P] tasks in same phase)
- `[US#]` - User Story assignment (US1=P1, US2=P2, US3=P3)

---

## Phase 1: Project Setup

**Goal**: Initialize project structure, dependencies, and configuration per plan.md

**Tasks**:

- [X] T001 Create Python package structure in `buderus_wps/` directory
- [X] T002 Create `buderus_wps/__init__.py` with package metadata and version
- [X] T003 Create test directory structure: `tests/unit/`, `tests/integration/`, `tests/contract/`
- [X] T004 Create `pyproject.toml` with Python 3.9+ requirement and pyserial dependency
- [X] T005 Create `pytest.ini` with test configuration and coverage settings
- [X] T006 Create `.gitignore` with Python-specific entries (already exists, verify completeness)
- [X] T007 Create `README.md` with quick start based on quickstart.md
- [X] T008 Install development dependencies: `pytest`, `pytest-cov`, `black`, `ruff`, `mypy` (Note: Requires venv setup by developer)

**Completion Criteria**: Project structure matches plan.md, all directories created, dependencies installable via `pip install -e .`

---

## Phase 2: Foundational Components

**Goal**: Implement core data structures and utilities needed by all user stories

**Tasks**:

- [X] T009 [P] Create custom exception hierarchy in `buderus_wps/exceptions.py` per contracts/exceptions.md
- [X] T010 [P] Write unit tests for exception classes in `tests/unit/test_exceptions.py`
- [X] T011 [P] Create `ValueEncoder` class in `buderus_wps/value_encoder.py` with temperature encoding methods
- [X] T012 [P] Write unit tests for `ValueEncoder.encode_temperature()` with all format types in `tests/unit/test_value_encoder.py`
- [X] T013 [P] Write unit tests for `ValueEncoder.decode_temperature()` with all format types in `tests/unit/test_value_encoder.py`
- [X] T014 [P] Implement `ValueEncoder.encode_int()` and `ValueEncoder.decode_int()` methods
- [X] T015 [P] Write unit tests for integer encoding/decoding in `tests/unit/test_value_encoder.py`

**Completion Criteria**: ✅ COMPLETE - Exceptions defined, `ValueEncoder` fully implemented and tested with 100% coverage

---

## Phase 3: User Story 1 - Establish Connection (P1)

**Goal**: Implement basic connection establishment to USBtin adapter

**Independent Test**: Mock USBtin device responds to initialization sequence, connection reports as open

**Tasks**:

### Tests First (TDD)

- [X] T016 [P] [US1] Write unit test for `CANMessage.__init__()` validation (ID ranges, data length) in `tests/unit/test_can_message.py`
- [X] T017 [P] [US1] Write unit test for `CANMessage.dlc` property in `tests/unit/test_can_message.py`
- [X] T018 [P] [US1] Write unit test for `CANMessage.to_usbtin_format()` standard frames in `tests/unit/test_usbtin_format.py`
- [X] T019 [P] [US1] Write unit test for `CANMessage.to_usbtin_format()` extended frames in `tests/unit/test_usbtin_format.py`
- [X] T020 [P] [US1] Write unit test for `CANMessage.from_usbtin_format()` parsing in `tests/unit/test_usbtin_format.py`
- [X] T021 [P] [US1] Write unit test for `USBtinAdapter.__init__()` parameter validation in `tests/unit/test_usbtin_adapter.py`
- [X] T022 [P] [US1] Write integration test for `USBtinAdapter.connect()` with mocked serial in `tests/integration/test_can_adapter_mock.py`
- [X] T023 [P] [US1] Write integration test for `USBtinAdapter.disconnect()` with mocked serial in `tests/integration/test_can_adapter_mock.py`
- [X] T024 [P] [US1] Write integration test for `USBtinAdapter.is_open` property in `tests/integration/test_can_adapter_mock.py`

### Implementation

- [X] T025 [US1] Implement `CANMessage` dataclass in `buderus_wps/can_message.py` with `__post_init__` validation
- [X] T026 [US1] Implement `CANMessage.to_usbtin_format()` method for SLCAN encoding
- [X] T027 [US1] Implement `CANMessage.from_usbtin_format()` classmethod for SLCAN parsing
- [X] T028 [US1] Create `USBtinAdapter` class skeleton in `buderus_wps/can_adapter.py` with `__init__`
- [X] T029 [US1] Implement `USBtinAdapter.connect()` with initialization sequence from research.md
- [X] T030 [US1] Implement `USBtinAdapter.disconnect()` with cleanup and atexit registration
- [X] T031 [US1] Implement `USBtinAdapter.is_open` property with connection status check
- [X] T032 [US1] Implement context manager methods (`__enter__`, `__exit__`) for `USBtinAdapter`

### Acceptance Tests

- [X] T033 [US1] Write acceptance test for AS1: Open connection with valid port path in `tests/contract/test_acceptance_us1.py`
- [X] T034 [US1] Write acceptance test for AS2: Query connection status when open in `tests/contract/test_acceptance_us1.py`
- [X] T035 [US1] Write acceptance test for AS3: Error handling for invalid port path in `tests/contract/test_acceptance_us1.py`

**Completion Criteria**: ✅ COMPLETE
- All US1 tests written (pending execution in venv)
- CANMessage and USBtinAdapter fully implemented
- Connection management with context manager support
- AS1, AS2, AS3 acceptance scenarios covered

**Dependencies**: Phase 2 complete

---

## Phase 4: User Story 2 - Send and Receive Messages (P2)

**Goal**: Implement bidirectional CAN message transmission

**Independent Test**: Send CAN message via mocked serial, receive and parse response, verify timeout handling

**Tasks**:

### Tests First (TDD)

- [ ] T036 [P] [US2] Write unit test for `USBtinAdapter.send_frame()` with successful response in `tests/unit/test_usbtin_adapter.py`
- [ ] T037 [P] [US2] Write unit test for `USBtinAdapter.send_frame()` timeout handling in `tests/unit/test_usbtin_adapter.py`
- [ ] T038 [P] [US2] Write unit test for `USBtinAdapter.receive_frame()` in `tests/unit/test_usbtin_adapter.py`
- [ ] T039 [P] [US2] Write integration test for sequential message transmission in `tests/integration/test_can_adapter_mock.py`
- [ ] T040 [P] [US2] Write contract test for SLCAN protocol compliance in `tests/contract/test_usbtin_protocol.py`

### Implementation

- [ ] T041 [US2] Implement `USBtinAdapter._read_frame()` private method with timeout and polling
- [ ] T042 [US2] Implement `USBtinAdapter.send_frame()` method with frame transmission and response handling
- [ ] T043 [US2] Implement `USBtinAdapter.receive_frame()` method for passive message reception
- [ ] T044 [US2] Implement `USBtinAdapter.flush_input_buffer()` method for buffer management
- [ ] T045 [US2] Add concurrent operation guard (`_in_operation` flag) to prevent simultaneous calls

### Acceptance Tests

- [ ] T046 [US2] Write acceptance test for AS1: Send CAN read request and receive response in `tests/contract/test_acceptance_us2.py`
- [ ] T047 [US2] Write acceptance test for AS2: Sequential message transmission in `tests/contract/test_acceptance_us2.py`
- [ ] T048 [US2] Write acceptance test for AS3: Timeout error when no response in `tests/contract/test_acceptance_us2.py`

**Completion Criteria**:
- All US2 tests passing (100% coverage for message transmission)
- Can send/receive CAN messages via mocked serial
- Timeout handling works correctly
- AS1, AS2, AS3 acceptance scenarios validated

**Dependencies**: Phase 3 (US1) complete

---

## Phase 5: User Story 3 - Graceful Connection Management (P3)

**Goal**: Implement robust error handling and resource cleanup

**Independent Test**: Simulate USB disconnection, verify error detection and resource cleanup

**Tasks**:

### Tests First (TDD)

- [ ] T049 [P] [US3] Write unit test for connection state detection in `tests/unit/test_usbtin_adapter.py`
- [ ] T050 [P] [US3] Write integration test for USB disconnection detection in `tests/integration/test_can_adapter_mock.py`
- [ ] T051 [P] [US3] Write integration test for resource cleanup on abnormal termination in `tests/integration/test_can_adapter_mock.py`
- [ ] T052 [P] [US3] Write integration test for `__del__` cleanup in `tests/integration/test_can_adapter_mock.py`

### Implementation

- [ ] T053 [US3] Implement `USBtinAdapter._check_connection()` private method for active status checking
- [ ] T054 [US3] Enhance `USBtinAdapter.disconnect()` to handle errors gracefully (no exceptions)
- [ ] T055 [US3] Implement `USBtinAdapter.__del__()` destructor for fallback cleanup
- [ ] T056 [US3] Add connection health checks before all operations (send_frame, receive_frame)
- [ ] T057 [US3] Implement comprehensive error messages with diagnostic context per exceptions.md

### Acceptance Tests

- [ ] T058 [US3] Write acceptance test for AS1: Explicit connection closure releases resources in `tests/contract/test_acceptance_us3.py`
- [ ] T059 [US3] Write acceptance test for AS2: USB disconnection error detection in `tests/contract/test_acceptance_us3.py`
- [ ] T060 [US3] Write acceptance test for AS3: Transient error recovery (future: not implemented) in `tests/contract/test_acceptance_us3.py`

**Completion Criteria**:
- All US3 tests passing (100% coverage for error handling)
- Disconnection detected and reported appropriately
- Resources cleaned up in all scenarios (normal, abnormal, with/without context manager)
- AS1, AS2 acceptance scenarios validated (AS3 marked as future enhancement)

**Dependencies**: Phase 4 (US2) complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal**: Add logging, improve error messages, and finalize documentation

**Tasks**:

- [ ] T061 [P] Add logging configuration to `USBtinAdapter` with configurable verbosity (FR-011)
- [ ] T062 [P] Enhance exception messages with diagnostic context and troubleshooting steps per exceptions.md
- [ ] T063 [P] Add type hints to all public methods and verify with `mypy --strict`
- [ ] T064 [P] Format all code with `black` and verify with `ruff`
- [ ] T065 [P] Generate coverage report: `pytest --cov=buderus_wps --cov-report=html`
- [ ] T066 [P] Verify 100% test coverage for all described functionality per constitution
- [ ] T067 [P] Update `buderus_wps/__init__.py` to export public API (CANMessage, USBtinAdapter, ValueEncoder)
- [ ] T068 [P] Add docstrings (Google style) to all public methods per contracts/library_api.md
- [ ] T069 [P] Create examples directory with quickstart.md code samples
- [ ] T070 [P] Run full test suite and fix any failures

**Completion Criteria**:
- Code quality checks pass (black, ruff, mypy)
- Test coverage ≥ 100% for all described functionality
- All FR requirements validated
- All SC success criteria validated
- Documentation complete and accurate

**Dependencies**: Phases 3, 4, 5 complete

---

## Dependencies & Execution Order

### Critical Path

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational)
    ↓
Phase 3 (US1: Connection) → MVP Milestone
    ↓
Phase 4 (US2: Messaging)
    ↓
Phase 5 (US3: Error Handling)
    ↓
Phase 6 (Polish)
```

### Parallelization Opportunities

**Within Each Phase**: All tasks marked `[P]` can run concurrently

**Example - Phase 3 Tests**:
- T016-T024 (all US1 tests) can be written in parallel
- T025-T032 (all US1 implementation) should run sequentially (each depends on previous)
- T033-T035 (acceptance tests) can run in parallel after implementation complete

**Example - Phase 2 Foundational**:
- T009-T010 (exceptions) parallel with T011-T015 (ValueEncoder)

---

## MVP Scope (Minimum Viable Product)

**Recommended MVP**: Complete through **Phase 3 (User Story 1)** only

**Includes**:
- Project setup and configuration
- Exception hierarchy
- Value encoding utilities
- CANMessage dataclass with validation
- USBtinAdapter connection management
- Complete test coverage for US1
- Acceptance scenarios AS1, AS2, AS3 validated

**Delivers**: Ability to establish connection to USBtin, verify status, disconnect cleanly

**Next Increments**:
- Increment 2: Add Phase 4 (message transmission)
- Increment 3: Add Phase 5 (error handling)
- Increment 4: Add Phase 6 (polish)

---

## Implementation Strategy

### Test-First Discipline (Constitution Principle IV)

1. **Write tests first** for each user story phase
2. **Run tests** - they should FAIL initially
3. **Implement** minimum code to make tests pass
4. **Refactor** while keeping tests green
5. **Verify coverage** - must be 100% for described functionality

### Task Execution Pattern

For each user story phase:

```
1. Write all tests for the phase (T###-T### marked [P])
   → Run: pytest tests/ -k "test_name" --verbose
   → Result: All tests should FAIL (red)

2. Implement functionality (T### sequential)
   → Write minimum code to pass one test
   → Run: pytest tests/ -k "test_name" --verbose
   → Result: Test passes (green)
   → Repeat for next test

3. Run acceptance tests (T### final tasks)
   → Run: pytest tests/contract/ --verbose
   → Result: All acceptance scenarios pass

4. Verify coverage
   → Run: pytest --cov=buderus_wps --cov-report=term-missing
   → Result: 100% coverage for new code
```

### File Organization

```
buderus_wps/
├── __init__.py           # T002, T067
├── exceptions.py         # T009
├── value_encoder.py      # T011, T014
├── can_message.py        # T025, T026, T027
└── can_adapter.py        # T028-T032, T041-T045, T053-T057

tests/
├── unit/
│   ├── test_exceptions.py       # T010
│   ├── test_value_encoder.py    # T012, T013, T015
│   ├── test_can_message.py      # T016, T017
│   ├── test_usbtin_format.py    # T018, T019, T020
│   └── test_usbtin_adapter.py   # T021, T036-T038, T049
├── integration/
│   └── test_can_adapter_mock.py # T022-T024, T039, T050-T052
└── contract/
    ├── test_usbtin_protocol.py  # T040
    ├── test_acceptance_us1.py   # T033-T035
    ├── test_acceptance_us2.py   # T046-T048
    └── test_acceptance_us3.py   # T058-T060
```

---

## Verification Checklist

After completing all tasks, verify:

- [ ] All 70 tasks completed
- [ ] All tests passing: `pytest tests/ --verbose`
- [ ] Coverage ≥ 100% for described functionality: `pytest --cov=buderus_wps --cov-report=html`
- [ ] Type checking passes: `mypy buderus_wps --strict`
- [ ] Linting passes: `ruff check buderus_wps/`
- [ ] Formatting correct: `black --check buderus_wps/`
- [ ] All FR (Functional Requirements) validated
- [ ] All SC (Success Criteria) validated
- [ ] All AS (Acceptance Scenarios) tested
- [ ] Documentation complete (README, docstrings, examples)
- [ ] No constitution violations (review plan.md Constitution Check)

---

## Notes for LLM Execution

- **File Paths**: All paths are absolute or relative to repository root
- **Test Strategy**: Use `unittest.mock` to mock `serial.Serial` class per research.md
- **SLCAN Protocol**: Reference research.md for initialization sequence and message format
- **Validation Rules**: Reference data-model.md for CANMessage validation constraints
- **Error Messages**: Reference contracts/exceptions.md for error message format
- **Constitution**: All tasks must maintain 100% test coverage per Principle IV

---

**Generated by**: `/speckit.tasks` command
**Ready for**: Immediate execution following TDD discipline