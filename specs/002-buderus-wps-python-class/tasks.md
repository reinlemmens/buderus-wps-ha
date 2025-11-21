# Implementation Tasks: Buderus WPS Heat Pump Python Class

**Feature**: 002-buderus-wps-python-class
**Branch**: `002-buderus-wps-python-class`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Task Summary

- **Total Tasks**: 21
- **User Story 1 (P1)**: 7 tasks (Parameter class + tests)
- **User Story 2 (P2)**: 4 tasks (Validation + tests)
- **User Story 3 (P3)**: 6 tasks (HeatPump lookup + tests)
- **Setup Phase**: 2 tasks
- **Foundational Phase**: 1 task
- **Polish Phase**: 1 task

## Implementation Strategy

**MVP Scope**: User Story 1 only (Parameter class with metadata access)
**Delivery Order**: P1 → P2 → P3 (each story builds on previous)
**Testing Approach**: TDD per Constitution Principle IV - write tests before implementation

### Dependencies

```
Setup (Phase 1)
  ↓
Foundational (Phase 2) - Extract parameter data from FHEM
  ↓
User Story 1 (P1) ← MVP: Parameter class with metadata access
  ↓
User Story 2 (P2) ← Extends US1: Add validation methods
  ↓
User Story 3 (P3) ← Uses US1+US2: Add HeatPump container with lookups
  ↓
Polish (Final) - Documentation, performance validation
```

### Parallel Execution Opportunities

**Within User Story 1** (after T004 Parameter class skeleton):
- T005 [P]: Test parameter creation
- T006 [P]: Test is_writable()
- Can run in parallel (different test classes)

**Within User Story 2** (after T010 validation methods):
- T011 [P]: Test validate_value() valid cases
- T012 [P]: Test validate_value() edge cases
- Can run in parallel (different test methods)

**Within User Story 3** (after T015 HeatPump class skeleton):
- T016 [P]: Test get_parameter_by_index()
- T017 [P]: Test get_parameter_by_name()
- T018 [P]: Test error handling (KeyError)
- Can run in parallel (different test classes)

---

## Phase 1: Setup

**Goal**: Prepare repository structure for parameter class implementation

### Tasks

- [ ] T001 Verify existing buderus_wps/ package structure and test directories
- [ ] T002 [P] Create placeholder files buderus_wps/parameter.py and buderus_wps/parameter_data.py

---

## Phase 2: Foundational - Data Extraction

**Goal**: Extract and convert FHEM parameter data to Python format

**Blocking**: Must complete before any user story can begin

### Tasks

- [ ] T003 Create script to parse fhem/26_KM273v018.pm and extract @KM273_elements_default array to buderus_wps/parameter_data.py as PARAMETER_DATA list

---

## Phase 3: User Story 1 - Read Heat Pump Parameters (P1)

**Goal**: A home automation developer can access all 400+ heat pump parameters with complete metadata (index, extid, min, max, format, read flag, text)

**Independent Test**: Instantiate Parameter class, access all attributes, verify metadata matches KM273 specification

**Why P1**: Core functionality - without this, no parameter data can be accessed

### Acceptance Scenarios

1. Developer imports and instantiates parameter, class provides access to all KM273 parameters
2. Look up parameter by name returns complete metadata (idx, extid, format, min/max, read)
3. Parameter format matches KM273 spec (int, temp, etc.)
4. Min/max values match KM273 constraints

### Tasks

- [ ] T004 [US1] Create Parameter dataclass in buderus_wps/parameter.py with attributes (idx, extid, min, max, format, read, text) and frozen=True
- [ ] T005 [P] [US1] Write unit tests in tests/unit/test_parameter.py for Parameter creation with valid data (idx=1, ACCESS_LEVEL example)
- [ ] T006 [P] [US1] Write unit tests in tests/unit/test_parameter.py for is_writable() method (test read=0 returns True, read=1 returns False)
- [ ] T007 [US1] Implement is_writable() method in Parameter class (return self.read == 0)
- [ ] T008 [US1] Write contract tests in tests/contract/test_parameter_fidelity.py to verify PARAMETER_DATA count matches FHEM source (parse Perl, compare counts)
- [ ] T009 [US1] Write contract tests in tests/contract/test_parameter_fidelity.py to spot-check key parameters (idx=0, idx=1, idx=11) match FHEM exactly
- [ ] T010 [US1] Run tests for US1 and verify all acceptance scenarios pass (pytest tests/unit/test_parameter.py tests/contract/test_parameter_fidelity.py -v)

---

## Phase 4: User Story 2 - Validate Parameter Values (P2)

**Goal**: Developer can validate parameter values are within valid range before writing to device

**Independent Test**: Create parameter instances with various values, verify validation accepts valid and rejects invalid

**Why P2**: Safety feature - prevents invalid writes to equipment (builds on P1)

### Acceptance Scenarios

1. Value within range is accepted
2. Value below minimum is rejected
3. Value above maximum is rejected
4. Wrong type is rejected (format constraints)

### Tasks

- [ ] T011 [P] [US2] Write unit tests in tests/unit/test_parameter.py for validate_value() with valid values (within min/max range)
- [ ] T012 [P] [US2] Write unit tests in tests/unit/test_parameter.py for validate_value() edge cases (below min, above max, at boundaries, min=max=0)
- [ ] T013 [US2] Implement validate_value(value: int) method in Parameter class (return self.min <= value <= self.max)
- [ ] T014 [US2] Write integration tests in tests/integration/test_parameter_validation.py for validation across multiple parameter types (normal range, negative min, large max, flag parameters)
- [ ] T015 [US2] Run tests for US2 and verify all acceptance scenarios pass (pytest tests/unit/test_parameter.py tests/integration/test_parameter_validation.py -v)

---

## Phase 5: User Story 3 - Access Parameters by Index or Name (P3)

**Goal**: Developer can flexibly access parameters by index number or human-readable name

**Independent Test**: Access parameters using both index and name, verify both return identical data

**Why P3**: Usability - supports different integration patterns (builds on P1+P2)

### Acceptance Scenarios

1. Access by index returns correct parameter
2. Access by name returns correct parameter
3. Index and name access return identical data
4. Invalid index/name raises appropriate error

### Tasks

- [ ] T016 [US3] Create HeatPump class in buderus_wps/parameter.py with _params_by_idx and _params_by_name dicts, load from PARAMETER_DATA in __init__
- [ ] T017 [P] [US3] Write unit tests in tests/unit/test_heat_pump.py for get_parameter_by_index() (found, not found KeyError, gaps in sequence)
- [ ] T018 [P] [US3] Write unit tests in tests/unit/test_heat_pump.py for get_parameter_by_name() (found, not found KeyError, case sensitivity)
- [ ] T019 [P] [US3] Write unit tests in tests/unit/test_heat_pump.py for has_parameter_index() and has_parameter_name() existence checks
- [ ] T020 [US3] Implement get_parameter_by_index(), get_parameter_by_name(), has_parameter_index(), has_parameter_name() in HeatPump class
- [ ] T021 [US3] Implement list_all_parameters(), list_writable_parameters(), list_readonly_parameters(), parameter_count() utility methods in HeatPump class
- [ ] T022 [US3] Write performance tests to verify lookups complete < 1 second (SC-002, SC-003) and run all US3 tests (pytest tests/unit/test_heat_pump.py -v)

---

## Phase 6: Polish & Validation

**Goal**: Ensure code quality, documentation, and all success criteria met

### Tasks

- [ ] T023 Run full test suite and verify 100% pass rate with coverage for all described functionality (pytest tests/ -v --cov=buderus_wps.parameter --cov-report=term-missing)

---

## Validation Checklist

Before marking feature complete, verify:

- [ ] All 21 tasks completed and marked with [X]
- [ ] All acceptance scenarios have corresponding passing tests
- [ ] Contract tests verify Python data matches FHEM source (SC-004: 100% metadata match)
- [ ] Performance tests confirm < 1 second lookup (SC-002, SC-003)
- [ ] Constitution Principle IV: 100% test coverage for described functionality
- [ ] All edge cases tested (gaps, negative min, min=max=0, large max)
- [ ] Code follows Python 3.9+ standards with type hints
- [ ] Docstrings present for all public classes/methods (Google style)

## Notes

- **No external dependencies**: Uses only Python stdlib (dataclasses, typing)
- **Data source**: FHEM Perl file `fhem/26_KM273v018.pm` @KM273_elements_default array
- **Immutability**: Parameter is frozen dataclass (no modification after creation)
- **Protocol fidelity**: Constitution Principle II requires exact data preservation
- **Test-first**: Constitution Principle IV requires tests before implementation
- **Files created**:
  - `buderus_wps/parameter.py` (Parameter + HeatPump classes)
  - `buderus_wps/parameter_data.py` (PARAMETER_DATA constant)
  - `tests/unit/test_parameter.py`
  - `tests/unit/test_heat_pump.py`
  - `tests/integration/test_parameter_validation.py`
  - `tests/contract/test_parameter_fidelity.py`

