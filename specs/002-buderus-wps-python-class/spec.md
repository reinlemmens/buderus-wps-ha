# Feature Specification: Buderus WPS Heat Pump Python Class with Dynamic Parameter Discovery

**Feature Branch**: `002-buderus-wps-python-class`
**Created**: 2025-10-21
**Updated**: 2025-12-18 (Added CAN ID Discovery Protocol)
**Status**: In Progress
**Input**: User description: "create a python class representing the buderus wps heat pump. reuse the map '@KM273_elements_default' as in @fhem/26_KM273v018.pm for the parameters, their index, address, user readable name, format, min and max values"

**Critical Discovery**: Investigation of FHEM implementation revealed that CAN IDs are NOT static. They must be dynamically discovered from the device using a CAN bus discovery protocol. The @KM273_elements_default array is a fallback/reference only - real hardware uses dynamically discovered parameter definitions.

## User Scenarios & Testing *(mandatory)*

### User Story 0 - Discover Heat Pump Parameters (Priority: P0)

**NEW**: A developer needs the system to automatically discover all available parameters from the connected heat pump device, as parameter indices vary between devices and firmware versions.

**Why this priority**: Critical foundation requirement - without parameter discovery, the system cannot know which CAN IDs to use for reading/writing parameters. This must complete before any parameter operations.

**Independent Test**: Can be fully tested with a mock CAN adapter that simulates the discovery protocol responses (element count, element data chunks with binary parameter definitions).

**Acceptance Scenarios**:

1. **Given** a heat pump connection is established, **When** the system initializes, **Then** it requests the element count from the device using CAN ID 0x01FD7FE0 and receives the count on 0x09FD7FE0
2. **Given** the element count is received, **When** the system requests element data, **Then** it sends requests to 0x01FD3FE0 with offset and length (4096-byte chunks) and receives binary data on 0x09FDBFE0
3. **Given** binary element data is received, **When** the system parses it, **Then** each 18-byte header + variable-length name is correctly decoded into: idx (2 bytes), extid (7 bytes hex), max (4 bytes), min (4 bytes), len (1 byte), name (len-1 bytes)
4. **Given** all element data is parsed, **When** the discovery completes, **Then** the system has a complete parameter registry populated from the device (not from hardcoded defaults)
5. **Given** parameter discovery fails, **When** retries are exhausted, **Then** the system falls back to @KM273_elements_default as a last resort with a warning

---

### User Story 1 - Read Heat Pump Parameters (Priority: P1)

A home automation developer needs to read parameter values from the Buderus WPS heat pump to display current status and settings in their monitoring application.

**Why this priority**: Core functionality that enables basic integration - without this, no data can be retrieved from the heat pump.

**Independent Test**: Can be fully tested by instantiating the class with discovered parameters (from mock discovery), accessing parameter definitions, and verifying that parameter metadata (index, address, name, format, min/max) is correctly represented.

**Acceptance Scenarios**:

1. **Given** a Python application with completed parameter discovery, **When** the developer imports and instantiates the heat pump class, **Then** the class provides access to all heat pump parameters discovered from the device
2. **Given** the heat pump class is instantiated, **When** the developer looks up a parameter by its name (e.g., "ACCESS_LEVEL"), **Then** the class returns the parameter with its dynamically discovered idx, address (extid), format, min/max values, and read flag
3. **Given** the developer accesses a parameter, **When** they check its format, **Then** the format matches the discovered parameter definition
4. **Given** the developer retrieves a parameter, **When** they check the min and max values, **Then** these values match the constraints discovered from the device
5. **Given** the developer looks up a parameter by name, **When** the parameter was dynamically discovered, **Then** the CAN read request ID is calculated as: `rtr = 0x04003FE0 | (idx << 14)` using the discovered idx value

---

### User Story 2 - Validate Parameter Values (Priority: P2)

A developer wants to ensure that parameter values they intend to write to the heat pump are within the valid range before sending the command.

**Why this priority**: Important for preventing errors and protecting equipment - builds on P1 by adding validation capability using discovered constraints.

**Independent Test**: Can be fully tested by creating parameter instances with various values and verifying that the validation logic correctly accepts valid values and rejects invalid ones based on the dynamically discovered min/max constraints.

**Acceptance Scenarios**:

1. **Given** a parameter with discovered min and max values, **When** a developer attempts to set a value within the valid range, **Then** the value is accepted
2. **Given** a parameter with discovered min and max values, **When** a developer attempts to set a value below the minimum, **Then** the system indicates the value is invalid
3. **Given** a parameter with discovered min and max values, **When** a developer attempts to set a value above the maximum, **Then** the system indicates the value is invalid
4. **Given** a parameter with format constraints discovered from the device, **When** a developer provides a value of the wrong type, **Then** the system indicates the value is invalid
5. **Given** the developer constructs a write command, **When** validation passes, **Then** the CAN write request ID is calculated as: `txd = 0x0C003FE0 | (idx << 14)` using the discovered idx value

---

### User Story 3 - Access Parameters by Index or Name (Priority: P3)

A developer needs flexible ways to access parameters, either by their sequential index or by their human-readable name, depending on the integration method.

**Why this priority**: Enhances usability and supports different integration patterns - developers may receive index-based data from the device or prefer name-based access in their code.

**Independent Test**: Can be fully tested by accessing parameters using both index numbers and string names, verifying that both methods return the same parameter data from the discovered registry.

**Acceptance Scenarios**:

1. **Given** the heat pump class is instantiated with discovered parameters, **When** the developer accesses a parameter by its idx (e.g., idx=1), **Then** the class returns the corresponding parameter
2. **Given** the heat pump class is instantiated, **When** the developer accesses a parameter by its name (e.g., "ACCESS_LEVEL"), **Then** the class returns the correct parameter matching that name
3. **Given** the developer accesses a parameter by index, **When** they also access the same parameter by name, **Then** both methods return identical parameter data
4. **Given** an invalid index or name is provided, **When** the developer attempts to access the parameter, **Then** the system indicates the parameter does not exist

---

### User Story 4 - Cache Discovered Parameters (Priority: P2)

A developer wants the system to cache discovered parameters to avoid running the discovery protocol on every connection, reducing connection time and CAN bus traffic.

**Why this priority**: Improves user experience by reducing startup time from ~30 seconds (full discovery) to <1 second (cached). Important for production deployments.

**Independent Test**: Can be fully tested with mocks by verifying that after first discovery, subsequent connections load from cache and only re-discover if cache is invalid or missing.

**Acceptance Scenarios**:

1. **Given** the first connection to a heat pump, **When** parameter discovery completes, **Then** the discovered parameters are cached to persistent storage with device identifier
2. **Given** a subsequent connection to the same heat pump, **When** the system initializes, **Then** it loads parameters from cache instead of running full discovery
3. **Given** cached parameters exist, **When** a cache validation check detects firmware change or cache corruption, **Then** the system invalidates the cache and re-runs discovery
4. **Given** cached parameters are loaded, **When** a developer accesses parameters, **Then** they work identically to freshly discovered parameters

---

### Edge Cases

- What happens when discovery protocol fails after max retries (network issues, unsupported firmware)?
- How does the system handle incomplete element data chunks (partial 4096-byte reads)?
- What happens when a parameter name contains non-ASCII characters or null bytes?
- How are parameters with idx values outside the expected range (0-2047) handled?
- What happens when cache is corrupted or incompatible with current device firmware?
- How does the system detect when to invalidate cache (firmware updates, different heat pump)?
- What happens when accessing a parameter with an index that has gaps in the sequence (e.g., idx=13 does not exist between idx=12 and idx=14)?
- How are format types other than 'int' handled during discovery?
- What happens when attempting to access parameters before discovery is complete?
- How does the system handle parameters with negative minimum values during binary parsing?

## Requirements *(mandatory)*

### Functional Requirements

**Parameter Discovery Protocol**

- **FR-001**: The system MUST implement the CAN bus parameter discovery protocol before any parameter read/write operations
- **FR-002**: The system MUST request element count by sending to CAN ID 0x01FD7FE0 and receiving response on 0x09FD7FE0
- **FR-003**: The system MUST request element data in 4096-byte chunks by sending to CAN ID 0x01FD3FE0 with offset+length and receiving on 0x09FDBFE0
- **FR-004**: The system MUST parse binary element data with structure: idx (2 bytes), extid (7 bytes hex), max (4 bytes), min (4 bytes), len (1 byte), name (len-1 bytes string)
- **FR-005**: The system MUST populate the parameter registry from discovered elements, NOT from hardcoded @KM273_elements_default array
- **FR-006**: The system MUST fall back to @KM273_elements_default ONLY when discovery fails after retries, and MUST log a warning
- **FR-007**: The system MUST use CAN ID 0x01FDBFE0 for data buffer read requests during discovery

**Dynamic CAN ID Construction**

- **FR-008**: The system MUST calculate read request CAN ID as: `rtr = 0x04003FE0 | (idx << 14)` where idx comes from discovery
- **FR-009**: The system MUST calculate write/response CAN ID as: `txd = 0x0C003FE0 | (idx << 14)` where idx comes from discovery
- **FR-010**: The system MUST NOT use hardcoded CAN IDs for parameter access (except the fixed discovery IDs)

**Python Class Interface**

- **FR-011**: The system MUST provide a Python class that represents the Buderus WPS heat pump with dynamically discovered parameters
- **FR-012**: Each parameter MUST include the following attributes: index (idx), external ID (extid), minimum value (min), maximum value (max), format type, read flag, and human-readable text name
- **FR-013**: The class MUST support accessing parameters by their discovered index value (idx)
- **FR-014**: The class MUST support accessing parameters by their human-readable text name
- **FR-015**: The class MUST provide validation capability to check if a value is within the discovered min/max range for a given parameter
- **FR-016**: The class MUST handle parameters with non-sequential indices (e.g., idx jumps from 12 to 14)
- **FR-017**: The class MUST support parameters with negative minimum values
- **FR-018**: The class MUST distinguish between read-only parameters (read flag) and writable parameters

**Parameter Caching**

- **FR-019**: The system MUST cache discovered parameters to persistent storage after successful discovery
- **FR-020**: The system MUST load parameters from cache on subsequent connections (if cache is valid)
- **FR-021**: The system MUST validate cache integrity before use (checksum, device identifier match)
- **FR-022**: The system MUST invalidate cache and re-discover when cache validation fails
- **FR-023**: The system MUST include device identifier (serial number or unique ID) in cache to prevent loading wrong parameters

### Key Entities

- **Heat Pump**: The main entity representing the Buderus WPS heat pump system, containing a dynamically discovered collection of parameters
- **Parameter**: Represents a single configurable or readable value on the heat pump, with attributes including:
  - Index (idx): Sequential identifier for the parameter (discovered from device)
  - External ID (extid): Hexadecimal address identifier used for communication (discovered from device)
  - Min/Max: Valid range constraints for the parameter value (discovered from device)
  - Format: Data type specification (e.g., integer, temperature) (discovered from device)
  - Read flag: Indicates whether the parameter is read-only (discovered from device)
  - Text: Human-readable name/description of the parameter (discovered from device)
- **Discovery Protocol**: The CAN bus communication sequence used to retrieve parameter definitions from the heat pump
- **Parameter Cache**: Persistent storage of discovered parameters to avoid re-discovery on every connection

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parameter discovery completes successfully within 30 seconds for devices with 400-2000 parameters
- **SC-002**: The system correctly discovers and parses 100% of available parameters from the connected heat pump
- **SC-003**: Parameter lookup by name completes in under 1 second for any discovered parameter
- **SC-004**: Parameter lookup by index completes in under 1 second for any discovered parameter
- **SC-005**: 100% of discovered parameter metadata (idx, extid, min, max, format, read flag, text) is accurately decoded from binary element data
- **SC-006**: Value validation correctly identifies valid and invalid values for any parameter with discovered constraints
- **SC-007**: Cached parameter loading reduces connection time by at least 90% compared to full discovery (from ~30s to <3s)
- **SC-008**: Cache invalidation correctly detects firmware changes or device mismatches 100% of the time
- **SC-009**: CAN ID calculation formula produces correct read/write IDs for 100% of discovered parameters
- **SC-010**: Fallback to @KM273_elements_default succeeds when discovery fails, allowing degraded operation

## Assumptions

**Discovery Protocol**
- The binary element data format (18-byte header + variable name) is consistent across all Buderus WPS firmware versions
- The discovery CAN IDs (0x01FD7FE0, 0x09FD7FE0, 0x01FD3FE0, 0x09FDBFE0, 0x01FDBFE0) are fixed across all devices
- Element data is transmitted in 4096-byte chunks maximum
- Parameter count does not exceed 2047 (based on idx being 2 bytes and formula using idx << 14)

**Static Fallback**
- The @KM273_elements_default array in fhem/26_KM273v018.pm provides a reasonable fallback when discovery fails
- Fallback parameters may not match the exact device firmware, but provide degraded functionality for common parameters
- Devices that don't support the discovery protocol are rare and may require manual parameter mapping

**General**
- The class will be used for reading and validating parameter data, but actual CAN communication is handled by a separate adapter layer
- All parameters use metric units as defined in the discovered or fallback specifications
- The Python class needs to be compatible with Python 3.9 or higher (for modern type hints and dataclasses)
- The 'read' flag value of 0 indicates writable parameters and value of 1 indicates read-only parameters
- Device firmware updates may add/remove/change parameters, requiring cache invalidation
- Cache storage location is writable and persistent across restarts

## Dependencies

**Source Data**
- Source fallback data file: fhem/26_KM273v018.pm containing the @KM273_elements_default array (line 218+)
- FHEM discovery protocol reference implementation: fhem/26_KM273v018.pm KM273_ReadElementList() (line 2052-2187)
- FHEM CAN ID construction reference: fhem/26_KM273v018.pm (lines 2229-2230, 213-214)
- FHEM binary element parsing reference: fhem/26_KM273v018.pm (line 2135-2143)

**Runtime**
- Python 3.9+ runtime environment
- CAN bus adapter layer (USBtin or socketcand) for discovery protocol communication
- Persistent storage for parameter cache (filesystem or database)
- Binary data parsing capabilities (struct module or equivalent)

## In Scope

**Discovery Protocol Implementation**
- Complete CAN bus discovery protocol sequence (element count request, element data requests, binary parsing)
- Binary element data parser for 18-byte header + variable-length name structure
- Dynamic CAN ID construction using formula: `rtr = 0x04003FE0 | (idx << 14)` and `txd = 0x0C003FE0 | (idx << 14)`
- Fallback to @KM273_elements_default when discovery fails
- Parameter registry population from discovered elements

**Parameter Caching**
- Persistent cache storage of discovered parameters
- Cache validation and integrity checking
- Device identifier tracking to prevent cache mismatches
- Cache invalidation on firmware changes or corruption

**Python Class Interface**
- Parameter lookup by name and index
- Parameter validation (min/max range, type checking)
- Read-only flag enforcement
- Parameter metadata access (idx, extid, min, max, format, text)

## Out of Scope

- Actual CAN bus communication protocol implementation (handled by adapter layer)
- Network connectivity or serial port handling (adapter layer responsibility)
- User interface for displaying or modifying parameters
- Unit conversion between metric and imperial systems
- Historical data storage or logging
- Integration with specific home automation platforms (Home Assistant, OpenHAB, etc.)
- Multi-language support for parameter text names (only names from device or fallback)
- Runtime modification of parameter definitions (parameters are static after discovery)
- Automatic firmware update detection (cache invalidation is manual or triggered by validation failure)
- Support for devices that don't implement the discovery protocol (would require manual parameter mapping outside this feature)

## Technical Notes

### FHEM Reference Implementation

**Discovery Protocol Main Loop**: fhem/26_KM273v018.pm:2052-2187
```perl
# Request element count
KM273_ReadElementList() {
    # Send R01FD7FE00, receive on 0x09FD7FE0
    # Then request data: T01FD3FE08 + offset + length (4096 chunks)
    # Receive on 0x09FDBFE0
}
```

**CAN ID Construction**: fhem/26_KM273v018.pm:2229-2230
```perl
$rtr = 0x04003FE0 | ($idx << 14);  # Read request
$txd = 0x0C003FE0 | ($idx << 14);  # Response/Write
```

**Element Parsing**: fhem/26_KM273v018.pm:2135-2143
```perl
# Binary structure per element:
# idx (2 bytes) - parameter index
# extid (7 bytes hex) - extended ID
# max (4 bytes) - maximum value
# min (4 bytes) - minimum value
# len (1 byte) - name length
# name (len-1 bytes) - parameter name string
```

**Formula Documentation**: fhem/26_KM273v018.pm:213-214 (German comments explain the bit shifting)

### Critical Implementation Points

1. **Discovery MUST complete before any parameter operations** - without discovered idx values, CAN IDs cannot be calculated
2. **@KM273_elements_default is a FALLBACK ONLY** - do not use as primary parameter source
3. **Parameter idx values are device-specific** - they are NOT portable across devices or firmware versions
4. **Cache invalidation is critical** - using wrong cached parameters can corrupt device state
5. **Binary parsing must handle variable-length names** - the len byte determines name length, structure is not fixed-width
