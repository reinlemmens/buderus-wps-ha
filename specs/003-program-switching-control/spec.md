# Feature Specification: Program-Based Switching Control for Heat Pump Functions

**Feature Branch**: `003-program-switching-control`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "for most features, like enabling hot water of enabling heating the buffer tank, we will be using switching between programs DHW_PROGRAM1 as selected program (DHW_PROGRAM_MODE) where we will be having program1 as an always-off programm and program2 as an always-on programm"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enable/Disable Hot Water on Demand (Priority: P1)

A homeowner needs to quickly enable or disable domestic hot water (DHW) production, for example to save energy during vacation or to force hot water production before guests arrive.

**Why this priority**: Core functionality that provides immediate user value - most common use case for manual heat pump control.

**Independent Test**: Can be fully tested by toggling DHW between on and off states and verifying that the heat pump responds by switching between the configured programs (program1 for off, program2 for on).

**Acceptance Scenarios**:

1. **Given** DHW is currently disabled (using program1), **When** the user enables DHW, **Then** the system switches to program2 (always-on) and hot water production begins
2. **Given** DHW is currently enabled (using program2), **When** the user disables DHW, **Then** the system switches to program1 (always-off) and hot water production stops
3. **Given** the user enables DHW, **When** they check the current program mode, **Then** the system shows program2 is active
4. **Given** the user disables DHW, **When** they check the current program mode, **Then** the system shows program1 is active

---

### User Story 2 - Enable/Disable Buffer Tank Heating (Priority: P2)

A homeowner with a buffer tank system wants to control when the tank is heated, allowing them to optimize energy usage based on electricity prices or heating needs.

**Why this priority**: Important for energy management and cost optimization - builds on the program-switching pattern established in P1.

**Independent Test**: Can be fully tested by toggling buffer tank heating between on and off states and verifying that the system switches between the configured heating programs independently of DHW control.

**Acceptance Scenarios**:

1. **Given** buffer tank heating is currently disabled, **When** the user enables buffer tank heating, **Then** the system switches to the always-on heating program and begins heating the tank
2. **Given** buffer tank heating is currently enabled, **When** the user disables buffer tank heating, **Then** the system switches to the always-off heating program and stops heating the tank
3. **Given** DHW is enabled and buffer heating is disabled, **When** the user enables buffer heating, **Then** both systems operate independently according to their respective program settings
4. **Given** the user changes buffer tank heating state, **When** they check the system status, **Then** the heating program mode reflects the current on/off state

---

### User Story 3 - Query Current System State (Priority: P3)

A user wants to check whether hot water or buffer tank heating is currently enabled without needing to remember the previous state they set.

**Why this priority**: Enhances usability by providing status visibility - users can verify system state before making changes.

**Independent Test**: Can be fully tested by setting various combinations of DHW and buffer heating states, then querying the system and verifying that reported states match the configured program modes.

**Acceptance Scenarios**:

1. **Given** DHW is enabled (program2), **When** the user queries DHW status, **Then** the system reports DHW is enabled
2. **Given** DHW is disabled (program1), **When** the user queries DHW status, **Then** the system reports DHW is disabled
3. **Given** both DHW and buffer heating are enabled, **When** the user queries system status, **Then** the system reports both functions are enabled
4. **Given** DHW is enabled and buffer heating is disabled, **When** the user queries system status, **Then** the system accurately reports the independent state of each function

---

### Edge Cases

- What happens when attempting to switch programs while the heat pump is in an active heating cycle?
- How does the system handle rapid toggling between on and off states (e.g., enabling and disabling within seconds)?
- What happens if the heat pump does not support the specified program numbers (program1, program2)?
- How does the system behave if communication with the heat pump is interrupted during a program switch?
- What happens when trying to enable a function that is already enabled (or disable one that is already disabled)?
- How are conflicting program switches handled if multiple functions try to change programs simultaneously?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support enabling and disabling domestic hot water (DHW) production by switching between program modes
- **FR-002**: The system MUST support enabling and disabling buffer tank heating by switching between program modes
- **FR-003**: The system MUST use program1 as the "always-off" program configuration for any controlled function
- **FR-004**: The system MUST use program2 as the "always-on" program configuration for any controlled function
- **FR-005**: The system MUST allow independent control of DHW and buffer tank heating - changing one MUST NOT affect the other
- **FR-006**: The system MUST provide a way to query the current state (enabled/disabled) of DHW production
- **FR-007**: The system MUST provide a way to query the current state (enabled/disabled) of buffer tank heating
- **FR-008**: The system MUST switch to the target program mode when a user enables or disables a function
- **FR-009**: The system MUST confirm successful program switching or report errors if the switch fails
- **FR-010**: The system MUST handle idempotent operations (enabling an already-enabled function should succeed without error)

### Key Entities

- **DHW Program Mode**: Controls domestic hot water production, with values indicating which program (1 or 2) is currently active
- **Heating Program Mode**: Controls buffer tank heating, with values indicating which program (1 or 2) is currently active
- **Program Configuration**: Defines behavior for program1 (always-off) and program2 (always-on), containing schedule and temperature settings
- **Function State**: Represents whether a specific function (DHW or buffer heating) is currently enabled or disabled based on its active program
- **Control Command**: A request to change a function's state, resulting in a program mode switch

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can enable or disable DHW production in under 5 seconds from issuing the command
- **SC-002**: Users can enable or disable buffer tank heating in under 5 seconds from issuing the command
- **SC-003**: System state queries return accurate results 100% of the time, correctly reflecting the currently active program
- **SC-004**: Program switches complete successfully 99% of the time under normal operating conditions
- **SC-005**: Users can independently control DHW and buffer heating without unintended cross-function effects

## Assumptions

- The heat pump supports at least two configurable programs (program1 and program2) for DHW and heating modes
- Program1 can be configured as an "always-off" schedule (e.g., no active time periods)
- Program2 can be configured as an "always-on" schedule (e.g., all time periods active)
- Program configurations are set up in advance and remain stable (not modified during operation)
- The DHW_PROGRAM_MODE parameter controls which DHW program is active
- Similar program mode parameters exist for buffer tank heating control
- Users have appropriate permissions to change program modes on the heat pump
- The heat pump responds to program mode changes within a reasonable time (under 5 seconds)
- Program switching does not require physical access to the heat pump unit

## Dependencies

- Access to the heat pump's program mode parameters (e.g., DHW_PROGRAM_MODE)
- Pre-configured program1 and program2 settings on the heat pump
- Communication channel to read and write program mode parameters on the heat pump
- Python class from feature 002 (buderus-wps-python-class) for parameter definitions and access

## Out of Scope

- Creating or modifying the actual program schedules and temperature settings (program1 and program2 must be pre-configured)
- Advanced scheduling features beyond simple on/off control
- Integration with external systems for automatic control based on energy prices or other factors
- Historical logging of program switches or state changes
- User interface for displaying or controlling the functions (specification focuses on the control mechanism)
- Support for more than two programs (only program1 and program2 are used)
- Control of other heat pump functions beyond DHW and buffer tank heating
- Handling of heat pump maintenance modes or error states
- Optimization of heating cycles or energy usage
