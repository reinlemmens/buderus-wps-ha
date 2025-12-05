# Feature Specification: CAN over USB Serial Connection

**Feature Branch**: `001-can-usb-serial`
**Created**: 2025-10-21
**Status**: Draft
**Input**: User description: "create a class representing the CAN over usb serial connection"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Establish Connection to Heat Pump (Priority: P1)

A developer or system integrator needs to establish a reliable connection between their computer/controller and the Buderus WPS heat pump via a USBtin CAN adapter. They need to open the connection, verify it's working, and have confidence that communication errors will be detected and reported.

**Why this priority**: This is the foundational capability. Without reliable connection establishment, no other features can work. This represents the minimal viable functionality.

**Independent Test**: Can be fully tested by connecting to a USBtin device (or mock), opening the connection, verifying the serial port opens successfully, and checking that connection status can be queried. Delivers the ability to establish basic hardware communication.

**Acceptance Scenarios**:

1. **Given** a USBtin adapter is connected to the computer at `/dev/ttyACM0`, **When** the connection is opened with correct baud rate, **Then** the serial port opens successfully and the connection is ready for CAN communication
2. **Given** the connection is open, **When** the connection status is queried, **Then** the system reports the connection as active and ready
3. **Given** an invalid serial port path is provided, **When** attempting to open the connection, **Then** the system reports a clear error indicating the port cannot be accessed

---

### User Story 2 - Passive CAN Bus Monitoring (Priority: P2)

A developer needs to receive and decode CAN messages that the heat pump broadcasts continuously. The Buderus WPS broadcasts sensor data (temperatures, states, counters) on the CAN bus without requiring active requests. The system must receive these broadcasts, decode the CAN ID structure, and provide the raw data for interpretation.

**Why this priority**: Passive monitoring is the most reliable data access method. Hardware verification (2025-12-05) confirmed that broadcast data matches FHEM readings exactly, while active RTR requests may not receive responses on all firmware versions.

**Hardware Verified**: Passive monitoring tested against FHEM readings - exact match on 5 parameters, within tolerance on 4 parameters (real-time variation).

**Independent Test**: Can be tested by opening a connection (US1), listening to bus traffic, and verifying that broadcast CAN messages are received and can be decoded.

**Acceptance Scenarios**:

1. **Given** an open connection to the heat pump, **When** listening passively for CAN messages, **Then** the system receives broadcast messages continuously (30+ messages/second typical)
2. **Given** broadcast CAN messages are received, **When** the CAN ID is decoded, **Then** the system correctly extracts the parameter index and element type from the CAN ID structure
3. **Given** the system is monitoring passively, **When** a specific CAN ID is watched for, **Then** the system can filter and return only matching messages

---

### User Story 2b - Send CAN Messages (Priority: P2b - Optional)

A developer may need to send CAN messages to the heat pump controller for active parameter reads or writes. Note: Hardware verification (2025-12-05) found that active RTR requests may not receive responses without a KM200 device on the bus. This functionality is provided but may not work on all installations.

**Why this priority**: Lower than passive monitoring because it's not universally supported. Some installations require a KM200 gateway for active communication.

**Hardware Verified**: Transmit works (got `Z` OK response), but RTR requests to element list CAN IDs did not receive responses. The heat pump may require KM200 handshake protocol.

**Independent Test**: Can be tested by opening a connection (US1), sending a CAN message, and verifying successful transmission (adapter acknowledges with `Z`).

**Acceptance Scenarios**:

1. **Given** an open connection, **When** a CAN data frame is transmitted, **Then** the adapter acknowledges successful transmission
2. **Given** an open connection, **When** multiple CAN messages are sent in sequence, **Then** each message is transmitted completely before the next begins
3. **Given** a CAN message is sent, **When** no response is received within the timeout period, **Then** the system reports a timeout error with details about the failed message

---

### User Story 3 - Graceful Connection Management (Priority: P3)

A developer needs to cleanly close connections, handle disconnections, and recover from transient errors. The system should manage resources properly and provide clear status information about connection health.

**Why this priority**: Production systems need robust error handling and resource management, but basic communication (P1, P2) can work without advanced connection management.

**Independent Test**: Can be tested by opening a connection, intentionally disconnecting the USB device, attempting communication, and verifying appropriate errors are raised. Then test clean connection closure and verify resources are released.

**Acceptance Scenarios**:

1. **Given** an open connection, **When** the connection is explicitly closed, **Then** the serial port is released and subsequent communication attempts report the connection as closed
2. **Given** an active connection, **When** the USB device is physically disconnected, **Then** the next communication attempt detects the disconnection and reports an appropriate error
3. **Given** a connection that experienced a transient error, **When** automatic reconnection is attempted, **Then** the system re-establishes the connection without data loss or corruption

---

### Edge Cases

- What happens when the serial port is opened by another process (exclusive access conflict)?
- How does the system handle partial CAN messages received due to buffer overflow or timing issues?
- What happens when invalid baud rates or communication parameters are specified?
- How are CAN bus errors (error frames, bus-off conditions) detected and reported?
- What happens if the USBtin firmware version is incompatible?
- How does the system behave when receiving unexpected or malformed data from the adapter?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST open a serial connection to a specified serial port device with configurable baud rate (default: 115200 for USBtin compatibility)
- **FR-002**: System MUST initialize the CAN adapter with appropriate commands for the specific hardware type (starting with USBtin support)
- **FR-003**: System MUST send CAN messages with proper framing and encoding according to the adapter's protocol
- **FR-004**: System MUST receive CAN messages from the adapter and parse them into structured data
- **FR-005**: System MUST implement timeout mechanisms for all communication operations with configurable timeout values (default: 2 seconds for read operations)
- **FR-006**: System MUST detect and report communication errors including timeout, disconnection, framing errors, and CAN bus errors
- **FR-007**: System MUST provide connection status information (connected, disconnected, error state)
- **FR-008**: System MUST properly close and release serial port resources when connection is terminated
- **FR-009**: System MUST support read-only mode where CAN messages can be received but not transmitted (for safe monitoring)
- **FR-010**: System MUST handle concurrent access protection to prevent simultaneous operations from corrupting the communication stream
- **FR-011**: System MUST log all CAN communication at configurable verbosity levels for debugging and troubleshooting
- **FR-012**: System MUST validate connection parameters (port path, baud rate, timeout values) before attempting connection

### Key Entities

- **CAN Message**: Represents a single CAN bus message with identifier, data payload (0-8 bytes), and metadata (timestamp, direction, error flags). Used for all communication between the system and heat pump controller.

- **Connection**: Represents the active serial port connection state, including port path, communication parameters (baud rate, timeout), adapter type, and current status (connecting, connected, error, closed).

- **Adapter Configuration**: Represents hardware-specific settings for different CAN adapter types (e.g., USBtin vs. socketcand), including initialization commands, message framing format, and capabilities.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can establish connection to a USBtin adapter in under 2 seconds from initialization call
- **SC-002**: System successfully sends and receives CAN messages with 99.9% reliability under normal operating conditions (no hardware faults)
- **SC-003**: All communication errors are detected within one timeout period and reported with sufficient detail for troubleshooting
- **SC-004**: Connection resources are properly released in 100% of cases, including abnormal termination scenarios
- **SC-005**: System handles at least 100 messages per second without message loss or buffer overflow
- **SC-006**: Connection recovery from transient errors succeeds in under 5 seconds without manual intervention

## Assumptions

- The USBtin CAN adapter is the primary target hardware, with other adapters (socketcand) to be supported through the same abstraction later
- Standard RS-232 serial communication parameters are sufficient (8 data bits, no parity, 1 stop bit)
- The host system has appropriate USB/serial drivers installed for the adapter hardware
- The CAN bus bitrate configuration is handled separately from the serial connection (typically configured once in the adapter's non-volatile memory)
- Thread-safety is required as the library may be used in async contexts or with multiple concurrent users
- **Passive monitoring is the primary data access method** - active RTR requests may not work without KM200 gateway

---

## Hardware Verification Results (2025-12-05)

### Test Environment
- **Device**: Buderus WPS heat pump
- **Adapter**: USBtin on `/dev/ttyACM0` (Raspberry Pi)
- **Reference**: FHEM plugin 26_KM273v018.pm captured readings

### Verification Summary

| Test | Result | Notes |
|------|--------|-------|
| Serial connection | ✅ Pass | Opens at 115200 baud |
| CAN transmit | ✅ Pass | Adapter returns `Z` (OK) |
| Passive receive | ✅ Pass | 30+ messages/second |
| Data accuracy | ✅ Pass | Matches FHEM within tolerance |
| Active RTR requests | ⚠️ Limited | No response to element list requests |

### Passive Monitoring Accuracy

| CAN ID | FHEM Value | Live Value | Match |
|--------|------------|------------|-------|
| 0x0C084060 | 214 | 214 | Exact (21.4°C) |
| 0x0C084062 | 228 | 228 | Exact (22.8°C) |
| 0x0C084063 | 246 | 246 | Exact (24.6°C) |
| 0x0C0E8060 | 552 | 553 | ~1 (55.2°C) |
| 0x0C000060 | 201 | 200 | ~1 (20.0°C) |

### CAN ID Structure (Broadcast Data)

The heat pump broadcasts data using this CAN ID structure:

```
Bits 31-24: Prefix (0x0C = response/data, 0x00 = status, 0x08 = counter)
Bits 23-12: Parameter Index (identifies the parameter type)
Bits 11-0:  Element Type (0x060-0x063 = units E21/E22/E31/E32, 0x270 = counter, 0x403 = config)
```

Example decoding:
- `0x0C084060`: Prefix=0x0C, ParamIdx=0x084 (33), Element=0x060 (unit 0)
- `0x0C084061`: Same parameter, Element=0x061 (unit 1)

### Active Request Limitations

The FHEM element list protocol (`R01FD7FE00` → `T09FD7FE0`) requires a KM200 device on the CAN bus to respond. Without KM200:
- RTR requests are transmitted successfully (adapter acknowledges)
- No response is received from the heat pump
- Element list discovery is not available

**Recommendation**: Use passive monitoring for reliable data access. Active requests may work for parameter writes but have not been verified.
