# Tasks: Buderus WPS Heat Pump Python Class with Dynamic Parameter Discovery

**Input**: Design documents from `/specs/002-buderus-wps-python-class/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md
**Branch**: `002-buderus-wps-python-class`

**Tests**: Constitution Principle IV requires 100% test coverage for all described functionality. All 23 acceptance scenarios from spec.md MUST have tests.

**Organization**: Tasks are grouped by user story (P0-P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US0, US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Core library: `buderus_wps/` at repository root
- Tests: `tests/` at repository root
- Reference: `fhem/` (READ-ONLY)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Review existing buderus_wps/ package structure and dependencies
- [ ] T002 Add struct, typing.Literal to import dependencies (Python 3.9+ stdlib)
- [ ] T003 [P] Create tests/unit/, tests/integration/, tests/contract/ directories if missing
- [ ] T004 [P] Verify pytest configuration supports coverage reporting

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Add DiscoveryError exception class to buderus_wps/exceptions.py
- [ ] T006 [P] Create MockCANAdapter test utility in tests/fixtures/mock_can_adapter.py for simulating discovery protocol
- [ ] T007 [P] Document FHEM protocol cross-references in buderus_wps/protocol_reference.md (CAN IDs, binary structure, formulas)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 0 - Discover Heat Pump Parameters (Priority: P0) 🎯 CRITICAL

**Goal**: Automatically discover all available parameters from the connected heat pump device using CAN bus discovery protocol

**Independent Test**: Can be fully tested with MockCANAdapter simulating element count response and element data chunks

**Why P0**: Without parameter discovery, the system cannot know which CAN IDs to use for reading/writing parameters. This MUST complete before any parameter operations.

### Tests for User Story 0

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T008 [P] [US0] Unit test for binary element parser in tests/unit/test_binary_parser.py
  - Test valid elements with various idx, extid, min/max combinations
  - Test edge cases: min=max, negative values, len=2, len=99
  - Test invalid elements: len=0, len=100, len>remaining data, idx not increasing
  - Use known test vectors from FHEM protocol reference

- [ ] T009 [P] [US0] Unit test for discovery protocol state machine in tests/unit/test_element_discovery.py
  - Test element count request/response sequence
  - Test element data request in 4096-byte chunks
  - Test 8-byte CAN message accumulation into buffer
  - Test timeout and retry logic (20 iterations)
  - Test malformed data abort and restart

- [ ] T010 [P] [US0] Integration test for full discovery sequence in tests/integration/test_discovery_sequence.py
  - Mock adapter returns element count on 0x09FD7FE0
  - Mock adapter returns 8-byte chunks on 0x09FDBFE0
  - Verify correct sequence: count request → data requests → parsing
  - Test partial chunk handling on last chunk
  - Verify all parameters populated in registry

- [ ] T011 [P] [US0] Contract test for binary structure in tests/contract/test_protocol_fidelity.py
  - Parse known-good element data from FHEM
  - Verify idx, extid, min, max, len, name extracted correctly
  - Compare against expected values from FHEM reference
  - Verify big-endian format matches FHEM unpack

- [ ] T012 [P] [US0] Acceptance tests for User Story 0 scenarios (5 scenarios) in tests/acceptance/test_discovery.py

### Implementation for User Story 0

- [ ] T013 [P] [US0] Implement binary element parser function in buderus_wps/element_discovery.py
  - Use struct.unpack_from(">H7s4s4sb", ...) for 18-byte header
  - Handle big-endian to signed int conversion for min/max
  - Extract name with Latin-1 decoding (len-1 bytes)
  - Add `# PROTOCOL: FHEM:2135-2143` comment tag
  - Raise ValueError for malformed elements

- [ ] T014 [US0] Implement DiscoveryProtocol class in buderus_wps/element_discovery.py
  - __init__(can_adapter): Initialize with CAN adapter
  - request_element_count(): Send to 0x01FD7FE0, receive from 0x09FD7FE0
  - request_element_chunk(offset, length=4096): Send to 0x01FD3FE0
  - accumulate_responses(timeout=5.0): Accumulate 8-byte messages into buffer
  - parse_elements(buffer): Parse all elements from buffer
  - run(): Main discovery loop with retry logic (20 iterations)
  - Add `# PROTOCOL: FHEM:2052-2187` comment tags

- [ ] T015 [US0] Add source field to Parameter dataclass in buderus_wps/parameter.py
  - source: Literal["discovered", "fallback"] = "discovered"
  - Update Parameter docstring with PROTOCOL tags

- [ ] T016 [US0] Implement fallback mechanism in buderus_wps/parameter_registry.py (partial)
  - Create ParameterRegistry._run_discovery() method
  - On DiscoveryError after retries, load from parameter_data.py
  - Log warning when using fallback
  - Mark all fallback parameters with source="fallback"

- [ ] T017 [US0] Add logging for discovery operations in buderus_wps/element_discovery.py
  - Log discovery start, element count received, chunk progress, completion
  - Log retry attempts and timeouts
  - Log malformed element errors with hex dump

**Checkpoint**: At this point, parameter discovery should be fully functional and testable independently. Registry can be populated from device or fallback.

---

## Phase 4: User Story 1 - Read Heat Pump Parameters (Priority: P1) 🎯 MVP

**Goal**: Provide access to all heat pump parameters discovered from the device with metadata (idx, extid, min/max, format, read flag, text)

**Independent Test**: Can be fully tested by instantiating the class with discovered parameters (from mock discovery), accessing parameter definitions, and verifying metadata

### Tests for User Story 1

- [ ] T018 [P] [US1] Unit test for Parameter class in tests/unit/test_parameter.py
  - Test is_writable() for read=0 and read=1
  - Test validate_value() for valid, below min, above max, at boundaries
  - Test CAN ID calculation methods (get_read_can_id, get_write_can_id)
  - Test immutability (frozen dataclass)

- [ ] T019 [P] [US1] Unit test for ParameterRegistry lookup in tests/unit/test_parameter_registry.py
  - Test get_parameter_by_index() (found, not found, KeyError)
  - Test get_parameter_by_name() (found, not found, KeyError)
  - Test has_parameter_index() and has_parameter_name()
  - Test parameter_count()

- [ ] T020 [P] [US1] Contract test for CAN ID formulas in tests/contract/test_can_id_construction.py
  - Verify idx=0 → rtr=0x04003FE0, txd=0x0C003FE0
  - Verify idx=1 → rtr=0x04007FE0, txd=0x0C007FE0
  - Verify idx=100 → rtr=0x04193FE0, txd=0x0C193FE0
  - Test formula: `rtr = 0x04003FE0 | (idx << 14)` with known vectors

- [ ] T021 [P] [US1] Acceptance tests for User Story 1 scenarios (5 scenarios) in tests/acceptance/test_parameter_reading.py

### Implementation for User Story 1

- [ ] T022 [P] [US1] Implement CAN ID calculation methods in buderus_wps/parameter.py
  - get_read_can_id(): return 0x04003FE0 | (self.idx << 14)
  - get_write_can_id(): return 0x0C003FE0 | (self.idx << 14)
  - Add `# PROTOCOL: FHEM:2229-2230` comment tags
  - Add docstrings with formula documentation

- [ ] T023 [US1] Implement ParameterRegistry class in buderus_wps/parameter_registry.py
  - __init__(): Create empty _params_by_idx and _params_by_name dicts
  - discover_parameters(can_adapter): Run discovery protocol or load from cache
  - _populate(parameters): Populate both lookup dicts from parameter list
  - get_parameter_by_index(idx): O(1) lookup by idx
  - get_parameter_by_name(name): O(1) lookup by name (case-insensitive, normalize to uppercase)
  - has_parameter_index(idx): bool check
  - has_parameter_name(name): bool check
  - parameter_count(): return len(_params_by_idx)

- [ ] T024 [US1] Add list methods to ParameterRegistry in buderus_wps/parameter_registry.py
  - list_all_parameters(): Return sorted by idx
  - list_writable_parameters(): Filter by read=0
  - list_readonly_parameters(): Filter by read=1

- [ ] T025 [US1] Update buderus_wps/__init__.py to export Parameter and ParameterRegistry

**Checkpoint**: At this point, User Story 1 should be fully functional. Parameters can be accessed by name or index with all metadata available.

---

## Phase 5: User Story 2 - Validate Parameter Values (Priority: P2)

**Goal**: Ensure that parameter values are within valid range before sending commands to heat pump

**Independent Test**: Can be fully tested by creating parameter instances and verifying validation logic

### Tests for User Story 2

- [ ] T026 [P] [US2] Unit test for value validation in tests/unit/test_parameter_validation.py
  - Test validate_value() with values in range, below min, above max
  - Test boundary conditions (exactly min, exactly max)
  - Test negative minimum values (temperature parameters)
  - Test flag parameters (min=max=0)
  - Test large maximum values (2^24)

- [ ] T027 [P] [US2] Integration test for validation workflow in tests/integration/test_parameter_validation.py
  - Look up parameter by name
  - Check if writable
  - Validate value
  - Construct CAN write request with calculated ID
  - Verify complete validation → write workflow

- [ ] T028 [P] [US2] Acceptance tests for User Story 2 scenarios (5 scenarios) in tests/acceptance/test_validation.py

### Implementation for User Story 2

- [ ] T029 [P] [US2] Enhance validate_value() method in buderus_wps/parameter.py
  - Add type checking for non-integer values
  - Return detailed error messages (not just bool)
  - Support optional strict mode for format-specific validation

- [ ] T030 [US2] Add validation helper methods to ParameterRegistry in buderus_wps/parameter_registry.py
  - validate_parameter_write(name, value): Combined lookup + writability + validation
  - Returns tuple (success: bool, error: str | None)
  - Checks read flag, min/max range, type

- [ ] T031 [US2] Document validation patterns in buderus_wps/parameter_registry.py
  - Add docstring examples for safe parameter writing
  - Document read-only flag enforcement
  - Add usage notes for CAN write ID calculation

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Parameters can be validated before writes.

---

## Phase 6: User Story 3 - Access Parameters by Index or Name (Priority: P3)

**Goal**: Flexible parameter access supporting both index-based and name-based lookup

**Independent Test**: Can be fully tested by accessing parameters using both methods and verifying identical results

### Tests for User Story 3

- [ ] T032 [P] [US3] Unit test for dual lookup in tests/unit/test_parameter_access.py
  - Test lookup by idx returns correct parameter
  - Test lookup by name returns correct parameter
  - Test same parameter accessible both ways (identity check)
  - Test KeyError for invalid idx or name
  - Test case-insensitive name lookup (normalize to uppercase)

- [ ] T033 [P] [US3] Acceptance tests for User Story 3 scenarios (4 scenarios) in tests/acceptance/test_parameter_access.py

### Implementation for User Story 3

- [ ] T034 [P] [US3] Add case-insensitive name normalization in buderus_wps/parameter_registry.py
  - Normalize parameter names to uppercase on population
  - Normalize query names to uppercase in get_parameter_by_name()
  - Document normalization behavior in docstrings

- [ ] T035 [US3] Add parameter search helper in buderus_wps/parameter_registry.py
  - search_parameters(query): Substring search in parameter names
  - Returns list of matching parameters
  - Case-insensitive matching
  - Useful for interactive parameter browsing

- [ ] T036 [US3] Handle non-sequential indices in buderus_wps/parameter_registry.py
  - Document that idx sequence may have gaps
  - Verify dict-based lookup handles naturally
  - Add test case for missing idx (e.g., 13 missing between 12 and 14)

**Checkpoint**: All core parameter access patterns should now be functional (name, index, search).

---

## Phase 7: User Story 4 - Cache Discovered Parameters (Priority: P2)

**Goal**: Cache discovered parameters to persistent storage, reducing connection time from ~30s to <3s

**Independent Test**: Can be fully tested with mocks by verifying cache save/load roundtrip

### Tests for User Story 4

- [ ] T037 [P] [US4] Unit test for cache persistence in tests/unit/test_parameter_cache.py
  - Test save/load roundtrip to JSON
  - Test checksum validation (SHA256 of parameters)
  - Test device ID matching
  - Test cache invalidation on checksum mismatch
  - Test cache invalidation on device ID mismatch
  - Test invalid JSON handling
  - Test missing cache file handling

- [ ] T038 [P] [US4] Integration test for cache roundtrip in tests/integration/test_cache_roundtrip.py
  - Run discovery with MockCANAdapter
  - Save to cache with device ID
  - Load from cache on next connection
  - Verify parameters identical (idx, extid, min, max, format, read, text)
  - Verify no discovery protocol runs on cached load
  - Measure load time < 3 seconds

- [ ] T039 [P] [US4] Performance test for cache loading in tests/integration/test_cache_performance.py
  - Load 400 parameters from cache
  - Load 2000 parameters from cache
  - Verify both < 3 seconds (SC-007 requirement)
  - Compare to discovery time (~30 seconds)
  - Verify 90% performance improvement

- [ ] T040 [P] [US4] Acceptance tests for User Story 4 scenarios (4 scenarios) in tests/acceptance/test_caching.py

### Implementation for User Story 4

- [ ] T041 [P] [US4] Implement ParameterCache class in buderus_wps/parameter_cache.py
  - __init__(cache_dir="~/.config/buderus-wps/"): Initialize cache directory
  - _get_cache_path(device_id): Return path to {cache_dir}/parameter_cache_{device_id}.json
  - _calculate_checksum(parameters): SHA256 hash of sorted parameter data
  - _get_device_id(can_adapter): Extract serial number or hash first 10 extids
  - save(device_id, parameters): Write JSON with version, device_id, checksum, timestamp, parameters
  - load(device_id): Read JSON, validate checksum and device_id, return parameters
  - invalidate(device_id): Delete cache file
  - Cache format per research.md decision (JSON with metadata)

- [ ] T042 [US4] Integrate caching into ParameterRegistry in buderus_wps/parameter_registry.py
  - discover_parameters(): Try cache first before running discovery
  - On cache hit: Load parameters and populate dicts
  - On cache miss: Run discovery, save to cache, populate dicts
  - On cache validation failure: Invalidate and re-discover
  - Add force_rediscover parameter to bypass cache

- [ ] T043 [US4] Add cache validation in buderus_wps/parameter_cache.py
  - Validate JSON structure (version, device_id, checksum, parameters)
  - Validate checksum matches calculated checksum
  - Validate device_id matches current device
  - Return ValidationResult(valid: bool, reason: str)

- [ ] T044 [US4] Add logging for cache operations in buderus_wps/parameter_cache.py
  - Log cache hit/miss
  - Log cache save with device_id and parameter count
  - Log cache invalidation with reason
  - Log cache validation failures

**Checkpoint**: Caching should reduce connection time by 90% (from ~30s to <3s) while maintaining full functionality.

---

## Phase 8: Fallback Data & Contract Tests

**Purpose**: Ensure fallback to static data works and matches FHEM reference

- [ ] T045 [P] Extract @KM273_elements_default from fhem/26_KM273v018.pm to buderus_wps/parameter_data.py
  - Manual Perl-to-Python conversion (one-time task)
  - Store as PARAMETER_DATA constant (list of dicts)
  - Add PROTOCOL comment with FHEM line number reference
  - Preserve exact data: idx, extid, min, max, format, read, text

- [ ] T046 [P] Contract test for fallback data fidelity in tests/contract/test_fallback_fidelity.py
  - Parse @KM273_elements_default from FHEM Perl file
  - Compare parameter count with Python PARAMETER_DATA
  - Spot-check key parameters (idx=0, idx=1, last parameter)
  - Verify no duplicate indices, names, or extids
  - Verify all required fields present

- [ ] T047 Test fallback loading in ParameterRegistry in tests/integration/test_discovery_fallback.py
  - Simulate discovery failure (MockCANAdapter raises DiscoveryError)
  - Verify fallback to PARAMETER_DATA
  - Verify warning logged
  - Verify all parameters marked with source="fallback"
  - Verify registry fully functional with fallback data

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T048 [P] Update data-model.md with discovery protocol entities
  - Add DiscoveredElement entity documentation
  - Add ParameterCache entity documentation
  - Add ParameterRegistry entity documentation
  - Update Parameter entity with source field and CAN ID methods
  - Document binary parsing structures

- [ ] T049 [P] Update quickstart.md with discovery flow examples
  - Example: First connection (discovery runs)
  - Example: Subsequent connections (cached load)
  - Example: Fallback scenario (discovery fails)
  - Example: Parameter lookup and CAN ID calculation
  - Example: Cache invalidation

- [ ] T050 [P] Add comprehensive docstrings to all modules
  - buderus_wps/element_discovery.py
  - buderus_wps/parameter.py
  - buderus_wps/parameter_registry.py
  - buderus_wps/parameter_cache.py
  - Include PROTOCOL tags with FHEM line references

- [ ] T051 [P] Add type hints to all function signatures
  - Use Python 3.9+ syntax (list[T], dict[K, V])
  - Use typing.Literal for source field
  - Run mypy validation

- [ ] T052 Run full test suite with coverage reporting
  - pytest --cov=buderus_wps --cov-report=html
  - Verify 100% coverage for all described functionality
  - Fix any coverage gaps

- [ ] T053 Validate quickstart.md examples work end-to-end
  - Run all code examples from quickstart.md
  - Verify output matches documented examples
  - Update examples if behavior changed

- [ ] T054 Constitution compliance review
  - Verify Principle II: All PROTOCOL tags present with FHEM line numbers
  - Verify Principle III: Validation, fallback, cache validation implemented
  - Verify Principle IV: 100% test coverage achieved
  - Verify Principle V: Protocol documentation complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - **User Story 0 (P0)**: CRITICAL - Must complete before US1, US2, US3 (they need discovered parameters)
  - **User Story 1 (P1)**: Depends on US0 (needs discovered parameters)
  - **User Story 2 (P2)**: Depends on US1 (needs parameter access)
  - **User Story 3 (P3)**: Depends on US1 (enhances parameter access)
  - **User Story 4 (P2)**: Depends on US0 (caches discovered parameters)
- **Fallback Data (Phase 8)**: Can run in parallel with user stories after Foundational
- **Polish (Phase 9)**: Depends on all desired user stories being complete

### Critical Path

```
Setup → Foundational → US0 (Discovery) → US1 (Reading) → US2 (Validation)
                                        ↘ US3 (Access methods)
                                        ↘ US4 (Caching)
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Unit tests before integration tests
- Contract tests before implementation
- Core implementation before enhancements
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 2 (Foundational):**
- T006 and T007 can run in parallel

**Phase 3 (User Story 0 - Tests):**
- T008, T009, T010, T011, T012 can all run in parallel

**Phase 3 (User Story 0 - Implementation):**
- T013 can run independently (binary parser)
- T015 can run independently (Parameter class update)

**Phase 4 (User Story 1 - Tests):**
- T018, T019, T020, T021 can all run in parallel

**Phase 4 (User Story 1 - Implementation):**
- T022 can run independently (CAN ID methods)

**Phase 5 (User Story 2 - Tests):**
- T026, T027, T028 can all run in parallel

**Phase 5 (User Story 2 - Implementation):**
- T029 can run independently (validation enhancement)

**Phase 6 (User Story 3 - Tests):**
- T032, T033 can run in parallel

**Phase 6 (User Story 3 - Implementation):**
- T034 can run independently (normalization)

**Phase 7 (User Story 4 - Tests):**
- T037, T038, T039, T040 can all run in parallel

**Phase 7 (User Story 4 - Implementation):**
- T041 can run independently (ParameterCache class)

**Phase 8 (Fallback):**
- T045, T046 can run in parallel

**Phase 9 (Polish):**
- T048, T049, T050, T051 can all run in parallel

---

## Parallel Example: User Story 0

```bash
# Launch all tests for User Story 0 together:
Task: "Unit test for binary element parser in tests/unit/test_binary_parser.py"
Task: "Unit test for discovery protocol state machine in tests/unit/test_element_discovery.py"
Task: "Integration test for full discovery sequence in tests/integration/test_discovery_sequence.py"
Task: "Contract test for binary structure in tests/contract/test_protocol_fidelity.py"
Task: "Acceptance tests for User Story 0 scenarios in tests/acceptance/test_discovery.py"

# Launch parallel implementation tasks for User Story 0:
Task: "Implement binary element parser function in buderus_wps/element_discovery.py"
Task: "Add source field to Parameter dataclass in buderus_wps/parameter.py"
```

---

## Implementation Strategy

### MVP First (User Story 0 + User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 0 (Discovery) - CRITICAL FOUNDATION
4. Complete Phase 4: User Story 1 (Reading) - CORE FUNCTIONALITY
5. **STOP and VALIDATE**: Test US0+US1 independently with mocked CAN adapter
6. Deploy/demo if ready - basic parameter discovery and reading works!

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 0 → Test independently → Discovery works! (but no caching yet)
3. Add User Story 1 → Test independently → Can read parameters! (MVP achieved)
4. Add User Story 4 → Test independently → Caching working! (90% faster)
5. Add User Story 2 → Test independently → Validation working!
6. Add User Story 3 → Test independently → Flexible access!
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done, one developer MUST complete User Story 0 (blocking)
3. Once US0 is done:
   - Developer A: User Story 1 (reading)
   - Developer B: User Story 4 (caching)
   - Developer C: Phase 8 (fallback data extraction)
4. After US1 complete:
   - Developer D: User Story 2 (validation)
   - Developer E: User Story 3 (access methods)
5. Stories complete and integrate independently

---

## Task Summary

**Total Tasks**: 54

**Task Count by User Story:**
- Setup (Phase 1): 4 tasks
- Foundational (Phase 2): 3 tasks
- User Story 0 (P0 - Discovery): 17 tasks (5 test tasks, 5 implementation, 7 support)
- User Story 1 (P1 - Reading): 8 tasks (4 test tasks, 4 implementation)
- User Story 2 (P2 - Validation): 6 tasks (3 test tasks, 3 implementation)
- User Story 3 (P3 - Access): 5 tasks (2 test tasks, 3 implementation)
- User Story 4 (P2 - Caching): 8 tasks (4 test tasks, 4 implementation)
- Fallback Data (Phase 8): 3 tasks
- Polish (Phase 9): 7 tasks

**Parallel Opportunities**: 25 tasks marked [P] can run in parallel within their phases

**Independent Test Criteria:**
- **US0**: Mock CAN adapter simulates discovery protocol → parameters populated in registry
- **US1**: Parameters accessible by name and index → metadata correct
- **US2**: Value validation works → read-only enforcement works
- **US3**: Both lookup methods work → search works
- **US4**: Cache saves and loads → load time < 3s

**Suggested MVP Scope**: User Story 0 + User Story 1 (Discovery + Reading)

**Performance Targets**:
- Discovery: < 30 seconds (SC-001)
- Cached load: < 3 seconds (SC-007)
- Lookup: < 1 second (SC-003, SC-004)
- Coverage: 100% of described functionality

**Critical Success Factors**:
1. User Story 0 MUST complete before other stories (provides discovered parameters)
2. All PROTOCOL tags MUST reference FHEM line numbers (Principle II)
3. All 23 acceptance scenarios MUST be tested (Principle IV)
4. Mock CAN adapter MUST simulate discovery without hardware (testability)
5. Cache MUST reduce connection time by 90% (SC-007)

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- User Story 0 is CRITICAL PATH - all other stories depend on discovery
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD required per Constitution)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Mock CAN adapter eliminates hardware dependency for testing
- FHEM protocol reference is READ-ONLY - all PROTOCOL tags must cite line numbers
