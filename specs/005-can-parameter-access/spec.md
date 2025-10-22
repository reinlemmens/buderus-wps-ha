# Feature Specification: CAN Bus Parameter Read/Write Access

**Feature Branch**: `005-can-parameter-access`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "in the library and in the CLI, foresee functionality to read and - where posible - write all parameters that are exposed on the CAN bus, preferably using their human-readable name"

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

- What happens when attempting to read a parameter while the CAN bus is not connected?
- How does the system handle concurrent read/write operations on the same parameter?
- What happens when a parameter name exists but the device doesn't respond to the read request?
- How are parameters with special naming characters or spaces handled?
- What happens when writing a parameter that takes time to apply on the device?
- How does the system handle case sensitivity in parameter names (e.g., "compressor_alarm" vs. "COMPRESSOR_ALARM")?
- What happens when the device firmware doesn't support a parameter defined in the configuration?
- How are parameters with complex data types (beyond simple integers) handled?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The library MUST support reading parameter values using human-readable parameter names
- **FR-002**: The library MUST support writing parameter values using human-readable parameter names
- **FR-003**: The library MUST validate write operations against parameter constraints (min/max values)
- **FR-004**: The library MUST distinguish between read-only and writable parameters and reject writes to read-only parameters
- **FR-005**: The library MUST map human-readable names to the appropriate CAN bus addresses (extid) for communication
- **FR-006**: The library MUST handle data format conversion between raw CAN values and user-friendly representations
- **FR-007**: The library MUST provide clear error messages for invalid parameter names, invalid values, or communication failures
- **FR-008**: The CLI MUST provide commands to read parameters with both human-readable and machine-parseable output formats
- **FR-009**: The CLI MUST provide commands to write parameters with value validation and confirmation
- **FR-010**: The CLI MUST return appropriate exit codes for success and various error conditions
- **FR-011**: The library MUST support accessing all 400+ parameters exposed on the CAN bus
- **FR-012**: The library MUST handle parameter name lookups efficiently (sub-second response for name resolution)

### Key Entities

- **Parameter Name**: Human-readable identifier for a heat pump parameter (e.g., "COMPRESSOR_ALARM", "DHW_TEMP_SETPOINT")
- **Parameter Value**: Current or desired value for a parameter, in user-friendly units and format
- **Parameter Metadata**: Information about a parameter including its extid (CAN address), min/max values, format, and read/write flag
- **CAN Read Operation**: Request to retrieve a parameter value from the heat pump via CAN bus
- **CAN Write Operation**: Request to set a parameter value on the heat pump via CAN bus, subject to validation
- **CLI Command**: User-facing command-line interface for parameter operations (read/write)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can read any parameter using its human-readable name in under 2 seconds
- **SC-002**: Users can write any writable parameter using its human-readable name in under 3 seconds
- **SC-003**: 100% of parameter write attempts are validated against min/max constraints before CAN transmission
- **SC-004**: CLI commands provide clear, actionable error messages for 100% of failure scenarios
- **SC-005**: Parameter name lookups complete in under 100 milliseconds for any of the 400+ parameters

## Assumptions

- The parameter configuration file (from feature 004) is available and loaded by the library
- The CAN bus communication layer (from feature 001) is functional and provides read/write primitives
- The Python class (from feature 002) provides parameter metadata access
- Parameter names in the configuration match the FHEM reference implementation exactly
- Case-insensitive parameter name matching is acceptable (system will normalize to uppercase or lowercase)
- The library will use synchronous blocking operations for read/write (async support is out of scope)
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
