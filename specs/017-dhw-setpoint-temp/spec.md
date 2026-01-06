# Feature Specification: DHW Setpoint Temperature Parameter

**Feature Branch**: `017-dhw-setpoint-temp`
**Created**: 2026-01-04
**Status**: Implemented
**Input**: User description: "add DHW_CALCULATED_SETPOINT_TEMP → 'DHW Setpoint Temperature' as a parameter in library, cli and HA integration"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Current DHW Setpoint in Home Assistant (Priority: P1)

A homeowner wants to see the current hot water target temperature displayed in their Home Assistant dashboard so they can monitor their heat pump settings without physically accessing the unit.

**Why this priority**: This is the most common use case - users need visibility into their current DHW setpoint before they can decide whether to change it. Read-only visibility is the foundation for all other functionality.

**Independent Test**: Can be fully tested by connecting to a heat pump and verifying the temperature value appears in HA and matches the physical unit display.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** the user views the DHW Setpoint Temperature entity in Home Assistant, **Then** they see the current setpoint value displayed in degrees Celsius
2. **Given** the heat pump has DHW setpoint set to 55°C, **When** the HA entity refreshes, **Then** the displayed value shows 55.0°C
3. **Given** the heat pump connection is lost, **When** the user views the entity, **Then** the last known value is displayed with a stale indicator

---

### User Story 2 - Adjust DHW Setpoint from Home Assistant (Priority: P1)

A homeowner wants to adjust their hot water target temperature from Home Assistant so they can optimize energy usage without leaving their couch or being at home.

**Why this priority**: The primary value proposition - remote control of DHW temperature. Equal priority to viewing since both are essential for a complete feature.

**Independent Test**: Can be fully tested by changing the value in HA and verifying the heat pump accepts the new setpoint.

**Acceptance Scenarios**:

1. **Given** a connected heat pump with DHW setpoint at 55°C, **When** the user sets the value to 50°C via HA, **Then** the heat pump accepts the new setpoint and the entity reflects 50°C
2. **Given** a user attempts to set a value below 40°C, **When** they submit the change, **Then** the system rejects it with a clear error message
3. **Given** a user attempts to set a value above 70°C, **When** they submit the change, **Then** the system rejects it with a clear error message
4. **Given** the heat pump is temporarily unreachable, **When** the user attempts to change the setpoint, **Then** they receive feedback that the change could not be applied

---

### User Story 3 - Read/Write DHW Setpoint via CLI (Priority: P2)

A developer or advanced user wants to read and write the DHW setpoint via the command-line interface for scripting, debugging, or automation purposes.

**Why this priority**: CLI access is important for developers and power users but secondary to the HA integration which serves the majority of users.

**Independent Test**: Can be fully tested by running CLI commands and verifying read/write operations work correctly.

**Acceptance Scenarios**:

1. **Given** CLI access to the heat pump, **When** the user runs a read command for DHW setpoint, **Then** the current value is displayed
2. **Given** CLI access to the heat pump, **When** the user runs a write command with value 52°C, **Then** the setpoint is updated and confirmed

---

### User Story 4 - Use DHW Setpoint in Automations (Priority: P2)

A homeowner wants to include the DHW setpoint in Home Assistant automations so they can automatically adjust hot water temperature based on conditions like time of day, occupancy, or electricity prices.

**Why this priority**: Automation capability unlocks significant energy savings but depends on the basic read/write functionality being in place first.

**Independent Test**: Can be fully tested by creating an automation that changes the setpoint and verifying it executes correctly.

**Acceptance Scenarios**:

1. **Given** an automation that sets DHW to 45°C at night, **When** the automation triggers, **Then** the heat pump setpoint changes to 45°C
2. **Given** an automation that reads current DHW setpoint, **When** the automation runs, **Then** it can use the value in conditions and actions

---

### Edge Cases

- What happens when the heat pump reports a value outside the expected 40-70°C range?
- How does the system handle concurrent write attempts from multiple sources (HA, physical unit, CLI)?
- What happens if the parameter index differs between heat pump firmware versions?
- How does the system behave when DHW is disabled or blocked?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read the DHW setpoint temperature from the heat pump using the `DHW_CALCULATED_SETPOINT_TEMP` parameter
- **FR-002**: System MUST display the DHW setpoint as a number entity in Home Assistant with unit °C
- **FR-003**: System MUST allow users to write new DHW setpoint values within the valid range (40.0°C to 70.0°C)
- **FR-004**: System MUST validate input values before sending to the heat pump and reject out-of-range values with user-friendly error messages
- **FR-005**: System MUST expose the parameter via CLI for read and write operations
- **FR-006**: System MUST update the displayed value when the heat pump reports a change
- **FR-007**: System MUST handle communication failures gracefully, displaying last known value when fresh data is unavailable
- **FR-008**: System MUST support the parameter in the core library for use by both CLI and HA integration

### Key Entities

- **DHW Setpoint Temperature**: The target temperature at which the heat pump maintains the domestic hot water tank during normal operation. Range: 40.0°C to 70.0°C. This is distinct from the "extra DHW" temperature used during boost mode.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view the current DHW setpoint in Home Assistant within 30 seconds of page load
- **SC-002**: Users can change the DHW setpoint from Home Assistant and see the change reflected within 10 seconds
- **SC-003**: 100% of write attempts with valid values (40-70°C) are accepted by the heat pump
- **SC-004**: 100% of write attempts with invalid values are rejected with clear error messages before being sent to the heat pump
- **SC-005**: CLI read/write commands complete successfully within 5 seconds under normal conditions

## Assumptions

- The `DHW_CALCULATED_SETPOINT_TEMP` parameter (idx 385) is available on the user's heat pump model
- The parameter range of 40-70°C is consistent across supported heat pump models
- The existing coordinator refresh mechanism will pick up changes made via the physical unit
- The parameter uses the standard "tem" format (value / 10 = temperature in °C)

## Dependencies

- Existing `BuderusCoordinator` for data refresh and write operations
- Existing `number.py` entity pattern (similar to `BuderusDHWStopTempNumber`)
- Existing CLI infrastructure for parameter read/write
- Parameter must be defined in `parameter_defaults.py` (already present)

## Out of Scope

- Comfort/Economy mode-specific DHW temperatures (separate parameters)
- DHW scheduling or time programs
- Integration with external energy price APIs for automatic optimization
- Multi-zone DHW configurations
