# Feature Specification: CAN Bus Parameter Read/Write Access

**Feature Branch**: `005-can-parameter-access`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "in the library and in the CLI, foresee functionality to read and - where posible - write all parameters that are exposed on the CAN bus, preferably using their human-readable name"

## Clarifications

### Session 2025-10-23

- Q: When CAN bus communication fails, should the system retry or fail immediately? → A: Immediate failure with clear error message indicating bus unavailability and suggesting checks
- Q: How should the library handle concurrent read/write operations? → A: No concurrency support - library assumes single-threaded sequential usage, concurrent calls are undefined behavior
- Q: What is the canonical case form for parameter names? → A: Normalize to uppercase, store and display all parameter names in uppercase
- Q: What should the timeout be when the device doesn't respond to a read/write request? → A: Timeout after 5 seconds with specific "device not responding" error message
- Q: What logging strategy should the library implement? → A: Full debug logging available via verbosity flag (all operations, requests, responses), default to error-only logging. Implement a log rotating strategy limiting log file size to 10MB

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read Parameters Using Human-Readable Names (Priority: P1)

A developer or operator needs to read heat pump parameter values from the CAN bus using intuitive parameter names rather than hexadecimal addresses or numeric indices.

**Why this priority**: Core functionality that makes the library usable - technical users shouldn't need to memorize hex codes or look up indices for every operation.

**Independent Test**: Can be fully tested by requesting a parameter by its human-readable name (e.g., "COMPRESSOR_ALARM") and verifying that the correct value is returned from the CAN bus.

**Acceptance Scenarios**:

1. **Given** the library is connected to the heat pump CAN bus, **When** a user requests a parameter by its human-readable name, **Then** the library returns the current value with appropriate units
2. **Given** a user specifies an invalid parameter name, **When** the request is made, **Then** the system provides a clear error message indicating the parameter doesn't exist
3. **Given** a parameter has a specific data format (e.g., temperature), **When** the value is read, **Then** the value is converted to the appropriate unit and format
4. **Given** multiple parameters are requested in sequence, **When** reads are performed, **Then** each parameter returns its correct independent value

---

### User Story 2 - Write Parameters Using Human-Readable Names (Priority: P2)

A developer or operator needs to modify writable heat pump parameters using intuitive parameter names, with automatic validation of allowed value ranges.

**Why this priority**: Essential for control functionality - enables safe parameter modification while building on read capability from P1.

**Independent Test**: Can be fully tested by setting a writable parameter by its human-readable name and verifying that the value is written to the CAN bus and validated against min/max constraints.

**Acceptance Scenarios**:

1. **Given** the library is connected to the heat pump CAN bus, **When** a user writes a writable parameter by its human-readable name with a valid value, **Then** the value is successfully written to the device
2. **Given** a user attempts to write a read-only parameter, **When** the write request is made, **Then** the system rejects the operation with a clear error message
3. **Given** a user provides a value outside the parameter's allowed range, **When** the write request is made, **Then** the system rejects the value and indicates the valid range
4. **Given** a writable parameter is successfully modified, **When** the parameter is read back, **Then** the new value is confirmed

---

### User Story 3 - CLI Parameter Access Commands (Priority: P3)

A system administrator needs command-line tools to read and write heat pump parameters for scripting, monitoring, and manual operations.

**Why this priority**: Enables practical usage and automation - builds on library functionality with a user-friendly interface.

**Independent Test**: Can be fully tested by executing CLI commands to read/write parameters and verifying correct output format and exit codes.

**Acceptance Scenarios**:

1. **Given** the CLI tool is installed, **When** a user runs a read command with a parameter name, **Then** the parameter value is displayed with human-readable formatting
2. **Given** the CLI tool is installed, **When** a user runs a write command with a parameter name and value, **Then** the value is written and confirmation is displayed
3. **Given** a CLI read command is executed, **When** the parameter doesn't exist, **Then** the CLI returns a non-zero exit code and error message
4. **Given** a CLI write command is executed with an invalid value, **When** validation fails, **Then** the CLI displays the error and valid range information

---

### Edge Cases

- **CAN Bus Disconnection**: When attempting to read/write a parameter while the CAN bus is not connected, the system fails immediately with a clear error message indicating bus unavailability and suggesting connection checks (no automatic retries)
- **Concurrent Operations**: The library does not support concurrent read/write operations; it assumes single-threaded sequential usage and concurrent calls result in undefined behavior
- **Device Non-Response**: When a parameter read/write request is sent but the device doesn't respond within 5 seconds, the operation times out with a specific "device not responding" error message
- How are parameters with special naming characters or spaces handled?
- What happens when writing a parameter that takes time to apply on the device?
- **Case Sensitivity**: Parameter names are case-insensitive for lookup, but all parameter names are normalized to uppercase for storage and display (e.g., "compressor_alarm" is accepted but stored/returned as "COMPRESSOR_ALARM")
- What happens when the device firmware doesn't support a parameter defined in the configuration?
- How are parameters with complex data types (beyond simple integers) handled?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST support reading parameter values using human-readable parameter names
- **FR-002**: The library MUST support writing parameter values using human-readable parameter names
- **FR-003**: The library MUST validate write operations against parameter constraints (min/max values)
- **FR-004**: The library MUST distinguish between read-only and writable parameters and reject writes to read-only parameters
- **FR-005**: The library MUST map human-readable names to the appropriate CAN bus addresses (extid) for communication; parameter names MUST be normalized to uppercase for storage and display, while accepting case-insensitive input
- **FR-006**: The library MUST handle data format conversion between raw CAN values and user-friendly representations
- **FR-007**: The library MUST provide clear error messages for invalid parameter names, invalid values, or communication failures; CAN bus communication failures MUST fail immediately with diagnostic suggestions (no automatic retries); device read/write operations MUST timeout after 5 seconds if no response is received
- **FR-008**: The CLI MUST provide commands to read parameters with both human-readable and machine-parseable output formats
- **FR-009**: The CLI MUST provide commands to write parameters with value validation and confirmation
- **FR-010**: The CLI MUST return appropriate exit codes for success and various error conditions
- **FR-011**: The library MUST support accessing all 400+ parameters exposed on the CAN bus
- **FR-012**: The library MUST handle parameter name lookups efficiently (sub-second response for name resolution)
- **FR-013**: The library MUST support configurable logging with error-only logging by default and optional debug verbosity for all operations, requests, and responses
- **FR-014**: The library MUST implement log rotation limiting individual log files to 10MB maximum size

### Non-Functional Requirements

- **NFR-001**: The library MUST default to error-only logging to minimize log volume in production environments
- **NFR-002**: The library MUST support a debug/verbose mode that logs all CAN operations including parameter names, values, requests, and responses
- **NFR-003**: Log files MUST automatically rotate when reaching 10MB size limit to prevent unbounded disk usage
- **NFR-004**: All error messages MUST include sufficient context for debugging (parameter name, operation type, failure reason)
- **NFR-005**: The library MUST complete parameter name lookups in under 100 milliseconds for any of the 400+ parameters

### Key Entities

- **Parameter Name**: Human-readable identifier for a heat pump parameter (e.g., "COMPRESSOR_ALARM", "DHW_TEMP_SETPOINT")
- **Parameter Value**: Current or desired value for a parameter, in user-friendly units and format
- **Parameter Metadata**: Information about a parameter including its extid (CAN address), min/max values, format, and read/write flag
- **CAN Read Operation**: Request to retrieve a parameter value from the heat pump via CAN bus
- **CAN Write Operation**: Request to set a parameter value on the heat pump via CAN bus, subject to validation
- **CLI Command**: User-facing command-line interface for parameter operations (read/write)
- **Log Entry**: Structured record of library operations, errors, or debug information with timestamp and context

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can read any parameter using its human-readable name in under 2 seconds (under normal conditions; 5-second timeout enforced)
- **SC-002**: Users can write any writable parameter using its human-readable name in under 3 seconds (under normal conditions; 5-second timeout enforced)
- **SC-003**: 100% of parameter write attempts are validated against min/max constraints before CAN transmission
- **SC-004**: CLI commands provide clear, actionable error messages for 100% of failure scenarios
- **SC-005**: Parameter name lookups complete in under 100 milliseconds for any of the 400+ parameters

## Assumptions

- The parameter configuration file (from feature 004) is available and loaded by the library
- The CAN bus communication layer (from feature 001) is functional and provides read/write primitives
- The Python class (from feature 002) provides parameter metadata access
- Parameter names in the configuration match the FHEM reference implementation exactly
- Parameter names are case-insensitive for lookup, but all names are normalized to uppercase for storage and display
- The library will use synchronous blocking operations for read/write (async support is out of scope)
- The library assumes single-threaded sequential usage; no thread-safety guarantees are provided
- CLI commands will be single-shot operations (not an interactive shell)
- Users have appropriate permissions to access the CAN bus hardware

## Dependencies

- Feature 001: CAN bus communication via USB serial adapter
- Feature 002: Buderus WPS Python class with parameter definitions
- Feature 004: Perl configuration parser (to generate parameter configuration)
- Access to loaded parameter configuration with human-readable names and metadata
- CAN bus hardware connection and appropriate permissions

## Out of Scope

- Asynchronous or event-driven parameter monitoring
- Batch read/write operations (multiple parameters in a single command)
- Parameter change notifications or subscriptions
- Historical parameter value storage or logging
- Graphical user interface for parameter access
- Parameter search or discovery features (fuzzy matching, autocomplete)
- Custom parameter aliases or user-defined names
- Parameter grouping or categorization beyond what's in the FHEM reference
- Automatic parameter polling or refresh mechanisms
- Unit conversion beyond what's defined in the parameter metadata
- Parameter access control or authentication (assumes authorized users)
- Web API or REST interface for parameter access (CLI and library only)
