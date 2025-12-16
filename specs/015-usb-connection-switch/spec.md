# Feature Specification: USB Connection Control Switch

**Feature Branch**: `015-usb-connection-switch`
**Created**: 2025-12-16
**Status**: Draft
**Input**: User description: "Add Home Assistant switch to temporarily release USB port for CLI debugging"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Release USB for CLI Debugging (Priority: P1)

A developer is actively monitoring their Buderus heat pump through Home Assistant when they notice unusual behavior. They need to use the CLI tool to send test CAN messages and debug the communication protocol, but the CLI cannot access the USB port while the Home Assistant integration is connected.

The developer opens Home Assistant, navigates to the heat pump integration, and toggles the "USB Connection" switch to OFF. The integration immediately releases the USB port. The developer then runs CLI commands to read parameters, monitor broadcasts, and test write operations. After debugging, the developer toggles the switch back to ON, and the integration reconnects automatically, resuming normal monitoring.

**Why this priority**: This is the core value proposition of the feature. Without this capability, developers must completely stop the Home Assistant integration (service restart or config entry reload) to debug via CLI, which is slow and disruptive. This addresses the primary workflow bottleneck.

**Independent Test**: Can be fully tested by toggling the switch OFF, verifying the CLI can connect to the USB port, running a CLI read command successfully, then toggling ON and verifying HA reconnects. Delivers immediate value as a standalone feature.

**Acceptance Scenarios**:

1. **Given** Home Assistant integration is running and connected to USB port, **When** developer toggles USB Connection switch to OFF, **Then** the integration releases the USB port within 2 seconds
2. **Given** USB Connection switch is OFF (port released), **When** developer runs a CLI read command, **Then** the CLI successfully connects and retrieves parameter values
3. **Given** CLI debugging session is complete and USB Connection switch is OFF, **When** developer toggles switch to ON, **Then** integration reconnects to USB port and resumes normal operation within 5 seconds
4. **Given** USB Connection switch is OFF, **When** polling cycle occurs, **Then** sensor entities continue showing last-known-good data with staleness indicators (no "unavailable" state)

---

### User Story 2 - Handle Port Busy Error (Priority: P2)

A developer has toggled the USB Connection switch OFF and is actively running CLI commands. While the CLI tool is still connected, the developer accidentally toggles the USB Connection switch back to ON (perhaps by automation or muscle memory).

The Home Assistant integration attempts to reconnect but finds the USB port is still in use by the CLI tool. Instead of silently failing or crashing, the integration shows a clear error message in the Home Assistant logs: "Cannot connect - port may be in use by CLI." The switch remains in the OFF state, and sensor entities continue displaying stale data. The developer sees the error, properly exits the CLI tool, then toggles the switch ON again successfully.

**Why this priority**: Error handling for race conditions is critical to prevent confusion and data loss. Without proper error feedback, developers may not understand why reconnection fails. This ensures robust operation under real-world usage patterns.

**Independent Test**: Can be tested by keeping a CLI session active, attempting to toggle the switch ON, verifying the error is logged and the switch stays OFF, then closing CLI and successfully reconnecting. Delivers defensive robustness as a standalone improvement.

**Acceptance Scenarios**:

1. **Given** USB port is actively in use by CLI tool, **When** developer toggles USB Connection switch to ON, **Then** integration logs "Cannot connect - port may be in use" error and switch remains OFF
2. **Given** reconnection failed due to port busy error, **When** developer closes CLI tool and toggles switch ON again, **Then** integration successfully reconnects
3. **Given** reconnection fails due to port busy, **When** automatic polling occurs, **Then** sensor entities remain available with stale data (not marked unavailable)

---

### User Story 3 - Auto-Reconnection Behavior (Priority: P3)

A developer is monitoring heat pump operation through Home Assistant when the USB cable becomes physically disconnected (accidental unplug, loose connection, or hardware failure). The integration's existing auto-reconnection logic attempts to restore the connection every few seconds using exponential backoff.

However, the developer now needs to debug the disconnection issue using the CLI tool. They toggle the USB Connection switch to OFF. The auto-reconnection attempts immediately stop, respecting the manual disconnect state. The developer plugs the USB cable back in and debugs via CLI. When finished, they toggle the switch back to ON, and the integration reconnects immediately without waiting for the backoff timer.

**Why this priority**: This ensures manual disconnect mode properly overrides automatic reconnection behavior. While less common than P1/P2 scenarios, it's essential for the feature to work correctly in all states (connected, disconnected-auto, disconnected-manual). Prevents confusing behavior where auto-reconnect fights with manual control.

**Independent Test**: Can be tested by simulating a connection failure (or using a failing mock), toggling the switch OFF, verifying auto-reconnect stops, then toggling ON and verifying immediate reconnection attempt. Validates state machine correctness as a standalone behavior.

**Acceptance Scenarios**:

1. **Given** integration is auto-reconnecting after connection failure (in backoff loop), **When** developer toggles USB Connection switch to OFF, **Then** auto-reconnection attempts stop immediately
2. **Given** USB Connection switch is OFF (manual disconnect mode), **When** natural connection failure recovery is attempted, **Then** integration does not attempt auto-reconnection
3. **Given** integration is in auto-reconnect backoff with 30-second delay, **When** developer toggles switch ON (manual reconnect), **Then** integration attempts reconnection immediately (bypassing backoff timer)
4. **Given** USB Connection switch is ON and connection is stable, **When** USB cable is unplugged, **Then** existing auto-reconnection logic activates normally (manual disconnect does not interfere with auto-reconnect when switch is ON)

---

### Edge Cases

- What happens when the Home Assistant service restarts while the USB Connection switch is OFF?
  - Expected: Integration always attempts connection on startup (switch initializes to ON by default). State is not persistent across restarts. This is acceptable as restarts are rare and the default should be "connected."

- What happens if the developer toggles the switch OFF and ON rapidly (multiple times in quick succession)?
  - Expected: Each toggle queues the appropriate action (disconnect/connect). The coordinator's async lock prevents race conditions. Rapid toggling may cause brief connection instability but should not crash or corrupt state.

- What happens to ongoing read/write operations when the switch is toggled OFF mid-operation?
  - Expected: Current operation may fail with timeout or connection error. Graceful degradation returns stale data. No data corruption. Next operation after reconnection proceeds normally.

- What happens if the USB device is physically unplugged while the switch is OFF?
  - Expected: No errors logged (port is already released). When switch is toggled ON, reconnection attempt fails with device-not-found error. User must plug device back in and toggle ON again.

- What happens to automations or scripts that depend on sensor data when the switch is OFF?
  - Expected: Sensors continue returning last-known-good values (stale data) rather than "unavailable." Automations see no disruption unless stale data exceeds threshold (3 consecutive failures). This prevents false automation triggers during brief debugging sessions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a toggle switch entity named "USB Connection" visible in the Home Assistant UI
- **FR-002**: System MUST disconnect from the USB serial port within 2 seconds when the switch is toggled to OFF
- **FR-003**: System MUST reconnect to the USB serial port within 5 seconds when the switch is toggled to ON (assuming port is available)
- **FR-004**: System MUST prevent automatic reconnection logic from activating when the switch is in OFF state (manual disconnect mode)
- **FR-005**: System MUST resume automatic reconnection behavior when the switch is toggled back to ON
- **FR-006**: System MUST log a clear error message when reconnection fails due to port being in use (e.g., "Cannot connect - port may be in use by CLI")
- **FR-007**: System MUST preserve last-known-good sensor data when USB connection is released, showing stale values rather than marking entities as unavailable
- **FR-008**: System MUST keep the switch in OFF state when reconnection fails, requiring explicit user action to retry
- **FR-009**: System MUST cancel any pending auto-reconnection tasks when manual disconnect is initiated
- **FR-010**: System MUST reset reconnection backoff timer when manual reconnection is initiated (immediate retry, no exponential delay)
- **FR-011**: System MUST initialize the switch to ON state (connected) when Home Assistant starts or the integration is reloaded
- **FR-012**: System MUST maintain thread safety when toggling the switch during ongoing read/write operations
- **FR-013**: Switch state MUST accurately reflect manual disconnect intent (OFF = "I want it disconnected") rather than actual connection status
- **FR-014**: System MUST allow CLI tool to successfully connect to USB port when switch is OFF (port is fully released, not held open)

### Key Entities

- **USB Connection Switch**: A Home Assistant switch entity that controls whether the integration maintains a connection to the USB serial port
  - States: ON (connected/attempting to connect), OFF (manually disconnected)
  - Icon: USB port icon (mdi:usb-port)
  - Actions: Turn ON (connect/reconnect), Turn OFF (disconnect/release port)

- **Coordinator Connection State**: Internal state tracking for the integration coordinator
  - Connection Status: connected, disconnected (failure), manual_disconnect
  - Auto-Reconnect Task: pending reconnection task that must be cancelled during manual disconnect
  - Manual Disconnect Flag: boolean indicating whether disconnect is user-initiated or due to failure

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can switch from Home Assistant to CLI debugging workflow in under 10 seconds (toggle OFF → run CLI command)
- **SC-002**: Integration successfully reconnects on manual toggle ON in 95% of cases (excluding port-busy scenarios)
- **SC-003**: Sensor entities remain responsive during manual disconnect, showing stale data for at least 10 minutes before marking unavailable
- **SC-004**: Zero crashes or state corruption from rapid switch toggling (100 ON/OFF cycles in test suite)
- **SC-005**: Error messages for port-busy scenarios are clear and actionable in 100% of failure cases
- **SC-006**: Auto-reconnection stops within 2 seconds of manual disconnect in 100% of cases
- **SC-007**: Manual reconnection bypasses backoff timer and attempts immediately in 100% of cases
- **SC-008**: Zero data loss or corruption during disconnect/reconnect cycles (verified across 1000 test cycles)
- **SC-009**: CLI tool can connect to USB port within 1 second after switch is toggled OFF in 100% of cases
- **SC-010**: Feature reduces debugging workflow time by at least 80% compared to service restart method (baseline: ~60 seconds restart time → target: ~10 seconds with switch)

## Assumptions

- USB serial port path does not change during runtime (device enumeration remains stable)
- Only one process (either HA integration or CLI) attempts to access the USB port at a time under normal operation
- Developers understand that switch OFF means "release port for other tools" not "connection failed"
- Stale data from last-known-good values is acceptable during debugging sessions (typical duration: 1-15 minutes)
- Home Assistant restart/reload occurring while switch is OFF is rare enough that non-persistent state is acceptable
- Serial port exclusive access model: only one process can open the port at a time (standard OS behavior)
- Integration is running on a system where the user has permission to access the USB serial device
- CLI tool and Home Assistant integration do not coordinate access (no locking protocol between processes)

## Dependencies

- Existing graceful degradation system (v1.1.0) for stale data handling during disconnection
- Existing auto-reconnection logic with exponential backoff (BACKOFF_INITIAL, BACKOFF_MAX constants)
- Existing coordinator infrastructure (BuderusCoordinator, _connected flag, _reconnect_task)
- Existing switch entity pattern (BuderusEnergyBlockSwitch serves as reference implementation)
- pyserial library for USB serial port management (exclusive port access model)
- Home Assistant SwitchEntity platform for UI integration

## Out of Scope

- Persistent switch state across Home Assistant restarts (acceptable limitation, initializes to ON)
- Automatic detection of when CLI tool has released the port (user must manually toggle ON)
- Coordination protocol between HA integration and CLI to automatically arbitrate port access
- Binary sensor showing actual connection status vs intended connection status (may be added in future)
- Lock file or semaphore mechanism for inter-process USB port coordination
- Automatic toggling based on external triggers (e.g., "when CLI process starts, auto-toggle OFF")
- Configuration option to change default switch state on startup
- Multiple simultaneous connections to USB port (not supported by hardware/OS)
- USB hot-swap detection and automatic reconnection when cable is plugged back in (requires hardware event monitoring)