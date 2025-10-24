# Feature Specification: Perl Configuration Parser for Python Library

**Feature Branch**: `004-perl-config-parser`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "write a script that parses the config part of the perl module into a configuration file for use by the python library"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Extract Parameter Definitions from FHEM Plugin (Priority: P1)

A developer setting up the Python library needs to extract the heat pump parameter definitions from the FHEM Perl module into a format the Python library can use, avoiding manual transcription of 400+ parameters.

**Why this priority**: Core functionality that enables the Python library to use the authoritative FHEM parameter definitions without error-prone manual conversion.

**Independent Test**: Can be fully tested by running the parser script on the FHEM Perl module and verifying that the output configuration file contains all parameter definitions with correct attributes (index, extid, min, max, format, text).

**Acceptance Scenarios**:

1. **Given** the FHEM Perl module file exists, **When** the parser script is executed, **Then** a configuration file is generated containing all parameters from the KM273_elements_default array
2. **Given** the parser extracts a parameter with all attributes, **When** the configuration file is read, **Then** each parameter includes idx, extid, max, min, format, read flag, and text name
3. **Given** the FHEM module contains 400+ parameters, **When** parsing completes, **Then** all parameters are present in the output with no data loss
4. **Given** the parser encounters parameters with special characters in text names, **When** parsing completes, **Then** the text names are correctly escaped and preserved

---

### User Story 2 - Validate Parsed Configuration Data (Priority: P2)

A developer wants assurance that the parsed configuration data is accurate and complete before using it in the Python library.

**Why this priority**: Ensures data integrity - incorrect parameter definitions could lead to equipment damage or safety issues.

**Independent Test**: Can be fully tested by running validation checks on the parsed configuration file and comparing parameter counts, data types, and value ranges against the source Perl module.

**Acceptance Scenarios**:

1. **Given** the parser has generated a configuration file, **When** validation is performed, **Then** the parameter count matches the source Perl module exactly
2. **Given** a parsed parameter has min/max values, **When** validation checks the values, **Then** numeric ranges are preserved correctly (including negative numbers)
3. **Given** the configuration file contains format types, **When** validation checks formats, **Then** all format values (int, temp, etc.) match the source exactly
4. **Given** the parser encounters malformed data in the Perl module, **When** parsing occurs, **Then** clear error messages identify the problematic lines

---

### User Story 3 - Update Configuration from New FHEM Versions (Priority: P3)

A developer needs to update the Python library's configuration when a new version of the FHEM plugin is released with updated or additional parameters.

**Why this priority**: Ensures maintainability - allows easy updates when the reference protocol implementation changes.

**Independent Test**: Can be fully tested by running the parser on different versions of the FHEM module and verifying that new parameters are added and changed parameters are updated correctly.

**Acceptance Scenarios**:

1. **Given** a new FHEM plugin version with additional parameters, **When** the parser script is re-run, **Then** the configuration file includes all new parameters
2. **Given** an existing parameter has changed attributes in the new FHEM version, **When** parsing completes, **Then** the configuration file reflects the updated values
3. **Given** the parser is run multiple times, **When** the output is compared, **Then** results are deterministic and consistent
4. **Given** the parser detects changes from a previous configuration, **When** parsing completes, **Then** a summary of changes (added, modified, removed parameters) is provided

---

### Edge Cases

- What happens when the Perl module file is missing or cannot be read?
- How does the parser handle malformed Perl syntax or incomplete parameter definitions?
- What happens if a parameter has special characters or escape sequences in its text field?
- How are parameters with very large numeric values (e.g., 16777216) handled?
- What happens when the KM273_elements_default array is empty or missing?
- How does the parser handle parameters with non-sequential indices (gaps in idx values)?
- What happens when multiple parameters have duplicate extid values?
- How are comments and non-standard formatting in the Perl source handled?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The parser MUST extract all parameter definitions from the KM273_elements_default array in the FHEM Perl module
- **FR-002**: The parser MUST preserve all parameter attributes: idx, extid, max, min, format, read flag, and text name
- **FR-003**: The parser MUST output configuration data in a structured format that the Python library can load
- **FR-004**: The parser MUST handle numeric values correctly, including negative numbers and large integers
- **FR-005**: The parser MUST handle special characters and escape sequences in parameter text names
- **FR-006**: The parser MUST validate that all extracted parameters have required attributes
- **FR-007**: The parser MUST report errors clearly when encountering malformed or incomplete data
- **FR-008**: The parser MUST produce deterministic output (same input always produces same output)
- **FR-009**: The parser MUST provide a summary of extracted parameters (count, any warnings or issues)
- **FR-010**: The parser MUST support re-running on updated FHEM module versions without manual intervention

### Key Entities

- **Parameter Definition**: A complete description of a heat pump parameter from the FHEM module, including:
  - idx: Sequential index number
  - extid: Hexadecimal external identifier for CAN communication
  - max: Maximum allowed value
  - min: Minimum allowed value
  - format: Data type specification (int, temp, etc.)
  - read: Read-only flag (0 or 1)
  - text: Human-readable parameter name
- **Configuration File**: Structured data format containing all parameter definitions in a format the Python library can parse
- **Parser Script**: Tool that reads the Perl module and extracts parameter definitions
- **FHEM Module**: Source Perl file (fhem/26_KM273v018.pm) containing the authoritative parameter definitions

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Parser successfully extracts 100% of parameters defined in the FHEM module's KM273_elements_default array
- **SC-002**: Parser completes extraction in under 10 seconds for the full FHEM module
- **SC-003**: Zero data loss - all parameter attributes are preserved exactly as defined in the source
- **SC-004**: Configuration file can be successfully loaded by the Python library without errors
- **SC-005**: Parser runs successfully on any updated FHEM module version without code changes

## Assumptions

- The FHEM Perl module file is available in the repository at fhem/26_KM273v018.pm
- The KM273_elements_default array structure in the Perl module follows consistent formatting
- Each parameter entry in the array is a hash with the expected keys (idx, extid, max, min, format, read, text)
- The configuration file format will be chosen during implementation (e.g., JSON, YAML, TOML, or Python module)
- The parser script will be a one-time migration tool, though it can be re-run when the FHEM module updates
- Parser does not need to understand or validate the protocol semantics, only extract the data structure
- The Python library will handle loading and using the configuration data (parser only extracts it)

## Dependencies

- Source file: fhem/26_KM273v018.pm (FHEM reference implementation)
- Access to the Perl module file for reading
- No runtime dependencies on Perl interpreter (parser will use text parsing, not Perl execution)

## Out of Scope

- Parsing other sections of the FHEM module beyond KM273_elements_default
- Validating protocol correctness or parameter semantics
- Implementing the Python library code that uses the configuration
- Creating documentation for individual parameters (only extracting existing data)
- Supporting FHEM modules for different heat pump models
- Automatic detection of FHEM module updates
- Migration or conversion of existing Python code
- User interface for viewing or editing parsed configuration
- Integration with version control for configuration changes
- Handling of FHEM module features beyond parameter definitions (logic, commands, etc.)
