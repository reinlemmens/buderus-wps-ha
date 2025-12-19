# Feature Specification: Heat Pump Menu API

**Feature Branch**: `007-heatpump-menu-api`
**Created**: 2025-11-28
**Status**: Draft
**Input**: User description: "Create a Python API that sits on top of feature 002 and mimics the workings of the menus on the heat pump as described in the manuals."

## Clarifications

### Session 2025-11-28

- Q: Should the API support acknowledging/clearing alarms, or is it read-only for alarm data? → A: Full control - API can read alarms AND acknowledge/clear them programmatically.
- Q: Should vacation mode configuration be included in this API's scope? → A: In scope - include vacation mode read/write for circuits and DHW.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read Current System Status (Priority: P1)

A home automation integrator wants to read the current status and temperatures from the heat pump to display on a dashboard, without needing to know the underlying CAN protocol or parameter names.

**Why this priority**: Reading status is the most fundamental operation and enables monitoring without any risk of misconfiguration. This is the foundation for all other features.

**Independent Test**: Can be fully tested by calling the API to read temperatures and status values, verifying they match what's displayed on the physical heat pump panel.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** requesting the standard display values, **Then** receive outdoor temperature, supply temperature, hot water temperature, and room temperature in human-readable format with units.
2. **Given** a connected heat pump, **When** requesting operational status, **Then** receive current operating mode (heating/cooling/DHW/standby) and compressor state.
3. **Given** a connected heat pump, **When** requesting circuit-specific temperatures, **Then** receive temperatures for all active circuits (1-4).

---

### User Story 2 - Navigate Menu Structure (Priority: P1)

A developer wants to explore what settings are available on the heat pump by navigating through the menu hierarchy programmatically, similar to using the physical menu button and dial.

**Why this priority**: Understanding the available menu structure is essential before modifying any settings. This mirrors the physical user experience.

**Independent Test**: Can be fully tested by listing menu items and comparing against the documented menu structure in the user manual.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** requesting the top-level menu, **Then** receive a list of menu categories matching the physical menu (Program Mode, Programs, Compressor, Hot Water, etc.).
2. **Given** a top-level menu category, **When** drilling down into a submenu, **Then** receive the child items with their current values and valid ranges.
3. **Given** any menu item, **When** requesting help information, **Then** receive a description of what the setting does.

---

### User Story 3 - Read and Modify Hot Water Settings (Priority: P2)

A homeowner wants to check and adjust their hot water temperature settings and extra hot water duration through a home automation system.

**Why this priority**: Hot water control is a frequent user need and relatively safe to modify within the allowed ranges.

**Independent Test**: Can be fully tested by reading current DHW settings, modifying temperature within allowed range, and verifying the change persists.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** reading hot water settings, **Then** receive current temperature setpoint, extra hot water duration, and stop temperature.
2. **Given** a new hot water temperature value within the allowed range (20-65 degrees), **When** setting the temperature, **Then** the value is written and can be verified by re-reading.
3. **Given** a temperature value outside the allowed range, **When** attempting to set it, **Then** receive a validation error with the allowed range before any CAN message is sent.

---

### User Story 4 - Read and Modify Weekly Schedules (Priority: P2)

A homeowner wants to view and adjust the weekly heating and hot water schedules to match their family's routine.

**Why this priority**: Schedule control is a key automation use case, allowing energy savings and comfort optimization.

**Independent Test**: Can be fully tested by reading current schedules, modifying a time slot, and verifying the change.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** reading the DHW weekly schedule for Program 1, **Then** receive start and end times for each day of the week in HH:MM format.
2. **Given** a connected heat pump, **When** reading room program schedules, **Then** receive start and end times for each day for each active circuit.
3. **Given** new schedule times (in 30-minute increments for DHW, variable for room), **When** setting a day's schedule, **Then** the times are encoded correctly and written.
4. **Given** an invalid time (not on 30-minute boundary for DHW), **When** attempting to set, **Then** receive a validation error explaining the constraint.

---

### User Story 5 - Control Operating Modes (Priority: P2)

A homeowner wants to switch between program modes (HP Optimized, Program 1, Program 2, Family, etc.) or set summer/winter mode through automation.

**Why this priority**: Mode switching is a common automation task for seasonal adjustments and vacation settings.

**Independent Test**: Can be fully tested by reading current mode, switching to a different mode, and verifying the switch.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** reading the current program mode for a circuit, **Then** receive the mode name (HP_Optimized, Program_1, Program_2, Family, Morning, Evening, Seniors).
2. **Given** a valid mode name, **When** setting the program mode, **Then** the mode changes and can be verified.
3. **Given** a connected heat pump, **When** reading summer/winter mode status, **Then** receive current mode and switchover temperature threshold.

---

### User Story 6 - Read Energy Statistics (Priority: P3)

A homeowner wants to monitor energy consumption and heat production to track efficiency over time.

**Why this priority**: Energy monitoring is valuable for long-term optimization but not critical for basic operation.

**Independent Test**: Can be fully tested by reading energy values and comparing against the energy menu on the physical display.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** reading energy statistics, **Then** receive generated heat energy and auxiliary heater electricity consumption.
2. **Given** historical energy data exists, **When** reading energy values, **Then** receive values in standard units (kWh).

---

### User Story 7 - Read and Acknowledge Alarms (Priority: P3)

A homeowner wants to be notified of and acknowledge alarms/warnings through their home automation system.

**Why this priority**: Alarm handling improves system reliability but is less frequently used than temperature/schedule control.

**Independent Test**: Can be fully tested by reading alarm log, checking for active alarms, and verifying alarm status.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** reading the alarm log, **Then** receive a list of alarm events with timestamps and descriptions.
2. **Given** an active alarm, **When** reading alarm status, **Then** receive alarm category, description, and acknowledgment status.
3. **Given** a connected heat pump, **When** reading the information log, **Then** receive operational events and warnings.
4. **Given** an unacknowledged alarm, **When** acknowledging the alarm via the API, **Then** the alarm status changes to acknowledged and can be verified.
5. **Given** a clearable alarm condition that has been resolved, **When** clearing the alarm via the API, **Then** the alarm is removed from the active alarm list.

---

### User Story 8 - Multi-Circuit Configuration (Priority: P3)

An installer wants to read and configure settings for multiple heating circuits (unmixed circuit 1, mixed circuits 2-4).

**Why this priority**: Multi-circuit configuration is important for complex installations but many users have single-circuit systems.

**Independent Test**: Can be fully tested by reading settings for each active circuit and verifying circuit-specific parameters.

**Acceptance Scenarios**:

1. **Given** a heat pump with 4 active circuits, **When** listing available circuits, **Then** receive circuit identifiers and types (unmixed/mixed).
2. **Given** a specific circuit number, **When** reading circuit settings, **Then** receive that circuit's temperatures, program mode, and schedule.
3. **Given** different circuits, **When** reading their schedules independently, **Then** receive circuit-specific schedule data.

---

### User Story 9 - Vacation Mode Configuration (Priority: P2)

A homeowner wants to configure vacation mode before leaving for holiday to reduce heating and pause DHW production, then restore normal operation upon return.

**Why this priority**: Vacation mode is a key energy-saving feature and common automation use case for smart home integration.

**Independent Test**: Can be fully tested by setting vacation dates, verifying reduced operation, and clearing vacation mode.

**Acceptance Scenarios**:

1. **Given** a connected heat pump, **When** reading vacation settings, **Then** receive current vacation mode status (active/inactive) and configured dates for each circuit and DHW.
2. **Given** vacation start and end dates, **When** setting vacation mode for circuit 1 and DHW, **Then** the vacation period is configured and can be verified.
3. **Given** an active vacation mode, **When** clearing vacation mode, **Then** normal operation resumes immediately.
4. **Given** vacation mode is active, **When** reading circuit status, **Then** the API indicates the circuit is in vacation mode with reduced setpoint.

---

### Edge Cases

- What happens when the heat pump is not responding (timeout)? The API returns a timeout error with diagnostic information.
- How does the system handle reading parameters that don't exist on this heat pump model? Returns a "parameter not available" error.
- What happens when attempting to write to a read-only parameter? Returns a permission error before sending any CAN message.
- How are communication errors during a write operation handled? Returns error with context; no automatic retry (per project constitution).
- What happens when the physical menu is being used simultaneously? CAN protocol allows concurrent access; API operations proceed normally.
- How are temperature values outside sensor range (-40 to +100 degrees) handled? Values are returned as-is; interpretation is caller's responsibility.

## Requirements *(mandatory)*

### Functional Requirements

**Menu Navigation:**
- **FR-001**: System MUST provide a hierarchical menu structure matching the physical heat pump display menus.
- **FR-002**: System MUST support listing menu items at any level with their current values.
- **FR-003**: System MUST indicate which menu items are read-only vs. writable.

**Status Reading:**
- **FR-004**: System MUST provide methods to read standard display values (outdoor temp, supply temp, DHW temp, room temp).
- **FR-005**: System MUST provide current operating state (heating, cooling, DHW priority, standby).
- **FR-006**: System MUST provide compressor status and run times.

**Hot Water Control:**
- **FR-007**: System MUST support reading and writing DHW temperature setpoint (20-65 degree range).
- **FR-008**: System MUST support reading and writing extra hot water duration and stop temperature.
- **FR-009**: System MUST support reading and writing DHW weekly schedules (Programs 1 and 2).

**Schedule Management:**
- **FR-010**: System MUST decode schedule times from the heat pump's internal encoding to human-readable HH:MM format.
- **FR-011**: System MUST encode schedule times from HH:MM to the heat pump's internal format before writing.
- **FR-012**: System MUST support DHW schedules with 30-minute time resolution.
- **FR-013**: System MUST support room program schedules with appropriate time resolution.
- **FR-014**: System MUST read full schedule data (start AND end times) for DHW schedules, using the correct parameter indices.

**Program Modes:**
- **FR-015**: System MUST support reading and setting program modes (HP_Optimized, Program_1, Program_2, Family, Morning, Evening, Seniors).
- **FR-016**: System MUST support reading and setting DHW program mode (Always_On, Program_1, Program_2).
- **FR-017**: System MUST support reading and setting summer/winter mode and switchover temperature.

**Circuit Management:**
- **FR-018**: System MUST support operations on circuits 1-4 independently.
- **FR-019**: System MUST identify circuit type (unmixed/mixed) for each circuit.
- **FR-020**: System MUST allow reading circuit-specific temperatures and settings.

**Vacation Mode:**
- **FR-021**: System MUST support reading vacation mode status (active/inactive) for each circuit and DHW.
- **FR-022**: System MUST support setting vacation mode with start and end dates per circuit.
- **FR-023**: System MUST support clearing vacation mode to resume normal operation.

**Energy Statistics:**
- **FR-024**: System MUST provide access to generated heat energy readings.
- **FR-025**: System MUST provide access to auxiliary heater power consumption.

**Alarms and Logging:**
- **FR-026**: System MUST support reading alarm log entries.
- **FR-027**: System MUST support reading information log entries.
- **FR-028**: System MUST expose alarm category and status.
- **FR-029**: System MUST support acknowledging active alarms programmatically.
- **FR-030**: System MUST support clearing alarms whose underlying condition has been resolved.

**Validation and Safety:**
- **FR-031**: System MUST validate all values against min/max ranges before sending to heat pump.
- **FR-032**: System MUST validate time values against allowed increments (30-min for DHW).
- **FR-033**: System MUST prevent writes to read-only parameters.
- **FR-034**: System MUST provide meaningful error messages including allowed ranges.

**Architecture:**
- **FR-035**: System MUST build on top of existing HeatPumpClient from feature 002.
- **FR-036**: System MUST provide both low-level parameter access and high-level menu-style access.
- **FR-037**: System MUST use the same connection (USBtinAdapter) as the underlying client.

### Key Entities

- **Menu**: A hierarchical navigation structure with categories, items, and values. Mirrors the physical display menu.
- **Circuit**: A heating circuit (1=unmixed primary, 2-4=mixed with valve control). Each has independent temperature and schedule settings.
- **Schedule**: A weekly time program with start/end times for each day. DHW uses 30-minute slots, room programs use configurable slots.
- **Program Mode**: An operating mode selector (HP_Optimized, Program_1, etc.) that determines which schedule is active.
- **Temperature**: A temperature value with unit (degrees), valid range, and precision (typically 0.1 degrees).
- **Alarm**: An event with category (warning/alarm), timestamp, description, and acknowledgment status.
- **Vacation**: A temporary override period with start/end dates that reduces heating setpoints and optionally disables DHW.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can read all standard display values (4 temperatures + status) in a single operation within 2 seconds.
- **SC-002**: Users can navigate the complete menu hierarchy and read any setting within 5 seconds.
- **SC-003**: 100% of writable parameters can be modified through the API with proper validation.
- **SC-004**: Schedule read/write operations correctly handle both start and end times for all 7 days.
- **SC-005**: All validation errors include the specific constraint that was violated (range, increment, read-only).
- **SC-006**: API method names and structure align with menu labels in the user manual (e.g., "hot_water" not "dhw").
- **SC-007**: Users can perform common tasks (read temp, change setpoint, read schedule) without consulting protocol documentation.
- **SC-008**: 100% of menu items documented in the user manual (Table 3) are accessible through the API.

## Assumptions

- The heat pump is a Buderus WPS series (WPS 6-1 through WPS 17-1) with KM273 controller.
- The existing HeatPumpClient and ParameterRegistry from feature 002 are functional and tested.
- The USB serial connection (USBtinAdapter) is already established before using this API.
- Temperature values are stored in tenths of degrees (e.g., 550 = 55.0 degrees) as per the FHEM reference.
- DHW schedule parameters use the sw2 format with full schedule data (start+end) at odd indices (+1 from documented indices).
- Room schedule parameters use the sw1 format with 2-byte responses containing both times.
- The user manual menu structure is consistent across WPS models supported by feature 002.
- Circuits 2-4 are optional and may not be present on all installations.
