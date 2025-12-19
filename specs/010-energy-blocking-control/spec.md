# Feature Specification: Energy Blocking Control

**Feature Branch**: `010-energy-blocking-control`
**Created**: 2025-12-06
**Status**: Draft
**Input**: User description: "the system should have a feature that allows forbidding the heat pump to use energy on the compressor and on the auxiliary heater."

## Overview

This feature enables users to block the heat pump from using energy on high-consumption components: the compressor and the auxiliary (electric backup) heater. This is useful for:
- Demand response during peak electricity pricing periods
- Manual load shedding during high grid demand
- Protecting electrical circuits from overload
- Integration with smart grid or home energy management systems

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Block Compressor Operation (Priority: P1)

As a heat pump operator, I want to block the compressor from running so that I can prevent energy consumption during peak electricity rates or high grid demand periods.

**Why this priority**: The compressor is the primary energy consumer (typically 2-5 kW). Blocking it provides the most significant energy reduction and is the most common use case for demand response.

**Independent Test**: Can be fully tested by activating compressor block and verifying the compressor does not start when heating demand exists. Delivers immediate energy savings.

**Acceptance Scenarios**:

1. **Given** the system is connected to the heat pump and compressor is not blocked, **When** the user activates compressor blocking, **Then** the heat pump acknowledges the block and the compressor will not start regardless of heating demand.
2. **Given** compressor blocking is active and the compressor is currently running, **When** the block is activated, **Then** the compressor stops within the heat pump's safe shutdown period.
3. **Given** compressor blocking is active, **When** the user deactivates blocking, **Then** the compressor returns to normal automatic operation based on demand.
4. **Given** compressor blocking is active, **When** the user queries the status, **Then** the system clearly indicates compressor blocking is enabled.

---

### User Story 2 - Block Auxiliary Heater Operation (Priority: P2)

As a heat pump operator, I want to block the auxiliary electric heater from activating so that I can prevent additional energy consumption when the heat pump cannot meet demand alone.

**Why this priority**: The auxiliary heater is a secondary energy consumer (typically 3-9 kW) that activates during extreme conditions or defrost cycles. Blocking it provides supplementary energy control.

**Independent Test**: Can be fully tested by activating aux heater block during conditions that would normally trigger auxiliary heating. Delivers energy savings during peak demand periods.

**Acceptance Scenarios**:

1. **Given** the system is connected and aux heater is not blocked, **When** the user activates auxiliary heater blocking, **Then** the heat pump acknowledges the block and the aux heater will not activate.
2. **Given** aux heater blocking is active, **When** conditions would normally trigger aux heater (e.g., defrost, extreme cold), **Then** the aux heater remains off.
3. **Given** aux heater blocking is active, **When** the user deactivates blocking, **Then** the aux heater returns to normal automatic operation.
4. **Given** aux heater blocking is active, **When** the user queries the status, **Then** the system clearly indicates aux heater blocking is enabled.

---

### User Story 3 - View Energy Blocking Status (Priority: P3)

As a heat pump operator, I want to view the current status of all energy blocking settings so that I can understand what restrictions are currently in place.

**Why this priority**: Status visibility is essential for understanding current system state but is supplementary to the actual blocking functionality.

**Independent Test**: Can be tested by querying status after setting various blocking combinations. Delivers operational awareness.

**Acceptance Scenarios**:

1. **Given** no energy blocks are active, **When** the user views blocking status, **Then** the system shows both compressor and aux heater as "Normal" or "Not Blocked".
2. **Given** compressor blocking is active but aux heater is not blocked, **When** the user views status, **Then** the system shows compressor as "Blocked" and aux heater as "Normal".
3. **Given** both blocks are active, **When** the user views status, **Then** the system clearly shows both components as "Blocked".

---

### User Story 4 - Clear All Energy Blocks (Priority: P3)

As a heat pump operator, I want to quickly clear all energy blocking restrictions so that I can restore normal heat pump operation with a single action.

**Why this priority**: Convenience feature that reduces steps when exiting a demand response period.

**Independent Test**: Can be tested by activating both blocks, then clearing all, and verifying both components return to normal operation.

**Acceptance Scenarios**:

1. **Given** both compressor and aux heater blocking are active, **When** the user clears all blocks, **Then** both components return to normal automatic operation.
2. **Given** only one block is active, **When** the user clears all blocks, **Then** all blocking states are reset to normal.

---

### Edge Cases

- What happens when blocking is activated while the component is already running? (System should initiate safe shutdown)
- What happens when blocking is activated but communication with heat pump fails? (System should report error, not assume success)
- What happens when the heat pump is in a critical mode (e.g., anti-freeze protection)? (Heat pump may override external blocks for safety)
- What happens when blocking commands are sent rapidly in succession? (System should handle gracefully, last command wins)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to activate compressor blocking via command
- **FR-002**: System MUST allow users to deactivate compressor blocking via command
- **FR-003**: System MUST allow users to activate auxiliary heater blocking via command
- **FR-004**: System MUST allow users to deactivate auxiliary heater blocking via command
- **FR-005**: System MUST provide a command to view current blocking status for both components
- **FR-006**: System MUST provide a command to clear all blocking settings at once
- **FR-007**: System MUST confirm successful blocking activation/deactivation with the heat pump
- **FR-008**: System MUST report errors if blocking commands fail to communicate with the heat pump
- **FR-009**: System MUST read current blocking status from the heat pump (not just track local state)
- **FR-010**: System MUST support blocking operations via CLI commands
- **FR-011**: System SHOULD support blocking operations via TUI menu (if TUI available)

### Key Entities

- **Compressor Block State**: Whether compressor operation is blocked (enabled/disabled)
- **Auxiliary Heater Block State**: Whether auxiliary heater operation is blocked (enabled/disabled)
- **Blocking Command Result**: Success/failure status of blocking operations with error details if applicable

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can block compressor operation within 5 seconds of issuing command
- **SC-002**: User can block auxiliary heater operation within 5 seconds of issuing command
- **SC-003**: System correctly reads and displays blocking status from heat pump within 3 seconds
- **SC-004**: Clear-all operation resets both blocking states within 5 seconds
- **SC-005**: All blocking operations provide clear success/failure feedback to the user
- **SC-006**: System handles communication errors gracefully without leaving blocking state unknown

## Assumptions

- The Buderus WPS heat pump supports external blocking commands via CAN bus parameters
- Blocking parameters exist in the FHEM reference implementation (to be verified during planning)
- The heat pump has internal safety overrides that cannot be bypassed by external blocking (e.g., anti-freeze protection)
- Blocking state persists in the heat pump until explicitly cleared (survives system restarts)

## Out of Scope

- Scheduled/automated blocking based on time or electricity pricing (future enhancement)
- Integration with external smart grid APIs or demand response programs
- Partial power limiting (e.g., reducing compressor to 50% instead of full block)
