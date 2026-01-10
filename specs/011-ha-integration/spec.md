# Feature Specification: Home Assistant Integration

**Feature Branch**: `011-ha-integration`
**Created**: 2025-12-06
**Status**: Draft
**Input**: Home Assistant custom integration for Buderus WPS heat pump with temperature sensors, compressor status, energy blocking control, and DHW extra production

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monitor Heat Pump Temperatures (Priority: P1)

As a homeowner, I want to see my heat pump's temperature readings in Home Assistant so that I can monitor system performance and detect issues without leaving my dashboard.

**Why this priority**: Temperature monitoring is the foundation of heat pump visibility. Without temperature data, users cannot assess system health or make informed decisions about heating and hot water.

**Independent Test**: Can be fully tested by adding the integration and verifying that temperature sensors appear in Home Assistant with current readings from the heat pump.

**Acceptance Scenarios**:

1. **Given** the integration is configured with the correct serial port, **When** Home Assistant starts, **Then** 13 temperature sensors appear: 5 core sensors (Outdoor, Supply, Return, DHW, Brine Inlet), 4 room temperature sensors (C1-C4 from RC10 thermostats), and 4 room setpoint sensors (C1-C4 target temperatures)
2. **Given** the heat pump is operating normally, **When** I view the sensors in Home Assistant, **Then** I see temperature values in Celsius that update periodically
3. **Given** the serial connection is lost, **When** Home Assistant polls for data, **Then** sensors retain their last known values with a "stale" indicator in entity attributes, and reconnection is attempted with exponential backoff

---

### User Story 2 - View Compressor Status (Priority: P1)

As a homeowner, I want to see whether the compressor is running so that I can understand when the heat pump is actively heating.

**Why this priority**: Compressor status is essential for understanding energy consumption and system activity. It enables automations based on heat pump operation.

**Independent Test**: Can be fully tested by observing the binary sensor state while the heat pump cycles on and off.

**Acceptance Scenarios**:

1. **Given** the compressor is running, **When** I view the compressor sensor, **Then** it shows "Running" (on state)
2. **Given** the compressor is stopped, **When** I view the compressor sensor, **Then** it shows "Stopped" (off state)
3. **Given** I create an automation based on compressor state, **When** the compressor starts, **Then** the automation triggers correctly

---

### User Story 3 - Control Energy Blocking (Priority: P2)

As a homeowner, I want to block energy usage (prevent compressor and auxiliary heater from running) via Home Assistant so that I can pause heat pump operation during peak electricity rates or maintenance.

**Why this priority**: Energy blocking enables cost savings and integration with electricity tariff automations. It builds on monitoring capabilities to add active control.

**Independent Test**: Can be tested by toggling the energy block switch and verifying the heat pump stops heating operations.

**Acceptance Scenarios**:

1. **Given** energy blocking is off, **When** I turn on the energy block switch, **Then** the heat pump stops all heating operations
2. **Given** energy blocking is on, **When** I turn off the energy block switch, **Then** the heat pump resumes normal operation
3. **Given** energy blocking is enabled, **When** I view the switch in Home Assistant, **Then** it shows "On" and indicates blocking is active
4. **Given** an automation for off-peak rates, **When** peak rates begin, **Then** the automation can enable energy blocking automatically

---

### User Story 4 - Control DHW Extra Production (Priority: P2)

As a homeowner, I want to start extra hot water production via Home Assistant so that I can ensure hot water availability before guests arrive or after heavy usage.

**Why this priority**: DHW boost control adds practical value for daily use. It complements temperature monitoring by allowing users to act on low hot water temperatures.

**Independent Test**: Can be tested by triggering extra DHW production and observing the DHW temperature increase.

**Acceptance Scenarios**:

1. **Given** DHW temperature is low, **When** I set DHW extra duration to 2 hours, **Then** the heat pump begins heating the hot water tank for 2 hours
2. **Given** DHW extra production is active, **When** I set the duration to 0, **Then** the heat pump stops the extra heating cycle
3. **Given** DHW extra is running, **When** I view the number control in Home Assistant, **Then** it shows the remaining duration
4. **Given** an automation for morning hot water, **When** the scheduled time arrives, **Then** the automation can set a DHW extra duration (e.g., 1 hour)

---

### User Story 5 - Set DHW Stop Temperature (Priority: P2)

As a homeowner, I want to adjust the hot water stop temperature via Home Assistant so that I can control when the heat pump stops heating the DHW tank, balancing energy efficiency with hot water availability.

**Why this priority**: DHW stop temperature directly affects energy consumption and comfort. A higher stop temperature means more stored hot water but higher energy use. It complements the DHW extra production control by allowing users to fine-tune DHW heating behavior.

**Independent Test**: Can be tested by setting the stop temperature and verifying the heat pump stops DHW charging when the tank reaches the configured temperature.

**Acceptance Scenarios**:

1. **Given** the integration is running, **When** I view the DHW Stop Temperature control, **Then** I see a number entity displaying the current stop temperature in the 50-65°C range
2. **Given** I set the stop temperature to 55°C, **When** the heat pump processes the command, **Then** DHW charging stops when the tank reaches 55°C
3. **Given** I try to set a temperature outside the 50-65°C range, **When** validation occurs, **Then** the value is rejected and the entity retains its previous valid value

---

### Edge Cases

- What happens when the USB serial device is disconnected? The integration should mark all entities as "unavailable" and attempt reconnection.
- How does the system handle communication timeouts? Failed operations should log errors but not crash; entities show unavailable status.
- What happens if the heat pump is already blocking energy? The switch should reflect the current state correctly.
- What if DHW extra is started when tank is already at target temperature? The heat pump handles this internally; the integration simply sends the command.
- What happens when data is stale for extended periods? Entity attributes indicate staleness; user can use USB Connection switch to manually release/reconnect for troubleshooting. Stale data is preferred over "Unknown" for slow-changing values.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Integration MUST discover and connect to the heat pump via USB serial port
- **FR-002**: Integration MUST provide temperature sensors for: Outdoor, Supply, Return, DHW, Brine Inlet, Room Temperature (C1-C4), and Room Setpoint (C1-C4)
- **FR-003**: Integration MUST provide a binary sensor showing compressor running status
- **FR-004**: Integration MUST provide a switch to enable/disable energy blocking
- **FR-005**: Integration MUST provide a control to start/stop extra DHW production
- **FR-006**: Integration MUST update sensor values periodically with configurable interval (default: 60 seconds, range: 10-300 seconds)
- **FR-007**: Integration MUST handle connection failures gracefully with exponential backoff reconnection (5s initial, doubling up to 2 min max) while retaining last-known-good sensor values indefinitely. Entity attributes MUST indicate data staleness (age in seconds, last successful update timestamp)
- **FR-008**: Integration MUST support configuration via YAML file
- **FR-009**: Integration MUST log errors with sufficient detail for troubleshooting
- **FR-010**: Integration MUST maintain a persistent connection to the heat pump (not reconnect on every poll)
- **FR-011**: Integration MUST retain last-known-good sensor values indefinitely when CAN bus communication is unavailable, displaying stale data with attributes indicating: `last_update_age_seconds`, `last_successful_update`, and `data_is_stale` (boolean). Sensors MUST only show "unavailable" before their first successful read.
- **FR-012**: Integration MUST provide a number entity for DHW stop temperature control (50-65°C range, 0.5°C step)

### Key Entities

Entity naming convention: Entity-only names (e.g., "Outdoor Temperature", "Compressor") with `has_entity_name=True`. Home Assistant automatically prepends device name "Heat Pump" in the UI, resulting in "Heat Pump Outdoor Temperature", "Heat Pump Compressor", etc.

- **Temperature Sensor**: Represents a temperature reading from the heat pump. Key attributes: value (Celsius), sensor type (outdoor/supply/return/dhw/brine/room_c1-c4/setpoint_c1-c4), last update timestamp. Room temperatures and setpoints are read from RC10 thermostat broadcasts on circuit bases 0x0060-0x0063
- **Compressor Status**: Binary state indicating whether the compressor is running. Derived from compressor frequency parameter
- **Energy Block Switch**: Toggle control for blocking heat pump energy usage. Maps to the ADDITIONAL_BLOCKED parameter
- **DHW Extra Control**: Number input (0-24 hours) for setting extra hot water production duration. Setting to 0 stops extra production; setting 1-24 starts heating for that duration. Uses the DHW_EXTRA_DURATION parameter
- **DHW Stop Temperature**: Number input (50-65°C, step 0.5°C) for setting the temperature at which DHW tank heating stops. Higher values mean more stored hot water but higher energy use. Maps to the XDHW_STOP_TEMP parameter

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 13 temperature sensors display accurate readings within 0.5 degrees of actual values
- **SC-002**: Compressor status updates within 60 seconds of state change
- **SC-003**: Energy blocking takes effect within 30 seconds of switch toggle
- **SC-004**: DHW extra production starts within 30 seconds of command
- **SC-005**: Integration remains stable for 24+ hours of continuous operation without memory leaks or crashes
- **SC-006**: Connection recovery completes within 2 minutes after USB device reconnection
- **SC-007**: User can configure and use the integration within 5 minutes using YAML configuration
- **SC-008**: DHW stop temperature changes take effect within 30 seconds of command

## Clarifications

### Session 2025-12-13

- Q: What type of control should DHW Extra be (button/switch/number)? → A: Number input with duration in hours (0-24), matching heat pump native behavior
- Q: Should polling interval be configurable? → A: Yes, configurable via YAML (default 60s, range 10-300s)
- Q: How should reconnection work after USB disconnection? → A: Exponential backoff (5s initial, doubling up to 2 min max)
- Q: Should the integration support remote socketcand connections? → A: No, local USB serial only (remote is out of scope)
- Q: How should HA entities be named? → A: Use entity-only descriptive names (e.g., "Outdoor Temperature") with `has_entity_name=True`. Home Assistant prepends device name "Heat Pump" automatically for display.

## Assumptions

- The heat pump is connected via USBtin CAN-to-USB adapter on a Linux system (typically Raspberry Pi)
- The serial port is accessible (user is in dialout group or has appropriate permissions)
- Home Assistant is running on the same machine as the USB adapter
- The existing buderus_wps Python library is bundled with the integration
- Temperature readings use the passive broadcast monitoring approach for reliability
- The ADDITIONAL_BLOCKED parameter controls energy blocking (verified in FHEM reference)
- The DHW_EXTRA_DURATION parameter controls extra hot water production
- The XDHW_STOP_TEMP parameter controls DHW charging stop temperature (range 50-65°C)

## Out of Scope

- Home Assistant UI-based configuration flow (YAML only for this version)
- HACS distribution packaging (future enhancement)
- Heating circuit climate entities (future enhancement)
- Schedule programming (future enhancement)
- Alarm management (future enhancement)
- Multiple heat pump support (single device only)
- Remote CAN connection via socketcand TCP/IP (local USB serial only)
