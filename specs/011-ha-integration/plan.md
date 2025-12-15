# Implementation Plan: Home Assistant Integration

**Branch**: `011-ha-integration` | **Date**: 2025-12-15 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-ha-integration/spec.md`

## Summary

Implement a Home Assistant custom integration for the Buderus WPS heat pump that provides temperature monitoring (5 sensors), compressor status visibility, energy blocking control, and DHW extra production control. The integration leverages the existing `buderus_wps` library for CAN bus communication and uses YAML configuration for setup.

**Key Deliverables**:
- Temperature sensors for Outdoor, Supply, Return, DHW, and Brine Inlet temperatures
- Binary sensor for compressor running status
- Switch entity for energy blocking control
- Number entity for DHW extra production duration (0-24 hours)
- Persistent connection with exponential backoff reconnection
- YAML-based configuration

## Technical Context

**Language/Version**: Python 3.9+ (Home Assistant compatibility requirement)
**Primary Dependencies**:
- `homeassistant` (core HA framework)
- `buderus_wps` library (existing CAN bus library - already implemented)
- `pyserial>=3.5` (USB serial communication)

**Storage**: N/A (stateless integration, relies on heat pump as source of truth)
**Testing**: `pytest` with `pytest-asyncio` for async tests, HA test fixtures
**Target Platform**: Home Assistant OS / Supervised / Container on Linux (Raspberry Pi primary target)
**Project Type**: Home Assistant custom integration (follows HA component structure)
**Performance Goals**:
- Sensor updates complete within 5 seconds
- Control commands execute within 1 second
- Memory footprint <50MB for integration

**Constraints**:
- Must use HA async I/O patterns (no blocking operations in event loop)
- Configuration limited to YAML (no UI config flow in v1.0)
- Single heat pump support only
- Local USB serial only (no remote socketcand)

**Scale/Scope**:
- 5 temperature sensors + 1 binary sensor + 1 switch + 1 number = 8 entities total
- Single device integration
- 1 coordinator managing all entities

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Library-First Architecture ✅ PASS

**Status**: COMPLIANT
**Justification**: Integration builds on existing `buderus_wps` library. The library handles all CAN protocol details. Integration layer is thin wrapper using HA DataUpdateCoordinator pattern. Already implemented: coordinator.py uses library's MenuAPI, BroadcastMonitor, and HeatPumpClient.

### Principle II: Hardware Abstraction & Protocol Fidelity ✅ PASS

**Status**: COMPLIANT
**Justification**: Integration delegates all CAN protocol to `buderus_wps` library which matches FHEM reference. Integration doesn't directly touch CAN messages. Protocol fidelity maintained at library layer (already verified in specs 001-005).

### Principle III: Safety & Reliability ✅ PASS

**Status**: COMPLIANT
**Justification**:
- Range validation happens in library layer (write_value validates against parameter metadata)
- Integration implements exponential backoff reconnection (5s → 120s max)
- All control methods are async with proper error handling
- Read-only monitoring via sensors doesn't risk equipment
- Write operations (energy block, DHW extra) logged with clear messages

### Principle IV: Comprehensive Test Coverage (NON-NEGOTIABLE) ⚠️ IN PROGRESS

**Status**: PARTIALLY COMPLIANT - Tests needed
**Current State**:
- Integration code implemented in coordinator.py, sensor.py, binary_sensor.py, switch.py, number.py
- Test stubs exist in tests/unit/test_ha_*.py and tests/integration/test_ha_*.py
- Tests currently fail due to incomplete mocking setup

**Required for COMPLIANCE**:
- [ ] Unit tests for all entity classes (sensor, binary_sensor, switch, number)
- [ ] Unit tests for coordinator data fetch and control methods
- [ ] Integration tests for reconnection logic with exponential backoff
- [ ] Integration tests for all 4 user story acceptance scenarios
- [ ] Contract tests verifying correct library API usage
- [ ] Acceptance tests for end-to-end workflows

**Action**: Phase 1 will define test contracts. Phase 2 (tasks.md) will include test implementation tasks.

### Principle V: Protocol Documentation & Traceability ✅ PASS

**Status**: COMPLIANT
**Justification**: Integration doesn't implement protocol directly - it uses library. Protocol documentation lives in specs/002-buderus-wps-python-class/protocol-broadcast-mapping.md. Integration documents which library APIs it uses (MenuAPI.status, hot_water.extra_duration, etc.) in code comments.

### Principle VI: Home Assistant Integration Standards ⚠️ IN PROGRESS

**Status**: PARTIALLY COMPLIANT - Standards followed, testing needed
**Current Implementation**:
- ✅ Uses DataUpdateCoordinator pattern for polling
- ✅ Async I/O throughout (no blocking in event loop)
- ✅ Proper entity types (sensor.SensorEntity, binary_sensor.BinarySensorEntity, etc.)
- ✅ Entity metadata (device_class, unit_of_measurement, state_class)
- ✅ Device registry integration (groups all entities under one device)
- ✅ Naming follows spec: "Heat Pump {Sensor Name}"
- ⚠️ YAML configuration (UI config flow out of scope for v1.0)
- ⚠️ Entity availability tracking on disconnect

**Missing for FULL COMPLIANCE**:
- Tests validating HA integration patterns
- Documentation of YAML configuration format

### Principle VII: CLI Design Principles ✅ N/A

**Status**: NOT APPLICABLE
**Justification**: This feature is HA integration only. CLI exists separately in buderus_wps_cli package (specs 005-006).

### Testing Gates (from Constitution Principle IV)

All gates must pass before merge:

1. ❌ All tests pass (unit, integration, contract, acceptance) - PENDING IMPLEMENTATION
2. ❌ Type checking passes (`mypy`) - NEEDS VERIFICATION
3. ❌ Linting passes (`ruff`) - NEEDS VERIFICATION
4. ❌ Coverage for all described functionality (100% of spec requirements) - PENDING
5. ❌ Documentation updated (README, configuration examples) - PENDING
6. ❌ All user story acceptance scenarios tested - PENDING

**Status Summary**: 0/6 gates passing. All test-related gates pending. This is expected for planning phase - tests will be implemented in Phase 2.

## Project Structure

### Documentation (this feature)

```
specs/011-ha-integration/
├── spec.md              # User stories, requirements (DONE)
├── plan.md              # This file (IN PROGRESS)
├── research.md          # Phase 0 output (PENDING)
├── data-model.md        # Phase 1 output (PENDING)
├── quickstart.md        # Phase 1 output (PENDING)
├── contracts/           # Phase 1 output (PENDING)
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
custom_components/buderus_wps/     # HA integration package
├── __init__.py                     # Integration setup/teardown (DONE - basic)
├── manifest.json                   # HA integration metadata (DONE)
├── const.py                        # Constants, sensor names (DONE)
├── coordinator.py                  # DataUpdateCoordinator (DONE)
├── entity.py                       # Base entity class (EXISTS on branch)
├── sensor.py                       # Temperature sensors (DONE)
├── binary_sensor.py                # Compressor status sensor (EXISTS on branch)
├── switch.py                       # Energy blocking switch (EXISTS on branch)
├── number.py                       # DHW extra duration control (EXISTS on branch)
├── select.py                       # Heating/DHW mode selects (EXISTS on branch)
└── config_flow.py                  # YAML config validation (EXISTS on branch)

buderus_wps/                        # Core library (EXISTING)
├── can_adapter.py                  # USBtin adapter
├── heat_pump.py                    # HeatPumpClient
├── menu_api.py                     # MenuAPI (high-level interface)
├── broadcast_monitor.py            # BroadcastMonitor for temps
└── ... (other library files)

tests/
├── unit/
│   ├── test_ha_sensor.py           # Sensor entity tests (STUB)
│   ├── test_ha_binary_sensor.py    # Binary sensor tests (STUB)
│   ├── test_ha_switch.py           # Switch entity tests (STUB)
│   ├── test_ha_number.py           # Number entity tests (STUB)
│   └── test_ha_config.py           # Config validation tests (STUB)
├── integration/
│   ├── test_ha_reconnection.py     # Reconnection logic tests (STUB)
│   ├── test_ha_temperature.py      # Temperature sensor integration (STUB)
│   ├── test_ha_compressor.py       # Compressor sensor integration (STUB)
│   ├── test_ha_energy_block.py     # Energy blocking integration (STUB)
│   └── test_ha_dhw_extra.py        # DHW extra integration (STUB)
└── acceptance/
    ├── test_ha_us1_temperature.py  # User Story 1 scenarios (STUB)
    ├── test_ha_us2_compressor.py   # User Story 2 scenarios (STUB)
    ├── test_ha_us3_energy_block.py # User Story 3 scenarios (STUB)
    └── test_ha_us4_dhw_extra.py    # User Story 4 scenarios (STUB)
```

**Structure Decision**: Home Assistant custom integration structure. The integration lives in `custom_components/buderus_wps/` following HA's platform-based organization. Each entity type (sensor, binary_sensor, switch, number) has its own module. The coordinator handles data fetching and state management using HA's DataUpdateCoordinator pattern. Tests are organized by layer (unit/integration/acceptance) to match constitution requirements.

## Complexity Tracking

*No constitutional violations requiring justification.*

The implementation follows all constitutional principles:
- Library-first: Integration uses existing buderus_wps library
- HA standards: Uses DataUpdateCoordinator, proper entity types, async I/O
- Safety: Error handling, exponential backoff, logging
- Testing: Test stubs in place, ready for implementation

## Phase 0: Research & Unknowns

### Research Tasks

1. **Home Assistant DataUpdateCoordinator Best Practices** ✅ RESOLVED
   - Decision: Use standard DataUpdateCoordinator pattern
   - Implementation: coordinator.py follows HA docs examples
   - Source: https://developers.home-assistant.io/docs/integration_fetching_data

2. **Broadcast Monitor Integration** ✅ RESOLVED
   - Decision: Use 5-second broadcast collection for temperature reads
   - Rationale: More reliable than RTR requests (per protocol docs)
   - Implementation: `cache = self._monitor.collect(duration=5.0)`

3. **Energy Blocking Parameter** ⚠️ NEEDS VERIFICATION
   - Spec says: Use ADDITIONAL_BLOCKED parameter
   - Protocol docs say: ADDITIONAL_BLOCKED may be read-only via CAN
   - Alternative: Use HEATING_SEASON_MODE and DHW_PROGRAM_MODE (verified writable)
   - **ACTION**: Verify ADDITIONAL_BLOCKED write capability; document alternative if needed

4. **Entity Availability on Disconnect** 🔍 NEEDS DESIGN
   - How should entities behave when connection lost?
   - Decision needed: Mark unavailable immediately or after backoff timeout?
   - **ACTION**: Define availability strategy in Phase 1

### Research Findings Summary

Most technical unknowns resolved:
- HA integration patterns: Standard DataUpdateCoordinator
- Temperature reading: BroadcastMonitor with 5s collection
- Async execution: executor_job pattern for sync library calls
- Reconnection: Exponential backoff implemented

**Remaining Unknowns** (for Phase 1):
- Energy blocking parameter verification (ADDITIONAL_BLOCKED vs mode-based)
- Entity availability strategy during reconnection
- YAML configuration schema format

## Phase 1: Design Artifacts

### Data Model (data-model.md)

**Entities**:
1. BuderusData (coordinator dataclass) - temperature dict, compressor bool, modes
2. Temperature Sensors (5x) - outdoor, supply, return, dhw, brine_in
3. Compressor Binary Sensor - derived from frequency parameter
4. Energy Block Switch - controls ADDITIONAL_BLOCKED or mode-based blocking
5. DHW Extra Number - 0-24 hour duration control

**Relationships**:
- All entities consume data from single BuderusCoordinator instance
- Coordinator manages single connection to heat pump
- No inter-entity dependencies (all read from coordinator.data)

### API Contracts (contracts/)

**Configuration Contract** (config.yaml):
```yaml
buderus_wps:
  port: /dev/ttyACM0
  scan_interval: 60  # 10-300 seconds
```

**Entity Contracts**:
- Temperature sensors: native_value (float | None), unit (°C), device_class (temperature)
- Compressor: is_on (bool), device_class (running)
- Energy block switch: is_on (bool), turn_on/turn_off async methods
- DHW extra number: native_value (int 0-24), native_min (0), native_max (24), native_step (1)

**Coordinator Contract**:
- update_interval: configurable timedelta
- _async_update_data() → BuderusData
- async_set_energy_blocking(blocked: bool)
- async_set_dhw_extra_duration(hours: int)

### Quickstart (quickstart.md)

Installation steps:
1. Copy custom_components/buderus_wps to HA config/custom_components/
2. Add YAML config with serial port
3. Restart Home Assistant
4. Verify 8 entities created (5 sensors, 1 binary_sensor, 1 switch, 1 number)

## Phase 2: Task Planning

Phase 2 will be executed via `/speckit.tasks` command to generate tasks.md.

**Expected Task Categories**:
1. Complete test implementation (unit, integration, acceptance)
2. Implement entity availability tracking
3. Verify energy blocking parameter (ADDITIONAL_BLOCKED write capability)
4. Document YAML configuration format
5. Add logging for troubleshooting
6. Verify all testing gates pass

## Next Steps

1. ✅ Complete this plan.md
2. ⏭️ Generate research.md (minimal - most research done)
3. ⏭️ Generate data-model.md, contracts/, quickstart.md
4. ⏭️ Update agent context
5. ⏭️ Run /speckit.tasks to generate task breakdown
6. ⏭️ Execute implementation tasks
7. ⏭️ Verify all testing gates pass
8. ⏭️ Merge to main

## References

- Feature Spec: [spec.md](./spec.md)
- Protocol Mapping: [../002-buderus-wps-python-class/protocol-broadcast-mapping.md](../002-buderus-wps-python-class/protocol-broadcast-mapping.md)
- Constitution: [../../.specify/memory/constitution.md](../../.specify/memory/constitution.md)
- HA Developer Docs: https://developers.home-assistant.io/
