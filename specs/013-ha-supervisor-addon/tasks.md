# Tasks: Home Assistant Supervisor Add-on

**Input**: Design documents from `/specs/013-ha-supervisor-addon/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included per constitution requirement for comprehensive test coverage.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and add-on scaffolding

- [x] T001 Create addon/ directory structure per implementation plan
- [x] T002 [P] Create addon/buderus_wps_addon/__init__.py with package metadata
- [x] T003 [P] Create addon/translations/en.yaml with configuration field descriptions
- [x] T004 [P] Create addon/CHANGELOG.md with initial version entry
- [x] T005 Create addon/build.yaml with multi-arch build configuration (amd64, aarch64)
- [x] T006 Create addon/Dockerfile with ghcr.io/home-assistant base-python image

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T007 Create addon/buderus_wps_addon/entity_config.py with EntityConfig dataclass from data-model.md
- [x] T008 [P] Define TEMPERATURE_SENSORS list in addon/buderus_wps_addon/entity_config.py
- [x] T009 [P] Define BINARY_SENSORS list in addon/buderus_wps_addon/entity_config.py
- [x] T010 [P] Define SELECT_ENTITIES list in addon/buderus_wps_addon/entity_config.py
- [x] T011 [P] Define SWITCH_ENTITIES list in addon/buderus_wps_addon/entity_config.py
- [x] T012 [P] Define NUMBER_ENTITIES list in addon/buderus_wps_addon/entity_config.py
- [x] T013 Create addon/buderus_wps_addon/config.py with AddonConfig dataclass and load_config() function
- [x] T014 [P] Create tests/unit/test_entity_config.py with entity definition validation tests
- [x] T015 [P] Create tests/contract/test_mqtt_discovery.py with MQTT Discovery payload validation tests

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Install Add-on from Repository (Priority: P1)

**Goal**: Enable users to install the Buderus WPS add-on from a GitHub repository via Home Assistant Add-on Store

**Independent Test**: Add repository URL to Home Assistant, verify add-on appears and installs successfully

### Tests for User Story 1

- [x] T016 [P] [US1] Create tests/contract/test_addon_config.py with config.yaml schema validation tests
- [x] T017 [P] [US1] Create tests/integration/test_addon_install.py with add-on metadata validation tests

### Implementation for User Story 1

- [x] T018 [US1] Create addon/config.yaml with name, version, slug, description, arch support (amd64, aarch64)
- [x] T019 [US1] Add options schema to addon/config.yaml (serial_device, mqtt_host, mqtt_port, mqtt_username, mqtt_password, scan_interval, log_level)
- [x] T020 [US1] Add device mapping for USB serial in addon/config.yaml (/dev/ttyUSB*, /dev/ttyACM*, /dev/serial/by-id/*)
- [x] T021 [US1] Create addon/DOCS.md with installation and configuration instructions
- [x] T022 [US1] Create S6 service type file addon/rootfs/etc/s6-overlay/s6-rc.d/buderus-wps/type (longrun)
- [x] T023 [US1] Create S6 service registration addon/rootfs/etc/s6-overlay/s6-rc.d/user/contents.d/buderus-wps (empty file)

**Checkpoint**: Add-on installable from repository, shows in Add-on Store with documentation

---

## Phase 4: User Story 2 - Configure USB Serial Device (Priority: P1)

**Goal**: Enable users to specify the USB serial device path and connect to their USBtin CAN adapter

**Independent Test**: Configure serial device in add-on settings, start add-on, verify connection success/failure in logs

### Tests for User Story 2

- [x] T024 [P] [US2] Create tests/unit/test_config.py with AddonConfig loading and validation tests
- [x] T025 [P] [US2] Add serial device validation tests to tests/unit/test_config.py (valid path, invalid path, permission error)

### Implementation for User Story 2

- [x] T026 [US2] Implement environment variable loading in addon/buderus_wps_addon/config.py (bashio config access)
- [x] T027 [US2] Add serial device path validation in addon/buderus_wps_addon/config.py
- [x] T028 [US2] Create addon/buderus_wps_addon/main.py with basic service entry point structure
- [x] T029 [US2] Implement USBtinAdapter connection logic in addon/buderus_wps_addon/main.py
- [x] T030 [US2] Add connection success/failure logging in addon/buderus_wps_addon/main.py
- [x] T031 [US2] Implement USB disconnect detection in addon/buderus_wps_addon/main.py
- [x] T032 [US2] Implement automatic reconnection logic in addon/buderus_wps_addon/main.py (with exponential backoff)
- [x] T033 [US2] Create S6 run script addon/rootfs/etc/s6-overlay/s6-rc.d/buderus-wps/run

**Checkpoint**: Add-on can connect to USB serial device and handle connection errors gracefully

---

## Phase 5: User Story 3 - Monitor Heat Pump Data via MQTT (Priority: P1)

**Goal**: Publish temperature sensors and compressor status to Home Assistant via MQTT Discovery

**Independent Test**: Start add-on, verify temperature sensors and compressor status appear automatically in Home Assistant

### Tests for User Story 3

- [x] T034 [P] [US3] Create tests/unit/test_mqtt_bridge.py with MQTT connection tests
- [x] T035 [P] [US3] Add discovery payload generation tests to tests/unit/test_mqtt_bridge.py
- [x] T036 [P] [US3] Add state publishing tests to tests/unit/test_mqtt_bridge.py
- [ ] T037 [P] [US3] Create tests/integration/test_sensor_discovery.py with end-to-end sensor discovery tests

### Implementation for User Story 3

- [x] T038 [US3] Create addon/buderus_wps_addon/mqtt_bridge.py with MQTTBridge class skeleton
- [x] T039 [US3] Implement MQTT broker connection in addon/buderus_wps_addon/mqtt_bridge.py (auto-detect via Supervisor API)
- [x] T040 [US3] Implement MQTT Discovery payload generation for sensors in addon/buderus_wps_addon/mqtt_bridge.py
- [x] T041 [US3] Implement publish_discovery_config() method for all sensor entities in addon/buderus_wps_addon/mqtt_bridge.py
- [x] T042 [US3] Implement BroadcastMonitor integration for temperature readings in addon/buderus_wps_addon/main.py
- [x] T043 [US3] Implement MenuAPI integration for compressor status in addon/buderus_wps_addon/main.py
- [x] T044 [US3] Implement publish_state() method for sensor values in addon/buderus_wps_addon/mqtt_bridge.py
- [x] T045 [US3] Implement polling loop with configurable scan_interval in addon/buderus_wps_addon/main.py
- [x] T046 [US3] Implement availability topic publishing (online/offline) in addon/buderus_wps_addon/mqtt_bridge.py
- [x] T047 [US3] Implement Last Will and Testament for offline status in addon/buderus_wps_addon/mqtt_bridge.py
- [x] T048 [US3] Add device grouping to discovery payloads in addon/buderus_wps_addon/mqtt_bridge.py

**Checkpoint**: All temperature sensors and compressor status appear automatically in Home Assistant with proper device grouping

---

## Phase 6: User Story 4 - Control Heat Pump via MQTT (Priority: P2)

**Goal**: Enable users to control heating mode, DHW mode, holiday mode, and extra hot water via Home Assistant entities

**Independent Test**: Toggle switches/selects in Home Assistant, verify heat pump responds and state updates

### Tests for User Story 4

- [ ] T049 [P] [US4] Create tests/unit/test_command_queue.py with command queuing and rate limiting tests
- [ ] T050 [P] [US4] Add command validation tests to tests/unit/test_command_queue.py
- [ ] T051 [P] [US4] Create tests/integration/test_control_entities.py with end-to-end control tests

### Implementation for User Story 4

- [ ] T052 [US4] Create addon/buderus_wps_addon/command_queue.py with CommandQueue class
- [ ] T053 [US4] Implement 500ms minimum delay between commands in addon/buderus_wps_addon/command_queue.py
- [ ] T054 [US4] Implement command validation (value ranges, read-only check) in addon/buderus_wps_addon/command_queue.py
- [ ] T055 [US4] Implement MQTT Discovery payload generation for control entities in addon/buderus_wps_addon/mqtt_bridge.py
- [ ] T056 [US4] Subscribe to command topics in addon/buderus_wps_addon/mqtt_bridge.py
- [ ] T057 [US4] Implement command message parsing in addon/buderus_wps_addon/mqtt_bridge.py
- [ ] T058 [US4] Implement value mapping (HA option string → parameter value) in addon/buderus_wps_addon/entity_config.py
- [ ] T059 [US4] Implement HeatPumpClient.write_value() integration in addon/buderus_wps_addon/main.py
- [ ] T060 [US4] Implement state refresh after successful command in addon/buderus_wps_addon/main.py
- [ ] T061 [US4] Add command timeout handling in addon/buderus_wps_addon/command_queue.py

**Checkpoint**: All control entities (heating mode, DHW mode, holiday mode, extra DHW) work from Home Assistant

---

## Phase 7: User Story 5 - View Add-on Logs (Priority: P2)

**Goal**: Provide meaningful log messages for troubleshooting connection and communication issues

**Independent Test**: View Log tab in add-on panel, verify timestamped entries with connection status and errors

### Tests for User Story 5

- [ ] T062 [P] [US5] Create tests/unit/test_logging.py with log format and verbosity tests
- [ ] T063 [P] [US5] Add log level configuration tests to tests/unit/test_logging.py

### Implementation for User Story 5

- [ ] T064 [US5] Configure Python logging with timestamped format in addon/buderus_wps_addon/main.py
- [ ] T065 [US5] Implement log_level configuration support in addon/buderus_wps_addon/config.py
- [ ] T066 [US5] Add connection success/failure log messages in addon/buderus_wps_addon/main.py
- [ ] T067 [US5] Add MQTT connection status log messages in addon/buderus_wps_addon/mqtt_bridge.py
- [ ] T068 [US5] Add CAN bus debug logging (verbose mode) in addon/buderus_wps_addon/main.py
- [ ] T069 [US5] Add command execution log messages in addon/buderus_wps_addon/command_queue.py
- [ ] T070 [US5] Add error context to exception messages throughout addon

**Checkpoint**: Logs provide actionable diagnostic information for all common issues

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, edge cases, and final validation

- [ ] T071 Implement MQTT broker disconnect handling with 60s message buffer in addon/buderus_wps_addon/mqtt_bridge.py
- [ ] T072 Implement HA restart detection (re-publish discovery on homeassistant/status online) in addon/buderus_wps_addon/mqtt_bridge.py
- [ ] T073 Implement health check endpoint for Supervisor monitoring in addon/buderus_wps_addon/main.py
- [ ] T074 [P] Create S6 finish script addon/rootfs/etc/s6-overlay/s6-rc.d/buderus-wps/finish for cleanup
- [ ] T075 [P] Create tests/acceptance/test_user_stories.py with acceptance tests for all user stories
- [ ] T076 Update addon/DOCS.md with troubleshooting section
- [ ] T077 Validate all success criteria from spec.md
- [ ] T078 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational
- **User Story 2 (Phase 4)**: Depends on Foundational, US1 (config.yaml)
- **User Story 3 (Phase 5)**: Depends on Foundational, US2 (connection logic)
- **User Story 4 (Phase 6)**: Depends on US3 (MQTT bridge)
- **User Story 5 (Phase 7)**: Can start after Foundational, integrates with all stories
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational - No story dependencies
- **US2 (P1)**: Depends on US1 (config.yaml structure)
- **US3 (P1)**: Depends on US2 (connection to heat pump)
- **US4 (P2)**: Depends on US3 (MQTT bridge infrastructure)
- **US5 (P2)**: Can integrate progressively with other stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Entity configs before bridge logic
- Connection before publishing
- Sensors before controls
- Core implementation before error handling

### Parallel Opportunities

```
# Phase 2 - Entity definitions can be done in parallel:
T008, T009, T010, T011, T012 (different entity lists)
T014, T015 (different test files)

# Phase 3 - US1 tests in parallel:
T016, T017 (different test files)

# Phase 4 - US2 tests in parallel:
T024, T025 (different test aspects)

# Phase 5 - US3 tests in parallel:
T034, T035, T036, T037 (different test aspects)

# Phase 6 - US4 tests in parallel:
T049, T050, T051 (different test files)

# Phase 7 - US5 tests in parallel:
T062, T063 (different test aspects)

# Phase 8 - Polish tasks:
T074, T075 (different files)
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (installable add-on)
4. Complete Phase 4: User Story 2 (USB serial connection)
5. Complete Phase 5: User Story 3 (sensor monitoring)
6. **STOP and VALIDATE**: Test monitoring functionality independently
7. Deploy/demo if ready - users can see sensor data

### Full Implementation

1. Complete MVP (US1-US3)
2. Add User Story 4 → Control capabilities
3. Add User Story 5 → Comprehensive logging
4. Complete Phase 8: Polish → Production ready

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution requires comprehensive tests - all scenarios must be covered
