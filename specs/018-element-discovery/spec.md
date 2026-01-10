# Feature Specification: Element Discovery Protocol

**Feature Branch**: `018-element-discovery`
**Created**: 2026-01-10
**Status**: Draft
**Input**: User description: "element discovery - investigate the current implementation (which has been fixed) and document it as a feature specification"

## Overview

Element discovery is a protocol for automatically retrieving parameter definitions from Buderus WPS heat pumps at runtime. This is essential because different heat pump firmware versions may have different parameter indices (idx values) for the same parameter names. Without discovery, parameter reads would use incorrect CAN IDs and return wrong values.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Parameter Index Calibration (Priority: P1)

When the Home Assistant integration starts, it automatically discovers the heat pump's actual parameter indices, ensuring all sensor readings use the correct CAN IDs regardless of firmware version.

**Why this priority**: This is the core functionality that enables the integration to work reliably across different heat pump models and firmware versions. Without it, temperature sensors and other readings would return incorrect values.

**Independent Test**: Can be fully tested by restarting the integration and verifying that all parameter readings match known good values from FHEM or the heat pump display.

**Acceptance Scenarios**:

1. **Given** a freshly installed integration, **When** the integration starts, **Then** it discovers parameter indices from the heat pump and updates its internal registry
2. **Given** a heat pump with firmware where GT3_TEMP is at idx=682 (not static default 681), **When** discovery completes, **Then** GT3_TEMP readings use CAN ID based on idx=682
3. **Given** discovery finds 2000+ elements, **When** the registry is updated, **Then** only parameters with changed indices are logged at INFO level

---

### User Story 2 - Discovery Caching for Fast Startup (Priority: P2)

After initial discovery, parameter definitions are cached to disk so subsequent starts don't need to re-run the full discovery protocol, reducing startup time from ~30 seconds to under 1 second.

**Why this priority**: Improves user experience by reducing integration startup time. However, correct readings (P1) are more important than fast startup.

**Independent Test**: Can be tested by restarting the integration twice - first restart triggers full discovery, second restart loads from cache in under 1 second.

**Acceptance Scenarios**:

1. **Given** no cache exists, **When** discovery completes successfully, **Then** results are saved to a persistent cache file
2. **Given** a valid cache exists, **When** the integration starts, **Then** it loads from cache without querying the heat pump
3. **Given** a cache older than 24 hours, **When** the integration starts, **Then** it refreshes the cache from the heat pump

---

### User Story 3 - Discovery Resilience and Recovery (Priority: P2)

If discovery fails or returns incomplete results, the system retries automatically. On fresh installs, discovery failure prevents startup (fail fast). On subsequent starts, the system falls back to the last successful discovery cache - never to static defaults for idx values.

**Why this priority**: Ensures the integration never silently returns incorrect readings. Static default indices are from one specific firmware version and produce garbage values on other versions.

**Independent Test**: Can be tested by simulating CAN bus issues and verifying the system either recovers from cache or fails clearly with actionable error message.

**Acceptance Scenarios**:

1. **Given** discovery returns fewer than 95% of expected bytes, **When** the retry count is below 3, **Then** discovery is retried after a 1-second delay
2. **Given** discovery fails after 3 retries on fresh install (no cache), **When** no valid cache exists, **Then** integration startup fails with clear error message
3. **Given** discovery fails but valid cache exists from previous successful discovery, **When** cache is loaded, **Then** cached idx values are used (not static defaults)
4. **Given** the cache file contains an incomplete previous discovery, **When** the integration starts, **Then** it forces a fresh discovery
5. **Given** static defaults exist for a parameter, **When** discovery has not provided an idx, **Then** that parameter is marked unavailable (not using static idx)

---

### User Story 4 - Index Update Transparency (Priority: P3)

When parameter indices are updated from discovery, the system logs the old and new CAN IDs to help diagnose communication issues.

**Why this priority**: Aids troubleshooting but doesn't affect core functionality.

**Independent Test**: Can be tested by checking logs after discovery for idx change messages.

**Acceptance Scenarios**:

1. **Given** a parameter's idx differs from static default, **When** registry is updated, **Then** a log entry shows "Updated {name}: idx {old} -> {new} (CAN ID 0x{old_id} -> 0x{new_id})"

---

### Edge Cases

- What happens when heat pump returns 0 bytes of element data? → Returns empty list, logs warning
- How does system handle corrupted cache files? → Logs warning, performs fresh discovery
- What happens if CAN bus has heavy traffic during discovery? → Retries with timeout, filters unrelated frames
- How does system handle non-ASCII parameter names? → Logs warning, skips malformed entries

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST query the heat pump for total element data length before starting bulk transfer
- **FR-002**: System MUST read element data in chunks of 4096 bytes maximum
- **FR-003**: System MUST parse 18-byte element headers containing idx (2B), extid (7B), max (4B), min (4B), name_length (1B)
- **FR-004**: System MUST update parameter registry when discovered idx differs from static default
- **FR-005**: System MUST cache discovery results in JSON format with metadata (timestamp, completion status, byte counts)
- **FR-006**: System MUST retry incomplete discovery up to 3 times before failing
- **FR-007**: System MUST validate discovery completeness (at least 95% of reported bytes received)
- **FR-008**: System MUST use static defaults ONLY for format and read-only flags, NEVER for idx values
- **FR-009**: System MUST fail startup on fresh install if discovery fails (no silent fallback to static idx)
- **FR-010**: System MUST fall back to last successful discovery cache if current discovery fails (cache-only fallback)
- **FR-011**: System MUST mark parameters as unavailable if their idx has not been discovered or cached
- **FR-012**: System MUST support cache age limits to force periodic refresh
- **FR-013**: System MUST log CAN ID changes when parameter indices are updated

### Key Entities

- **DiscoveredElement**: Represents a parameter discovered from the heat pump (idx, extid, text, min_value, max_value)
- **ElementDiscovery**: Orchestrates the CAN protocol for bulk element transfer
- **ElementListParser**: Parses binary element data into DiscoveredElement objects
- **Parameter Registry**: Maintains lookup tables by name and idx, updated from discovery results

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Discovery completes within 30 seconds for heat pumps reporting up to 100KB of element data
- **SC-002**: All sensor readings match values from FHEM when using same heat pump (within measurement precision)
- **SC-003**: Integration starts from cache in under 5 seconds after initial discovery
- **SC-004**: Discovery succeeds on first attempt at least 90% of the time under normal CAN bus conditions
- **SC-005**: Parameter index mismatches (causing wrong readings) are eliminated for all discovered parameters

## Assumptions

- Heat pump firmware supports the element list discovery protocol (CAN IDs 0x01FD7FE0, 0x09FD7FE0, 0x01FD3FE0, 0x09FDBFE0)
- Static parameter defaults (parameter_defaults.py) contain correct format types for known parameters (but idx values are NOT reliable across firmware versions)
- CAN bus operates at 125 kbit/s with extended (29-bit) identifiers
- Cache storage location must be persistent across integration restarts (not /tmp in containerized environments)
- First-time users have a working CAN connection to complete initial discovery

## Dependencies

- USBtinAdapter for CAN communication (001-can-usb-serial)
- Parameter registry with static defaults (002-buderus-wps-python-class)
- Home Assistant coordinator integration (011-ha-integration)

## Out of Scope

- Discovering parameter format types (always derived from static defaults)
- Writing discovered parameters back to heat pump EEPROM
- Automatic firmware version detection beyond element list differences
- Real-time parameter index monitoring for firmware updates

## Implementation Gap

**Current implementation differs from this spec in these areas:**

1. **Static idx fallback** - Current code falls back to static default idx values when discovery fails. This produces incorrect readings and should be changed to fail-fast or cache-only fallback.

2. **Cache location** - Current code uses `/tmp/buderus_wps_elements.json` which is ephemeral in HA containers. Should use `/config/` for persistence.

3. **Parameter availability** - Current code doesn't mark parameters as unavailable when idx is not discovered. Should refuse to read parameters without discovered idx.

These gaps need to be addressed in `/speckit.plan` and `/speckit.implement`.
