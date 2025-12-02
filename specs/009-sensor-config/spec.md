# Feature Specification: Sensor Configuration and Installation Settings

**Feature Branch**: `009-sensor-config`
**Created**: 2024-12-02
**Status**: Draft
**Input**: User description: "isolate those human-readable mappings (outdoor temp, DHW, ...) to a config outside of the tui, so it can also be used in both feature 006 and 008. make sure you provide a config mechanism for configuring specifics of the installation"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load Sensor Mappings from Configuration (Priority: P1)

As a system component (TUI, CLI, or library), I need to load CAN broadcast-to-sensor mappings from a central configuration so that temperature readings are correctly identified regardless of which tool is accessing them.

**Why this priority**: Without correct sensor mappings, all temperature readings display incorrect values. This is the foundational capability that enables accurate monitoring across all system components.

**Independent Test**: Can be fully tested by loading the configuration file and verifying that CAN broadcast addresses map to the expected sensor names (outdoor, supply, return, dhw, brine_in).

**Acceptance Scenarios**:

1. **Given** a configuration file exists with sensor mappings, **When** the library loads the configuration, **Then** it returns a mapping from (base, idx) tuples to sensor names
2. **Given** the configuration file is missing, **When** the library attempts to load it, **Then** it uses built-in default mappings and logs a warning
3. **Given** the TUI starts up, **When** it reads broadcast temperatures, **Then** it uses the sensor mappings from the shared configuration
4. **Given** the CLI reads temperatures, **When** it displays values, **Then** it uses the same sensor mappings as the TUI

---

### User Story 2 - Configure Installation-Specific Circuit Layout (Priority: P2)

As a system administrator, I want to define which heating circuits exist in my installation, their types (ventilo vs floor heating), and which apartments they serve, so that the system displays meaningful labels and can filter data by apartment.

**Why this priority**: Different installations have different circuit configurations. Without this, the system cannot provide user-friendly labels or apartment-based views.

**Independent Test**: Can be fully tested by loading a configuration file with circuit definitions and verifying that circuit metadata (type, apartment, label) is accessible via the library.

**Acceptance Scenarios**:

1. **Given** a configuration defines Circuit 1 as "Ventilo" serving "Apartment 0", **When** the system queries circuit metadata, **Then** it returns type="ventilo" and apartment="Apartment 0"
2. **Given** a configuration defines 4 circuits with different apartments, **When** the system lists circuits by apartment, **Then** it correctly groups circuits by their assigned apartment
3. **Given** no installation configuration exists, **When** the system queries circuit metadata, **Then** it returns generic defaults (Circuit 1-4, type=unknown)

---

### User Story 3 - Configure DHW Distribution (Priority: P2)

As a system administrator, I want to specify which apartments receive domestic hot water (DHW), so that the system can show relevant DHW information only to applicable apartments.

**Why this priority**: Not all apartments in a multi-unit installation receive DHW. Showing irrelevant DHW data clutters the interface and confuses users.

**Independent Test**: Can be fully tested by loading a configuration with DHW settings and verifying that apartment DHW availability is correctly reported.

**Acceptance Scenarios**:

1. **Given** configuration specifies DHW serves only Apartment 0, **When** querying DHW availability for Apartment 0, **Then** returns true
2. **Given** configuration specifies DHW serves only Apartment 0, **When** querying DHW availability for Apartment 1, **Then** returns false
3. **Given** no DHW configuration exists, **When** querying DHW availability, **Then** assumes all apartments have DHW access (safe default)

---

### User Story 4 - Custom Sensor Labels (Priority: P3)

As a system administrator, I want to optionally provide custom human-readable labels for sensors (e.g., "Living Room Temperature" instead of "GT2"), so that displays are more meaningful to end users.

**Why this priority**: Custom labels improve usability but are not essential for core functionality. Default sensor names (outdoor, supply, etc.) work adequately.

**Independent Test**: Can be fully tested by adding custom labels to configuration and verifying they override default sensor names in display output.

**Acceptance Scenarios**:

1. **Given** configuration defines a custom label "Outside Air" for the outdoor sensor, **When** the TUI displays outdoor temperature, **Then** it shows "Outside Air" as the label
2. **Given** no custom label is defined for a sensor, **When** displaying that sensor, **Then** it uses the default label (e.g., "Outdoor Temperature")

---

### Edge Cases

- What happens when configuration file has invalid syntax?
  - System logs error, falls back to default configuration
- What happens when a configured sensor mapping references an unknown sensor name?
  - System ignores the invalid mapping, logs a warning
- What happens when circuit numbers in config exceed available circuits (1-4)?
  - System ignores out-of-range circuits, logs a warning
- What happens when multiple CAN addresses map to the same sensor?
  - System uses the first value received (existing behavior, multiple sources allowed)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a configuration loader that reads sensor mappings from a file
- **FR-002**: System MUST support mapping CAN broadcast addresses (base, idx) to sensor names
- **FR-003**: System MUST support these core sensors: outdoor, supply, return_temp, dhw, brine_in
- **FR-004**: System MUST support installation-specific circuit definitions including circuit number, type, and apartment assignment
- **FR-005**: System MUST support DHW distribution configuration specifying which apartments receive hot water
- **FR-006**: System MUST provide default values when configuration is missing or incomplete
- **FR-007**: System MUST log warnings when using fallback defaults
- **FR-008**: Configuration MUST be loadable by both the core library and CLI/TUI components
- **FR-009**: System SHOULD support custom human-readable labels for sensors
- **FR-010**: System MUST validate configuration on load and report errors gracefully

### Key Entities

- **SensorMapping**: Represents a CAN broadcast address (base, idx) mapped to a sensor name
- **CircuitConfig**: Represents a heating circuit with its number (1-4), type (ventilo/floor_heating/unknown), apartment assignment, and optional custom label
- **InstallationConfig**: The complete installation configuration containing sensor mappings, circuit definitions, and DHW settings
- **Apartment**: A logical grouping representing a dwelling unit, referenced by circuits and DHW configuration

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: TUI and CLI display identical temperature readings when using the same configuration
- **SC-002**: Configuration changes take effect without code modifications
- **SC-003**: System starts successfully with default values when no configuration file exists
- **SC-004**: Invalid configuration entries are logged but do not crash the application
- **SC-005**: All 5 core sensors (outdoor, supply, return, dhw, brine_in) can be configured via the configuration file

## Assumptions

- Configuration file format will be determined during planning (YAML, TOML, or JSON are candidates)
- Configuration file will be located in a standard location within the project or user's home directory
- The existing hardcoded mappings in app.py serve as the initial default values
- Circuit numbers are fixed at 1-4 as per the heat pump's hardware design
- Apartment identifiers are user-defined strings (e.g., "Apartment 0", "Ground Floor", etc.)
