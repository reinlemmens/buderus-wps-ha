# Feature Specification: Buderus WPS Heat Pump Python Class

**Feature Branch**: `002-buderus-wps-python-class`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "create a python class representing the buderus wps heat pump. reuse the map '@KM273_elements_default' as in @fhem/26_KM273v018.pm for the parameters, their index, address, user readable name, format, min and max values"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read Heat Pump Parameters (Priority: P1)

A home automation developer needs to read parameter values from the Buderus WPS heat pump to display current status and settings in their monitoring application.

**Why this priority**: Core functionality that enables basic integration - without this, no data can be retrieved from the heat pump.

**Independent Test**: Can be fully tested by instantiating the class, accessing parameter definitions, and verifying that parameter metadata (index, address, name, format, min/max) is correctly represented.

**Acceptance Scenarios**:

1. **Given** a Python application, **When** the developer imports and instantiates the heat pump class, **Then** the class provides access to all heat pump parameters defined in the KM273 specification
2. **Given** the heat pump class is instantiated, **When** the developer looks up a parameter by its name (e.g., "ACCESS_LEVEL"), **Then** the class returns the parameter with its index, address (extid), format, min/max values, and read flag
3. **Given** the developer accesses a parameter, **When** they check its format, **Then** the format matches the KM273 specification (int, temp, or other defined formats)
4. **Given** the developer retrieves a parameter, **When** they check the min and max values, **Then** these values match the constraints defined in the KM273 specification

---

### User Story 2 - Validate Parameter Values (Priority: P2)

A developer wants to ensure that parameter values they intend to write to the heat pump are within the valid range before sending the command.

**Why this priority**: Important for preventing errors and protecting equipment - builds on P1 by adding validation capability.

**Independent Test**: Can be fully tested by creating parameter instances with various values and verifying that the validation logic correctly accepts valid values and rejects invalid ones based on the min/max constraints.

**Acceptance Scenarios**:

1. **Given** a parameter with defined min and max values, **When** a developer attempts to set a value within the valid range, **Then** the value is accepted
2. **Given** a parameter with defined min and max values, **When** a developer attempts to set a value below the minimum, **Then** the system indicates the value is invalid
3. **Given** a parameter with defined min and max values, **When** a developer attempts to set a value above the maximum, **Then** the system indicates the value is invalid
4. **Given** a parameter with format constraints (e.g., integer only), **When** a developer provides a value of the wrong type, **Then** the system indicates the value is invalid

---

### User Story 3 - Access Parameters by Index or Name (Priority: P3)

A developer needs flexible ways to access parameters, either by their sequential index or by their human-readable name, depending on the integration method.

**Why this priority**: Enhances usability and supports different integration patterns - developers may receive index-based data from the device or prefer name-based access in their code.

**Independent Test**: Can be fully tested by accessing parameters using both index numbers and string names, verifying that both methods return the same parameter data.

**Acceptance Scenarios**:

1. **Given** the heat pump class is instantiated, **When** the developer accesses a parameter by its index (e.g., idx=1), **Then** the class returns the corresponding parameter
2. **Given** the heat pump class is instantiated, **When** the developer accesses a parameter by its name (e.g., "ACCESS_LEVEL"), **Then** the class returns the correct parameter matching that name
3. **Given** the developer accesses a parameter by index, **When** they also access the same parameter by name, **Then** both methods return identical parameter data
4. **Given** an invalid index or name is provided, **When** the developer attempts to access the parameter, **Then** the system indicates the parameter does not exist

---

### Edge Cases

- What happens when a parameter has min=0 and max=0 (indicating a flag or read-only status parameter)?
- How does the system handle parameters with negative minimum values (e.g., temperature parameters)?
- What happens when accessing a parameter with an index that has gaps in the sequence (e.g., idx=13 does not exist between idx=12 and idx=14)?
- How are format types other than 'int' handled (if they exist in the specification)?
- What happens when attempting to access parameters before the class is properly initialized?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a Python class that represents the Buderus WPS heat pump
- **FR-002**: The class MUST contain all parameters defined in the KM273_elements_default array from the Perl module file (26_KM273v018.pm)
- **FR-003**: Each parameter MUST include the following attributes: index (idx), external ID (extid), minimum value (min), maximum value (max), format type, read flag, and human-readable text name
- **FR-004**: The class MUST support accessing parameters by their sequential index value
- **FR-005**: The class MUST support accessing parameters by their human-readable text name
- **FR-006**: The class MUST provide validation capability to check if a value is within the allowed min/max range for a given parameter
- **FR-007**: The class MUST preserve the exact data structure from the KM273_elements_default array, including all numeric values and text identifiers
- **FR-008**: The class MUST handle parameters with non-sequential indices (e.g., idx jumps from 12 to 14)
- **FR-009**: The class MUST support parameters with negative minimum values
- **FR-010**: The class MUST distinguish between read-only parameters (read flag) and writable parameters

### Key Entities

- **Heat Pump**: The main entity representing the Buderus WPS heat pump system, containing a complete collection of parameters
- **Parameter**: Represents a single configurable or readable value on the heat pump, with attributes including:
  - Index: Sequential identifier for the parameter
  - External ID (extid): Hexadecimal address identifier used for communication
  - Min/Max: Valid range constraints for the parameter value
  - Format: Data type specification (e.g., integer, temperature)
  - Read flag: Indicates whether the parameter is read-only
  - Text: Human-readable name/description of the parameter

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can access any of the 400+ heat pump parameters defined in the KM273 specification
- **SC-002**: Parameter lookup by name completes in under 1 second for any parameter
- **SC-003**: Parameter lookup by index completes in under 1 second for any parameter
- **SC-004**: 100% of parameter metadata (index, extid, min, max, format, read flag, text) matches the original KM273 specification
- **SC-005**: Value validation correctly identifies valid and invalid values for any parameter with defined constraints

## Assumptions

- The KM273_elements_default array in the Perl module (fhem/26_KM273v018.pm) is the authoritative source for all parameter definitions
- The class will be used for reading and validating parameter data, but actual communication with the heat pump hardware is handled separately
- All parameters use metric units as defined in the original specification
- The Python class needs to be compatible with Python 3.7 or higher (standard assumption for modern Python projects)
- Parameter definitions are static and will be loaded once during class initialization
- The 'read' flag value of 0 indicates writable parameters and value of 1 indicates read-only parameters

## Dependencies

- Source data file: fhem/26_KM273v018.pm containing the @KM273_elements_default array
- Python 3.7+ runtime environment
- No external Python libraries required for core functionality (optional: type hinting with typing module)

## Out of Scope

- Actual communication protocol implementation for reading/writing values to the physical heat pump
- Network connectivity or serial communication handling
- User interface for displaying or modifying parameters
- Unit conversion between metric and imperial systems
- Historical data storage or logging
- Integration with specific home automation platforms (Home Assistant, OpenHAB, etc.)
- Multi-language support for parameter text names (only English names from the source data)
- Runtime modification of parameter definitions (parameters are static after class initialization)
