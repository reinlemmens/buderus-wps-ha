# Feature Specification: Home Assistant Supervisor Add-on

**Feature Branch**: `013-ha-supervisor-addon`
**Created**: 2025-12-12
**Status**: Draft
**Input**: Docker-based Home Assistant add-on for Buderus WPS heat pump control via USB serial CAN bus

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install Add-on from Repository (Priority: P1)

As a Home Assistant user, I want to install the Buderus WPS add-on from a repository so that I can control my heat pump without manually copying files or managing dependencies.

**Why this priority**: Installation is the entry point for all users. Without easy installation, the add-on provides no value. Repository-based installation is the standard Home Assistant add-on distribution method.

**Independent Test**: Can be fully tested by adding the repository URL to Home Assistant and installing the add-on from the Add-on Store.

**Acceptance Scenarios**:

1. **Given** Home Assistant OS or Supervised installation, **When** I add the repository URL to the Add-on Store, **Then** the Buderus WPS add-on appears in the available add-ons list
2. **Given** the add-on is listed in the store, **When** I click Install, **Then** the add-on downloads and installs within 5 minutes
3. **Given** the add-on is installed, **When** I view the add-on info, **Then** I see the version, description, and documentation link

---

### User Story 2 - Configure USB Serial Device (Priority: P1)

As a user, I want to configure which USB serial device the add-on uses so that I can connect to my USBtin CAN adapter.

**Why this priority**: The add-on cannot function without access to the USB serial device. This is the essential configuration that enables all functionality.

**Independent Test**: Can be tested by specifying the serial device path in configuration and verifying the add-on connects successfully.

**Acceptance Scenarios**:

1. **Given** the add-on is installed, **When** I open the Configuration tab, **Then** I see an option to specify the serial device path
2. **Given** I enter a valid device path (e.g., /dev/ttyACM0), **When** I start the add-on, **Then** it connects to the heat pump and logs successful connection
3. **Given** I enter an invalid device path, **When** I start the add-on, **Then** it shows a clear error message explaining the device was not found
4. **Given** the USB adapter is unplugged, **When** the add-on is running, **Then** it detects the disconnection and logs an error

---

### User Story 3 - Monitor Heat Pump Data via MQTT (Priority: P1)

As a Home Assistant user, I want the add-on to publish heat pump data to MQTT so that Home Assistant automatically discovers and displays my sensors.

**Why this priority**: MQTT auto-discovery is the standard way for add-ons to expose data to Home Assistant. This enables seamless integration without manual entity configuration.

**Independent Test**: Can be tested by starting the add-on and verifying that temperature sensors and compressor status appear automatically in Home Assistant.

**Acceptance Scenarios**:

1. **Given** the add-on is running and connected to the heat pump, **When** it reads temperature values, **Then** it publishes them to MQTT with Home Assistant discovery payloads
2. **Given** Home Assistant has MQTT integration configured, **When** the add-on publishes discovery messages, **Then** temperature sensors appear automatically in Home Assistant
3. **Given** sensors are discovered, **When** I view them in Home Assistant, **Then** I see current temperature readings with proper units and device grouping
4. **Given** the add-on reads compressor status, **When** it publishes the status, **Then** a binary sensor appears showing running/stopped state

---

### User Story 4 - Control Heat Pump via MQTT (Priority: P2)

As a user, I want to control my heat pump through Home Assistant switches so that I can manage energy blocking and DHW production from my dashboard.

**Why this priority**: Control capabilities add significant value beyond monitoring but require the monitoring infrastructure to be in place first.

**Independent Test**: Can be tested by toggling switches in Home Assistant and verifying the heat pump responds to commands.

**Acceptance Scenarios**:

1. **Given** the add-on is running, **When** Home Assistant discovers MQTT entities, **Then** control switches appear for heating mode and DHW mode
2. **Given** a heating mode switch exists, **When** I change the mode in Home Assistant, **Then** the add-on sends the appropriate command to the heat pump
3. **Given** I change DHW mode to "Off", **When** the command is processed, **Then** the heat pump stops hot water production and the state updates in Home Assistant
4. **Given** I enable extra hot water production, **When** the command is sent, **Then** the heat pump starts the DHW boost cycle

---

### User Story 5 - View Add-on Logs (Priority: P2)

As a user troubleshooting issues, I want to view add-on logs so that I can diagnose connection problems or communication errors.

**Why this priority**: Logs are essential for troubleshooting and support. Users need visibility into add-on operation to resolve issues independently.

**Independent Test**: Can be tested by viewing the Log tab in the add-on panel and verifying meaningful messages appear.

**Acceptance Scenarios**:

1. **Given** the add-on is running, **When** I click the Log tab, **Then** I see timestamped log entries
2. **Given** the add-on connects to the heat pump, **When** I view logs, **Then** I see a success message with device details
3. **Given** a communication error occurs, **When** I view logs, **Then** I see the error with actionable diagnostic information
4. **Given** verbose logging is enabled in configuration, **When** I view logs, **Then** I see detailed CAN bus communication messages

---

### Edge Cases

- What happens when the MQTT broker is unavailable? The add-on should buffer messages for up to 60 seconds and retry, logging warnings but not crashing. Older messages are discarded if buffer fills.
- How does the add-on handle USB device hot-unplug? It should detect the loss, mark entities as unavailable, and attempt reconnection.
- What if Home Assistant restarts while the add-on is running? The add-on should re-publish discovery messages to restore entities.
- What if the heat pump doesn't respond to a command? The add-on should log the timeout and mark the entity as unavailable temporarily.
- What happens with concurrent command requests? Commands should be queued and processed sequentially with a minimum 500ms delay between commands to avoid CAN bus conflicts.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Add-on MUST be installable from a GitHub repository via Home Assistant's Add-on Store
- **FR-002**: Add-on MUST run as a Docker container managed by Home Assistant Supervisor
- **FR-003**: Add-on MUST provide configuration options for serial device path and MQTT settings
- **FR-004**: Add-on MUST access USB serial devices through Supervisor's device mapping
- **FR-005**: Add-on MUST auto-detect MQTT broker via Supervisor API when available, with fallback to manual configuration (host, port, credentials)
- **FR-006**: Add-on MUST publish sensor data using MQTT Discovery protocol for automatic entity creation
- **FR-007**: Add-on MUST publish 6 temperature sensors: outdoor, supply, return, DHW, buffer top, buffer bottom
- **FR-008**: Add-on MUST publish compressor status as a binary sensor (on when running)
- **FR-009**: Add-on MUST publish Heating Season Mode as a select entity with options: Winter, Automatic, Summer
- **FR-010**: Add-on MUST publish DHW Program Mode as a select entity with options: Automatic, Always On, Always Off
- **FR-011**: Add-on MUST publish Holiday Mode as a switch entity (on/off)
- **FR-012**: Add-on MUST publish Extra Hot Water Duration as a number entity (0-48 hours)
- **FR-013**: Add-on MUST publish Extra Hot Water Target as a number entity (50.0-65.0°C)
- **FR-014**: Add-on MUST update sensor values at a configurable interval (default: 60 seconds)
- **FR-015**: Add-on MUST handle connection failures gracefully and attempt automatic reconnection
- **FR-016**: Add-on MUST provide a health check endpoint for Supervisor monitoring
- **FR-017**: Add-on MUST include documentation accessible from the Add-on Store

### Key Entities

- **Add-on Container**: Docker container running the Buderus WPS service. Managed by Supervisor with resource limits, restart policies, and device mappings.
- **MQTT Discovery Payload**: Configuration message published to MQTT that instructs Home Assistant to create an entity. Includes entity type, unique ID (format: `buderus_wps_<entity_name>`), device info, and state/command topics.
- **Device Info**: Metadata grouping all entities under a single device in Home Assistant. Includes manufacturer (Buderus), model (WPS), and serial device identifier.

### Sensor Entities (Read-Only)

These entities display temperature and status values from the heat pump via CAN bus broadcasts:

| Entity Name | Type | Unit | Description |
|-------------|------|------|-------------|
| Outdoor Temperature | sensor | °C | Outside air temperature (GT2) |
| Supply Temperature | sensor | °C | Heat pump supply line temperature |
| Return Temperature | sensor | °C | Heat pump return line temperature |
| DHW Temperature | sensor | °C | Domestic hot water tank temperature |
| Buffer Top Temperature | sensor | °C | Buffer tank top/supply (GT8) |
| Buffer Bottom Temperature | sensor | °C | Buffer tank bottom/return (GT9) |
| Compressor Status | binary_sensor | - | Compressor running state (on/off) |

### Control Entities (Read/Write - Hardware Verified)

These entities allow users to control heat pump operation. All have been hardware-verified to accept CAN bus writes:

| Entity Name | Type | Options/Range | Description |
|-------------|------|---------------|-------------|
| Heating Season Mode | select | Winter, Automatic, Summer | Controls space heating enable/disable. "Summer" blocks all heating (peak hour use case) |
| DHW Program Mode | select | Automatic, Always On, Always Off | Controls hot water production. "Always Off" blocks DHW heating (peak hour use case) |
| Holiday Mode | switch | On/Off | Enables holiday/absence mode for Circuit 1 |
| Extra Hot Water Duration | number | 0-48 hours | Duration for extra hot water boost (0 = off) |
| Extra Hot Water Target | number | 50.0-65.0 °C | Target temperature for extra hot water boost |

### Control Entity Value Mappings

**Heating Season Mode** (HEATING_SEASON_MODE):
- Winter (0): Forced heating - heating always enabled
- Automatic (1): Normal operation - heating based on outdoor temperature
- Summer (2): No heating - hot water only (use for peak hour blocking)

**DHW Program Mode** (DHW_PROGRAM_MODE):
- Automatic (0): Normal operation - follows time program
- Always On (1): DHW always active
- Always Off (2): No DHW heating (use for peak hour blocking)

**Holiday Mode** (HOLIDAY_ACTIVE_GLOBAL):
- Off (0): Normal operation
- On (1): Holiday mode active for Circuit 1

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Add-on installs successfully in under 5 minutes on standard Home Assistant hardware
- **SC-002**: All temperature sensors appear automatically within 60 seconds of add-on startup
- **SC-003**: Sensor values update at the configured interval with less than 10% variation
- **SC-004**: Control commands are executed within 30 seconds of user interaction
- **SC-005**: Add-on recovers from USB disconnection within 2 minutes of device reconnection
- **SC-006**: Add-on maintains stable operation for 7+ days without memory leaks or crashes
- **SC-007**: Log messages provide sufficient detail to diagnose 90% of common issues without support
- **SC-008**: Users can complete installation and see first sensor data within 15 minutes

## Assumptions

- User has Home Assistant OS or Home Assistant Supervised (not Core or Container, which don't support add-ons)
- User has the MQTT integration configured in Home Assistant (either Mosquitto add-on or external broker)
- USB serial device (USBtin) is physically connected to the same machine running Home Assistant
- The existing buderus_wps Python library is packaged into the Docker image
- User has basic familiarity with Home Assistant add-on installation

## Technical Constraints

- **Docker Base Image**: ghcr.io/home-assistant/amd64-base-python (includes S6 overlay for process supervision)
- **Multi-architecture**: Must support amd64 and aarch64 for Raspberry Pi compatibility

## Dependencies

- **Feature 001**: CAN USB Serial communication (provides USBtinAdapter)
- **Feature 002**: Parameter definitions (provides parameter registry)
- **Feature 005**: Parameter read/write (provides HeatPumpClient)
- **Home Assistant Supervisor**: Provides add-on management infrastructure
- **MQTT Broker**: Mosquitto add-on or external MQTT broker for entity communication

## Clarifications

### Session 2025-12-13

- Q: How should MQTT broker connection be established? → A: Auto-detect via Supervisor API with manual fallback
- Q: What Docker base image should be used? → A: ghcr.io/home-assistant/amd64-base-python (HA-optimized with S6 overlay)
- Q: How long should MQTT messages be buffered when broker unavailable? → A: 60 seconds
- Q: How should entity unique IDs be generated? → A: Static prefix (e.g., "buderus_wps_outdoor_temp")
- Q: What minimum delay between CAN bus commands? → A: 500ms minimum

## Out of Scope

- Home Assistant Core/Container installation support (add-ons require Supervisor)
- Remote USB device support (device must be local to HA machine)
- HACS distribution (add-on store repository only for this version)
- Web UI for the add-on (configuration via YAML and HA interface only)
- Multi-device support (single heat pump per add-on instance)
