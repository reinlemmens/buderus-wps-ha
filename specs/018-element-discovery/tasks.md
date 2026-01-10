# Tasks: Element Discovery Protocol

**Input**: Design documents from `/specs/018-element-discovery/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Tests**: Tests are included for the fail-fast behavior and parameter availability tracking.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Library**: `buderus_wps/` at repository root
- **HA Integration**: `custom_components/buderus_wps/`
- **Tests**: `tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and new exception type

- [x] T001 Add `DiscoveryRequiredError` exception to buderus_wps/exceptions.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Add `_discovered_names: Set[str]` field to HeatPump class in buderus_wps/parameter.py
- [x] T003 Add `is_discovered(name: str) -> bool` method to HeatPump class in buderus_wps/parameter.py
- [x] T004 Update `update_from_discovery()` in buderus_wps/parameter.py to populate `_discovered_names` set

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel ✅

---

## Phase 3: User Story 1 - Automatic Parameter Index Calibration (Priority: P1)

**Goal**: Integration automatically discovers parameter indices from heat pump, ensuring all sensor readings use correct CAN IDs regardless of firmware version.

**Independent Test**: Restart integration and verify all parameter readings match known good values from FHEM or heat pump display.

### Tests for User Story 1

- [x] T005 [US1] Add test for `_discovered_names` population in tests/unit/test_parameter.py
- [x] T006 [US1] Add test for `is_discovered()` method in tests/unit/test_parameter.py

### Implementation for User Story 1

- [ ] T007 [US1] Update `get_parameter()` in buderus_wps/parameter.py to check discovery status before returning parameter
- [x] T008 [US1] Add logging for idx changes during `update_from_discovery()` in buderus_wps/parameter.py (FR-013) - **ALREADY EXISTED**

**Checkpoint**: At this point, User Story 1 should be fully functional - parameters have discovery tracking ✅

---

## Phase 4: User Story 2 - Discovery Caching for Fast Startup (Priority: P2)

**Goal**: Cache discovery results persistently so subsequent starts load in under 1 second instead of 30 seconds.

**Independent Test**: Restart integration twice - first triggers discovery, second loads from cache in <1s.

### Implementation for User Story 2

- [x] T009 [US2] Change cache path from `/tmp/buderus_wps_elements.json` to `/config/buderus_wps_elements.json` in custom_components/buderus_wps/coordinator.py (FR-005)
- [x] T010 [US2] Add diagnostic logging for cache path and existence at startup in custom_components/buderus_wps/coordinator.py

**Checkpoint**: At this point, cache persists across container restarts ✅

---

## Phase 5: User Story 3 - Discovery Resilience and Recovery (Priority: P2)

**Goal**: Fail-fast on fresh install if discovery fails. Fall back only to last successful cache (never static defaults for idx).

**Independent Test**: Simulate CAN bus failure and verify system either recovers from cache or fails with clear error.

### Tests for User Story 3

- [x] T011 [US3] Add test for fail-fast when no cache exists and discovery fails in tests/unit/test_element_discovery.py
- [x] T012 [US3] Add test for cache-only fallback when discovery fails but cache exists in tests/unit/test_element_discovery.py
- [x] T013 [US3] Add test verifying incomplete cache is NOT used as fallback in tests/unit/test_element_discovery.py

### Implementation for User Story 3

- [x] T014 [US3] Modify `discover_with_cache()` in buderus_wps/element_discovery.py to raise `DiscoveryRequiredError` when no cache and discovery fails (FR-009)
- [x] T015 [US3] Modify `discover_with_cache()` in buderus_wps/element_discovery.py to use cache-only fallback, removing static idx fallback (FR-010)
- [x] T016 [US3] Add `mark_discovered()` method in buderus_wps/parameter.py for parameters with discovered idx (FR-011)
- [x] T017 [US3] Handle `DiscoveryRequiredError` in coordinator to show clear user-facing error in custom_components/buderus_wps/coordinator.py

**Checkpoint**: At this point, the system never silently produces wrong readings ✅

---

## Phase 6: User Story 4 - Index Update Transparency (Priority: P3)

**Goal**: Log CAN ID changes when parameter indices are updated to aid troubleshooting.

**Independent Test**: Check logs after discovery for idx change messages.

### Implementation for User Story 4

- [x] T018 [US4] Enhance idx change logging to include CAN ID calculation in buderus_wps/parameter.py - log format: "Updated {name}: idx {old} -> {new} (CAN ID 0x{old_id} -> 0x{new_id})" - **ALREADY EXISTED**

**Checkpoint**: All user stories should now be independently functional ✅

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation

- [x] T019 [P] Run full test suite: `pytest tests/unit/test_element_discovery.py tests/unit/test_parameter.py -v` - **PASSED**: 47 tests pass
- [x] T020 [P] Verify cache path works in HA container via SSH to homeassistant.local - **VERIFIED**: Cache at /config/buderus_wps_elements.json (269KB)
- [ ] T021 Run quickstart.md validation (manually verify troubleshooting steps work)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 and US2 can proceed in parallel
  - US3 depends on T001 (DiscoveryRequiredError) but can run parallel to US1/US2
  - US4 can proceed in parallel with others
- **Polish (Phase 7)**: Depends on all user stories being complete

### Within Each User Story

- Tests should be written first (when included)
- Implementation follows tests
- Story complete before moving to next priority (though parallel work possible)

### Parallel Opportunities

- T005, T006 (US1 tests) can run in parallel
- T011, T012, T013 (US3 tests) can run in parallel
- T009, T010 (US2 implementation) can run in parallel with US1 implementation
- T019, T020 (polish) can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 + 3 Together)

1. Complete Phase 1: Setup (exception)
2. Complete Phase 2: Foundational (discovery tracking in registry)
3. Complete Phase 3: User Story 1 (parameter availability tracking)
4. Complete Phase 5: User Story 3 (fail-fast, cache-only fallback)
5. **STOP and VALIDATE**: Test with real heat pump, verify no wrong readings
6. Add User Story 2 (persistent cache path)
7. Add User Story 4 (enhanced logging)

### Critical Path

T001 → T002/T003/T004 → T014/T015/T016 → T017

This path implements the core fail-fast and cache-only fallback that prevents silent wrong readings.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- US1 and US3 are tightly coupled - both need to work for correct behavior
