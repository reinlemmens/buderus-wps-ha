# Feature Specification: CLI Broadcast Read Fallback

**Feature Branch**: `012-broadcast-read-fallback`
**Created**: 2025-12-06
**Status**: Draft
**Input**: User description: "CLI broadcast read fallback: Enhance the CLI read command to optionally source temperature data from CAN bus broadcasts instead of RTR requests. The heat pump returns incomplete 1-byte responses to direct RTR reads for temperature parameters, but broadcasts complete 2-byte temperature values. The read command should support a --broadcast flag to collect broadcast data for a configurable duration and return the value, or automatically fallback to broadcast when RTR returns invalid data (0.1°C for temperatures)."

## Problem Statement

The current CLI `read` command uses RTR (Remote Transmission Request) to fetch parameter values directly from the heat pump. However, for temperature parameters, the heat pump returns incomplete 1-byte responses (showing 0.1°C) instead of the expected 2-byte temperature values. The heat pump does broadcast correct temperature values on the CAN bus, which the `monitor` command can capture successfully.

Users need a reliable way to read temperature parameters that returns accurate values matching the physical readings on the heat pump display.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Explicit Broadcast Read (Priority: P1)

As a CLI user, I want to explicitly request that a parameter be read from broadcast traffic so that I can reliably obtain temperature values that the RTR method fails to retrieve correctly.

**Why this priority**: This is the core functionality that directly solves the problem of unreliable RTR reads. Without this, users cannot get accurate temperature readings from the CLI.

**Independent Test**: Can be fully tested by running `wps-cli read GT2_TEMP --broadcast` and verifying the returned temperature matches the heat pump display.

**Acceptance Scenarios**:

1. **Given** the CLI is connected to the heat pump via CAN bus, **When** user runs `read GT2_TEMP --broadcast`, **Then** the system collects broadcast traffic and returns the temperature value from broadcast data
2. **Given** the CLI is connected and --broadcast flag is used, **When** user runs `read GT2_TEMP --broadcast --duration 10`, **Then** the system collects broadcast traffic for 10 seconds before returning the value
3. **Given** the CLI is connected and --broadcast flag is used, **When** the requested parameter is not found in broadcast traffic within the duration, **Then** the system displays an appropriate error message indicating no broadcast data was captured for that parameter

---

### User Story 2 - Automatic Fallback (Priority: P2)

As a CLI user, I want the read command to automatically fallback to broadcast data when RTR returns invalid values so that I get accurate readings without having to remember which parameters require broadcast mode.

**Why this priority**: This improves user experience by making the CLI "just work" for temperature parameters without requiring explicit flags. Depends on P1 being implemented first.

**Independent Test**: Can be tested by running `wps-cli read GT2_TEMP` (without --broadcast flag) and verifying it returns accurate temperature after detecting invalid RTR response.

**Acceptance Scenarios**:

1. **Given** the CLI is connected and RTR read returns 0.1°C for a temperature parameter, **When** user runs `read GT2_TEMP`, **Then** the system automatically falls back to broadcast collection and returns the accurate value
2. **Given** the CLI is connected and RTR read returns a valid temperature value, **When** user runs `read GT2_TEMP`, **Then** the system returns the RTR value without attempting broadcast fallback
3. **Given** automatic fallback is triggered, **When** the broadcast fallback also fails to find the value, **Then** the system displays the original invalid RTR value with a warning that broadcast fallback was unsuccessful

---

### User Story 3 - Source Indication (Priority: P3)

As a CLI user, I want to see which data source (RTR or broadcast) provided the value so that I can understand how the reading was obtained and debug issues if needed.

**Why this priority**: This is a diagnostic/informational enhancement that helps users understand system behavior. Core functionality works without it.

**Independent Test**: Can be tested by running reads with and without --broadcast flag and verifying the output indicates the source.

**Acceptance Scenarios**:

1. **Given** a read is performed via RTR successfully, **When** the result is displayed, **Then** the output indicates the source was "RTR"
2. **Given** a read is performed via broadcast (explicit or fallback), **When** the result is displayed, **Then** the output indicates the source was "broadcast"
3. **Given** JSON output mode is enabled, **When** a read is performed, **Then** the JSON includes a "source" field indicating "rtr" or "broadcast"

---

### Edge Cases

- What happens when broadcast duration expires without receiving the requested parameter? System returns error with clear message
- What happens when multiple broadcast values are received for the same parameter during collection? System uses the most recent value
- What happens for non-temperature parameters with --broadcast flag? System attempts broadcast collection (may or may not find data depending on parameter)
- How does system handle parameters that only exist in RTR and not in broadcasts? Returns RTR value or error if RTR also fails
- What happens if CAN bus is disconnected during broadcast collection? System returns timeout/connection error

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: CLI read command MUST support a `--broadcast` flag to force broadcast-based reading
- **FR-002**: CLI read command MUST support a `--duration` option to specify broadcast collection time (default: 5 seconds)
- **FR-003**: When `--broadcast` is used, system MUST collect CAN bus broadcast traffic for the specified duration
- **FR-004**: System MUST map broadcast CAN IDs to parameter names using the existing broadcast mapping
- **FR-005**: System MUST detect invalid RTR responses for temperature parameters (value of 0.1°C or raw single-byte response)
- **FR-006**: When invalid RTR response is detected for temperature parameters, system MUST automatically attempt broadcast fallback
- **FR-007**: System MUST indicate the data source (RTR or broadcast) in the output
- **FR-008**: Automatic fallback MUST be disableable via a `--no-fallback` flag for debugging purposes
- **FR-009**: System MUST preserve existing read command behavior for parameters that work correctly via RTR
- **FR-010**: Broadcast read MUST support the same output formats as RTR read (text and JSON)

### Key Entities

- **Broadcast Mapping**: Association between CAN broadcast IDs (base + idx) and parameter names. Used to identify which broadcast messages correspond to which parameters.
- **Read Source**: Indicator of how a value was obtained - either "rtr" (direct request/response) or "broadcast" (passive capture from bus traffic).
- **Temperature Parameter**: Parameters with format "tem" that represent temperature values in tenths of degrees Celsius.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Temperature parameters (GT2_TEMP, GT3_TEMP, GT8_TEMP, etc.) return values within 0.5°C of the heat pump display reading when using broadcast mode
- **SC-002**: Automatic fallback activates for 100% of temperature parameters that return 0.1°C via RTR
- **SC-003**: Read command completes within the specified duration + 2 seconds overhead for broadcast mode
- **SC-004**: Users can obtain accurate temperature readings without needing to know which parameters require broadcast mode
- **SC-005**: Existing CLI read functionality for working parameters remains unchanged (no regression)
- **SC-006**: Source indication is present in all read command outputs (text and JSON formats)

## Assumptions

- The existing `BroadcastMonitor` class and `KNOWN_BROADCASTS` mapping provide sufficient coverage for common temperature parameters
- A 5-second default broadcast duration is sufficient to capture most broadcast cycles from the heat pump
- The 0.1°C value is a reliable indicator of invalid RTR response for temperature parameters (not a valid temperature reading)
- Parameters that work via RTR should continue to use RTR as the primary method (broadcast is fallback only)

## Out of Scope

- Adding new parameters to the broadcast mapping (that is a separate enhancement)
- Modifying the RTR protocol implementation to fix the 1-byte response issue
- Real-time continuous monitoring (that is the existing `monitor` command)
- Write operations (only read is affected)
