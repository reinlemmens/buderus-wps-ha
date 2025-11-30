# Feature Specification: Terminal Menu UI

**Feature Branch**: `008-terminal-menu-ui`
**Created**: 2025-11-28
**Status**: Draft
**Input**: User description: "create a linux terminal application with menus that exposes the menus developed in feature 007"
**Depends On**: Feature 007 (Heat Pump Menu API)

## Overview

A terminal-based application that provides an interactive menu interface to control and monitor the Buderus WPS heat pump. The interface mirrors the physical display's menu structure, making it intuitive for users familiar with the device while enabling remote access via SSH.

## Clarifications

### Session 2025-11-30

- Q: Should dashboard auto-refresh or manual refresh only? → A: Manual refresh only (press 'r' to update values)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View System Status Dashboard (Priority: P1)

As a homeowner, I want to see a dashboard showing current temperatures and system status so I can quickly understand my heating system's state without navigating through menus.

**Why this priority**: This is the most common use case - users check status far more often than changing settings. It provides immediate value with read-only access.

**Independent Test**: Launch application, verify dashboard displays outdoor temp, supply temp, DHW temp, operating mode, and compressor status. Compare values to physical display.

**Acceptance Scenarios**:

1. **Given** the application is launched, **When** it connects to the heat pump, **Then** a status dashboard is displayed showing all key temperatures and operating status
2. **Given** the dashboard is displayed, **When** the user presses 'r' to refresh, **Then** the dashboard updates with current values within 5 seconds
3. **Given** the heat pump is unreachable, **When** the application is launched, **Then** a clear error message is displayed with troubleshooting hints

---

### User Story 2 - Navigate Menu Structure (Priority: P1)

As a homeowner, I want to navigate through menus using arrow keys so I can explore settings just like on the physical display.

**Why this priority**: Core functionality - without navigation, users cannot access any settings.

**Independent Test**: Use arrow keys to navigate from main menu to Hot Water > Temperature, verify correct items are highlighted and selected.

**Acceptance Scenarios**:

1. **Given** the main menu is displayed, **When** I press Up/Down arrows, **Then** menu items are highlighted sequentially
2. **Given** a menu item is highlighted, **When** I press Enter, **Then** I navigate into that submenu or see the current value
3. **Given** I am in a submenu, **When** I press Escape or Backspace, **Then** I return to the parent menu
4. **Given** I am navigating, **When** the current path is displayed, **Then** I can see breadcrumbs showing my location (e.g., "Hot Water > Temperature")

---

### User Story 3 - Adjust Hot Water Temperature (Priority: P2)

As a homeowner, I want to adjust the DHW temperature setpoint so I can control hot water heating.

**Why this priority**: Most frequently modified setting after viewing status.

**Independent Test**: Navigate to Hot Water > Temperature, change value from current to new value within 20-65 range, verify change persists on heat pump.

**Acceptance Scenarios**:

1. **Given** I am at the Temperature setting, **When** I press Enter to edit, **Then** I enter edit mode with current value displayed
2. **Given** I am in edit mode, **When** I type a new value within 20-65, **Then** the value is accepted
3. **Given** I am in edit mode, **When** I type a value outside 20-65, **Then** an error is shown and the value is rejected
4. **Given** I have entered a valid value, **When** I press Enter to confirm, **Then** the new value is written to the heat pump

---

### User Story 4 - View and Edit Weekly Schedules (Priority: P2)

As a homeowner, I want to view and modify DHW weekly schedules so I can optimize heating times.

**Why this priority**: Schedule management is a key feature for energy optimization.

**Independent Test**: Navigate to Programs > DHW Program 1, view Monday schedule, modify start/end times, verify change on heat pump.

**Acceptance Scenarios**:

1. **Given** I navigate to a schedule, **When** it is displayed, **Then** I see all 7 days with their start and end times
2. **Given** I am viewing a schedule, **When** I select a day, **Then** I can edit the start and end times
3. **Given** I enter schedule times, **When** times are not on 30-minute boundaries, **Then** an error is shown
4. **Given** I save a schedule change, **When** the write completes, **Then** a confirmation message is displayed

---

### User Story 5 - Monitor Energy Statistics (Priority: P3)

As a homeowner, I want to view energy consumption statistics so I can monitor efficiency.

**Why this priority**: Useful for monitoring but less frequently accessed than settings.

**Independent Test**: Navigate to Energy menu, verify heat generated and aux heater kWh values are displayed.

**Acceptance Scenarios**:

1. **Given** I navigate to Energy menu, **When** it is displayed, **Then** I see heat generated and auxiliary heater consumption
2. **Given** energy values are displayed, **When** I refresh, **Then** values update from the heat pump

---

### User Story 6 - View Active Alarms (Priority: P3)

As a homeowner, I want to see active alarms and alarm history so I can respond to issues.

**Why this priority**: Important for troubleshooting but not accessed frequently.

**Independent Test**: Navigate to Alarms menu, view active alarms list, verify alarm codes and timestamps.

**Acceptance Scenarios**:

1. **Given** I navigate to Alarms, **When** there are active alarms, **Then** they are listed with code, description, and timestamp
2. **Given** I navigate to Alarms, **When** there are no active alarms, **Then** a "No active alarms" message is displayed
3. **Given** I select an alarm, **When** I choose to acknowledge it, **Then** the acknowledge command is sent to the heat pump

---

### User Story 7 - Configure Vacation Mode (Priority: P3)

As a homeowner, I want to set vacation mode so the system reduces heating while I'm away.

**Why this priority**: Occasional use case for energy savings during vacations.

**Independent Test**: Navigate to Vacation, set start/end dates for a circuit, verify vacation mode is active on heat pump.

**Acceptance Scenarios**:

1. **Given** I navigate to Vacation, **When** I select a circuit, **Then** I see current vacation status (active/inactive with dates if set)
2. **Given** I am setting vacation, **When** I enter start and end dates, **Then** dates are validated (end after start, not in past)
3. **Given** vacation is active, **When** I choose to clear it, **Then** vacation mode is deactivated

---

### Edge Cases

- What happens when connection to heat pump is lost mid-operation?
  - Display error message, offer retry option, prevent data corruption
- What happens when user enters invalid input (non-numeric for temperature)?
  - Reject input immediately, show error, keep cursor in edit field
- How does the application handle terminal resize?
  - Redraw interface to fit new dimensions
- What happens if user presses Ctrl+C?
  - Graceful shutdown, disconnect from heat pump cleanly

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Application MUST connect to heat pump via USB serial adapter
- **FR-002**: Application MUST display a status dashboard on startup showing temperatures and operating mode
- **FR-003**: Application MUST provide keyboard-based menu navigation (arrow keys, Enter, Escape)
- **FR-004**: Application MUST display breadcrumb path showing current menu location
- **FR-005**: Application MUST allow editing of writable parameters with value validation
- **FR-006**: Application MUST display validation errors when input is rejected
- **FR-007**: Application MUST show confirmation when values are written successfully
- **FR-008**: Application MUST handle connection errors gracefully with user-friendly messages
- **FR-009**: Application MUST allow users to refresh status data manually (press 'r'); no automatic polling
- **FR-010**: Application MUST provide help text for navigation (shown at bottom of screen)
- **FR-011**: Application MUST exit cleanly when user presses 'q' or Ctrl+C
- **FR-012**: Application MUST display schedules in a readable weekly format
- **FR-013**: Application MUST validate schedule times are on 30-minute boundaries before writing

### Key Entities

- **Menu Item**: A node in the menu hierarchy with name, description, optional parameter reference, and children
- **Parameter Value**: A readable or writable setting with current value, valid range, and units
- **Schedule**: Weekly time slots with start/end times for each day
- **Alarm**: Active or historical alarm with code, description, timestamp, and status

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view current status within 3 seconds of launching the application
- **SC-002**: Users can navigate to any menu item within 5 key presses from the main menu
- **SC-003**: Users can modify a temperature setting in under 30 seconds (navigate + edit + confirm)
- **SC-004**: Application displays clear error messages for all failure scenarios (connection, validation, timeout)
- **SC-005**: Application runs reliably over SSH connections without display artifacts
- **SC-006**: 100% of Menu API features from feature 007 are accessible through the terminal interface

## Assumptions

- Application runs on Linux/macOS terminal (POSIX-compatible)
- Terminal supports ANSI escape codes for colors and cursor positioning
- USB serial adapter is connected and accessible at a known device path
- User has terminal access (local or via SSH)
- Feature 007 Menu API is complete and functional
