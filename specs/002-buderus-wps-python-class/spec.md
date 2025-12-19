# Feature Specification: Buderus WPS Heat Pump Python Class with Dynamic Parameter Discovery

**Feature Branch**: `002-buderus-wps-python-class`
**Created**: 2025-10-21
**Updated**: 2025-12-18
**Status**: Draft (Updated with CAN ID Discovery Protocol)
**Input**: User description: "create a python class representing the buderus wps heat pump with dynamic parameter discovery via CAN bus protocol"

## Overview

This feature implements a Python class that discovers and represents all parameters of the Buderus WPS heat pump. Critical finding: CAN IDs are NOT static - they must be dynamically constructed based on parameter indices discovered from the device at runtime.

**Key Protocol Insight**: The FHEM reference implementation reveals that parameter definitions are discovered from the device using a binary protocol, not hardcoded. The @KM273_elements_default array serves only as a fallback when discovery fails.

## User Scenarios & Testing *(mandatory)*

### User Story 0 - Discover Parameters from Device (Priority: P0)

A home automation developer needs to discover all available parameters from the connected Buderus WPS heat pump before any read/write operations can occur.

**Why this priority**: Critical foundation - without discovery, CAN IDs cannot be constructed and no parameter access is possible. Must execute before any other operations.

**Independent Test**: Can be fully tested by executing the discovery protocol sequence, parsing binary responses, and verifying that parameter metadata (idx, extid, min, max, format, read, text) is correctly extracted.

**Acceptance Scenarios**:

1. **Given** a CAN bus connection to the heat pump, **When** the developer initiates parameter discovery, **Then** the system requests the element count using CAN ID 0x01FD7FE0
2. **Given** the element count is received, **When** the system requests element data, **Then** it retrieves data in 4096-byte chunks using CAN ID 0x01FD3FE0
3. **Given** binary element data is received, **When** the system parses it, **Then** each element's idx, extid, max, min, len, and name are correctly extracted
4. **Given** parameter discovery completes successfully, **When** the developer accesses parameters, **Then** CAN IDs are dynamically constructed using the formula `rtr = 0x04003FE0 | (idx << 14)`
5. **Given** parameter discovery fails (timeout, device unavailable), **When** the developer requests parameters, **Then** the system falls back to @KM273_elements_default static data

---

### User Story 1 - Read Heat Pump Parameters (Priority: P1)

A home automation developer needs to read parameter values from the Buderus WPS heat pump to display current status and settings in their monitoring application.

**Why this priority**: Core functionality that enables basic integration - without this, no data can be retrieved from the heat pump.

**Independent Test**: Can be fully tested by instantiating the class, triggering discovery, accessing parameter definitions, and verifying that parameter metadata (index, address, name, format, min/max) is correctly represented.

**Acceptance Scenarios**:

1. **Given** a Python application, **When** the developer imports and instantiates the heat pump class, **Then** the class provides access to all heat pump parameters discovered from the device (or fallback data)
2. **Given** the heat pump class is instantiated, **When** the developer looks up a parameter by its name (e.g., "ACCESS_LEVEL"), **Then** the class returns the parameter with its index, address (extid), format, min/max values, and read flag
3. **Given** the developer accesses a parameter, **When** they request its CAN ID, **Then** the system calculates `rtr = 0x04003FE0 | (idx << 14)` for read requests
4. **Given** the developer accesses a parameter, **When** they check its format, **Then** the format matches the discovered or KM273 specification (int, temp, or other defined formats)
5. **Given** the developer retrieves a parameter, **When** they check the min and max values, **Then** these values match the discovered constraints (or fallback KM273 constraints)

---

### User Story 2 - Validate Parameter Values (Priority: P2)

A developer wants to ensure that parameter values they intend to write to the heat pump are within the valid range before sending the command.

**Why this priority**: Important for preventing errors and protecting equipment - builds on P1 by adding validation capability.

**Independent Test**: Can be fully tested by creating parameter instances with various values and verifying that the validation logic correctly accepts valid values and rejects invalid ones based on the min/max constraints.

**Acceptance Scenarios**:

1. **Given** a parameter with discovered min and max values, **When** a developer attempts to set a value within the valid range, **Then** the value is accepted
2. **Given** a parameter with discovered min and max values, **When** a developer attempts to set a value below the minimum, **Then** the system indicates the value is invalid
3. **Given** a parameter with discovered min and max values, **When** a developer attempts to set a value above the maximum, **Then** the system indicates the value is invalid
4. **Given** a writable parameter (read flag = 0), **When** the developer requests the write CAN ID, **Then** the system calculates `txd = 0x0C003FE0 | (idx << 14)`
5. **Given** a read-only parameter (read flag != 0), **When** the developer attempts to write, **Then** the system rejects the operation

---

### User Story 3 - Access Parameters by Index or Name (Priority: P3)

A developer needs flexible ways to access parameters, either by their sequential index or by their human-readable name, depending on the integration method.

**Why this priority**: Enhances usability and supports different integration patterns - developers may receive index-based data from the device or prefer name-based access in their code.

**Independent Test**: Can be fully tested by accessing parameters using both index numbers and string names, verifying that both methods return the same parameter data.

**Acceptance Scenarios**:

1. **Given** parameters are discovered, **When** the developer accesses a parameter by its idx value, **Then** the class returns the corresponding parameter with calculated CAN IDs
2. **Given** parameters are discovered, **When** the developer accesses a parameter by its text name, **Then** the class returns the correct parameter matching that name
3. **Given** the developer accesses a parameter by index, **When** they also access the same parameter by name, **Then** both methods return identical parameter data
4. **Given** an invalid index or name is provided, **When** the developer attempts to access the parameter, **Then** the system indicates the parameter does not exist

---

### User Story 4 - Cache Discovered Parameters (Priority: P2)

A developer wants discovered parameters to be cached to avoid re-running the 30+ second discovery protocol on every connection.

**Why this priority**: Performance optimization - discovery takes ~30 seconds; caching enables rapid reconnection.

**Independent Test**: Can be fully tested by running discovery, verifying cache creation, then loading from cache without device access.

**Acceptance Scenarios**:

1. **Given** parameters are discovered successfully, **When** the discovery completes, **Then** the system persists discovered parameters to cache storage
2. **Given** a valid cache exists, **When** the developer initializes the heat pump class, **Then** parameters are loaded from cache without device discovery
3. **Given** cache data is corrupted or invalid, **When** the developer initializes the class, **Then** the system falls back to discovery or static data
4. **Given** the device firmware version changes, **When** the developer connects, **Then** the system invalidates cache and re-discovers parameters

---

### Edge Cases

- What happens when a parameter has min=0 and max=0 (indicating a flag or read-only status parameter)?
- How does the system handle parameters with negative minimum values (e.g., temperature parameters)?
- What happens when accessing a parameter with an index that has gaps in the sequence (e.g., idx=13 does not exist between idx=12 and idx=14)?
- How are format types other than 'int' handled (if they exist in the specification)?
- What happens when attempting to access parameters before discovery completes?
- How does the system handle incomplete element data chunks (less than 4096 bytes)?
- What happens if element names contain non-ASCII characters or null bytes?
- How are elements with idx values outside the expected range handled?
- What happens when the element count response differs from actual elements received?
- How does the system recover from partial discovery (some elements parsed, then error)?

## Requirements *(mandatory)*

### Functional Requirements - Discovery Protocol

- **FR-001**: The system MUST implement the CAN ID discovery protocol before any parameter read/write operations
- **FR-002**: The system MUST request element count by sending to CAN ID 0x01FD7FE0 and receiving on 0x09FD7FE0
- **FR-003**: The system MUST request element data by sending to CAN ID 0x01FD3FE0 with offset and length, receiving on 0x09FDBFE0
- **FR-004**: The system MUST support reading element data in 4096-byte chunks
- **FR-005**: The system MUST parse binary element data using the structure: idx (2 bytes), extid (7 bytes), max (4 bytes), min (4 bytes), len (1 byte), name (len-1 bytes)
- **FR-006**: The system MUST fall back to @KM273_elements_default static data when discovery fails
- **FR-007**: The system MUST use discovered idx values to construct CAN IDs dynamically

### Functional Requirements - CAN ID Construction

- **FR-008**: The system MUST construct read request CAN IDs using formula: `rtr = 0x04003FE0 | (idx << 14)`
- **FR-009**: The system MUST construct write/response CAN IDs using formula: `txd = 0x0C003FE0 | (idx << 14)`
- **FR-010**: The system MUST NOT use hardcoded CAN IDs for parameter access (only fixed discovery IDs allowed)

### Functional Requirements - Python Class

- **FR-011**: The system MUST provide a Python class that represents the Buderus WPS heat pump
- **FR-012**: The class MUST contain all parameters discovered from the device or loaded from fallback data
- **FR-013**: Each parameter MUST include the following attributes: index (idx), external ID (extid), minimum value (min), maximum value (max), format type, read flag, and human-readable text name
- **FR-014**: The class MUST support accessing parameters by their sequential index value
- **FR-015**: The class MUST support accessing parameters by their human-readable text name
- **FR-016**: The class MUST provide validation capability to check if a value is within the allowed min/max range for a given parameter
- **FR-017**: The class MUST handle parameters with non-sequential indices (e.g., idx jumps from 12 to 14)
- **FR-018**: The class MUST support parameters with negative minimum values
- **FR-019**: The class MUST distinguish between read-only parameters (read flag) and writable parameters

### Functional Requirements - Caching

- **FR-020**: The system MUST cache discovered parameters to persistent storage
- **FR-021**: The system MUST validate cache before use (checksum, device identifier)
- **FR-022**: The system MUST invalidate cache when device firmware changes
- **FR-023**: The system MUST support cache bypass for forced re-discovery

### Key Entities

- **Heat Pump**: The main entity representing the Buderus WPS heat pump system, containing a complete collection of discovered or fallback parameters
- **Parameter**: Represents a single configurable or readable value on the heat pump, with attributes including:
  - Index (idx): Parameter index used for CAN ID construction
  - External ID (extid): Hexadecimal address identifier (7 bytes)
  - Min/Max: Valid range constraints for the parameter value
  - Format: Data type specification (e.g., integer, temperature)
  - Read flag: Indicates whether the parameter is read-only
  - Text: Human-readable name/description of the parameter
- **Discovery Protocol**: The CAN bus message sequence for retrieving parameter definitions from the device
- **Parameter Cache**: Persistent storage of discovered parameters for fast reconnection

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parameter discovery completes within 30 seconds for 400-2000 parameters
- **SC-002**: A developer can access any discovered heat pump parameter
- **SC-003**: Parameter lookup by name completes in under 1 second for any parameter
- **SC-004**: Parameter lookup by index completes in under 1 second for any parameter
- **SC-005**: 100% of discovered parameter metadata (idx, extid, min, max, format, read flag, text) is accurately parsed
- **SC-006**: Value validation correctly identifies valid and invalid values for any parameter with defined constraints
- **SC-007**: Cached parameter loading completes in under 3 seconds (90% faster than discovery)
- **SC-008**: Cache invalidation correctly detects firmware changes or corruption
- **SC-009**: Fallback to static data succeeds when discovery fails
- **SC-010**: CAN ID construction produces correct values matching FHEM reference implementation

## Assumptions

### Discovery Protocol Assumptions

- The binary element data format is consistent across Buderus WPS firmware versions
- The fixed discovery CAN IDs (0x01FD7FE0, 0x09FD7FE0, 0x01FD3FE0, 0x09FDBFE0, 0x01FDBFE0) are stable
- Element data is transmitted in 4096-byte chunks as documented in FHEM
- The element count response accurately reflects the number of discoverable elements

### Fallback Assumptions

- The @KM273_elements_default array in fhem/26_KM273v018.pm is a valid fallback when discovery fails
- Fallback data may not perfectly match connected device but provides reasonable defaults
- Developers are informed when operating in fallback mode

### General Assumptions

- The class will be used for discovering, reading, and validating parameter data
- Actual CAN bus communication layer is provided by existing infrastructure
- All parameters use metric units as defined in the original specification
- The Python class needs to be compatible with Python 3.9 or higher (Home Assistant compatibility)
- The 'read' flag value of 0 indicates writable parameters and value of 1+ indicates read-only parameters

## Dependencies

- CAN bus adapter layer (USBtin or socketcand) for device communication
- Source data file: fhem/26_KM273v018.pm containing @KM273_elements_default array (fallback)
- Python 3.9+ runtime environment
- Persistent storage for parameter cache (filesystem)

## Out of Scope

- Implementation of the CAN bus adapter layer (covered by separate feature)
- User interface for displaying or modifying parameters
- Unit conversion between metric and imperial systems
- Historical data storage or logging
- Integration with specific home automation platforms (Home Assistant integration is separate)
- Multi-language support for parameter text names
- Runtime modification of parameter definitions after discovery/load

## Technical Notes (for implementers)

### FHEM Reference Implementation Locations

- Discovery main loop: `fhem/26_KM273v018.pm:2052-2187`
- CAN ID construction formulas: `fhem/26_KM273v018.pm:2229-2230`
- Element binary parsing: `fhem/26_KM273v018.pm:2135-2143`
- Formula documentation (German): `fhem/26_KM273v018.pm:213-214`
- Fallback data array: `fhem/26_KM273v018.pm:218-2009`

### Binary Element Structure

```
Offset  Size  Field    Description
0       2     idx      Parameter index (uint16, little-endian)
2       7     extid    External ID (hex string, 14 chars)
9       4     max      Maximum value (int32, little-endian)
13      4     min      Minimum value (int32, little-endian)
17      1     len      Name length (uint8)
18      N     name     Parameter name (len-1 bytes, null-terminated)
```

### Fixed Discovery CAN IDs

| Purpose                  | Send CAN ID | Receive CAN ID |
| ------------------------ | ----------- | -------------- |
| Element count request    | 0x01FD7FE0  | 0x09FD7FE0     |
| Element data request     | 0x01FD3FE0  | 0x09FDBFE0     |
| Data buffer read request | 0x01FDBFE0  | -              |
