# Feature Specification: Mock CAN Testing Infrastructure

**Feature Branch**: `017-mock-can-testing`
**Created**: 2025-12-18
**Status**: Draft
**Input**: User description: "Create a dev container testing infrastructure with mock CAN adapter that supports: 1) Recording actual CAN traffic from real hardware to JSON files, 2) Replaying recorded traffic with realistic timing, 3) Generating synthetic CAN broadcasts for test scenarios. The mock should replace USBtinAdapter at the adapter layer (not virtual serial port). Primary use case is testing the Home Assistant integration in dev container without physical hardware. Should enable reproducing and testing the sensor caching bug fix where missing broadcast sensors show 'Unknown'."

## User Scenarios & Testing

### User Story 1 - Recording Real CAN Traffic (Priority: P1)

As a developer, I want to record actual CAN bus traffic from the physical heat pump to JSON files, so that I can replay realistic device behavior in tests without needing hardware access.

**Why this priority**: Recording real traffic is the foundation for realistic testing. Without authentic data, we cannot validate that our integration handles real-world device behavior correctly. This enables all other testing scenarios.

**Independent Test**: Can be fully tested by connecting to real hardware, recording for a specified duration, and verifying the JSON output contains timestamped CAN frames with correct format and metadata.

**Acceptance Scenarios**:

1. **Given** a connection to real heat pump hardware, **When** I start recording for 60 seconds, **Then** a JSON file is created with all CAN frames timestamped and formatted correctly
2. **Given** CAN traffic is being received, **When** frames contain temperature broadcasts, **Then** the recording includes frame metadata (CAN ID, data bytes, timestamp) and human-readable descriptions
3. **Given** I complete a recording session, **When** I inspect the JSON file, **Then** I see metadata about the recording (duration, frame count, timestamp, hardware info)
4. **Given** multiple recording sessions, **When** I save recordings with different names, **Then** I can organize recordings by scenario (normal operation, startup, cycling, etc.)

---

### User Story 2 - Replaying Recorded Traffic in Dev Container (Priority: P1)

As a developer, I want to replay recorded CAN traffic in my dev container Home Assistant instance, so that I can test the integration with realistic device behavior without physical hardware.

**Why this priority**: Replay capability is essential for dev container testing. It allows developers to work on the integration without physical device access, speeds up iteration cycles, and enables reproducible tests.

**Independent Test**: Can be fully tested by configuring the dev container to use a replay file, starting Home Assistant, and verifying that sensors update with values from the recording.

**Acceptance Scenarios**:

1. **Given** a recorded CAN traffic file, **When** I configure the dev container to replay it, **Then** the Home Assistant integration starts successfully and sensors show values from the recording
2. **Given** replay is active, **When** frames are played back, **Then** they maintain realistic timing based on timestamps in the recording
3. **Given** a recording reaches the end, **When** configured to loop, **Then** playback restarts from the beginning seamlessly
4. **Given** sensors are displaying replayed data, **When** I check entity attributes, **Then** staleness indicators reflect the replay state appropriately

---

### User Story 3 - Generating Synthetic Test Scenarios (Priority: P2)

As a developer, I want to generate synthetic CAN traffic for specific test scenarios, so that I can reproduce edge cases and bugs that are difficult to trigger with real hardware.

**Why this priority**: Synthetic generation enables testing scenarios impossible to reliably trigger on real hardware, such as partial broadcast loss, missing sensors, rapid temperature changes, or device errors. Critical for regression testing and bug reproduction.

**Independent Test**: Can be fully tested by configuring synthetic mode with specific parameters (e.g., "skip DHW sensor every 3rd broadcast"), running tests, and verifying the expected scenario occurs.

**Acceptance Scenarios**:

1. **Given** synthetic mode is configured, **When** I specify temperature values for sensors, **Then** broadcasts are generated with those values at realistic intervals
2. **Given** I want to reproduce the "Unknown" sensor bug, **When** I configure the generator to randomly omit specific sensors from broadcasts, **Then** the integration behavior matches the real bug scenario
3. **Given** synthetic broadcasts are running, **When** I modify temperature values during operation, **Then** sensors reflect the new values after the next broadcast cycle
4. **Given** a test scenario requires specific timing, **When** I configure broadcast intervals, **Then** frames are generated at the specified rate

---

### User Story 4 - Test Fixture Integration (Priority: P2)

As a developer writing integration tests, I want to use mock CAN adapters as pytest fixtures, so that I can easily test coordinator and entity behavior without hardware dependencies.

**Why this priority**: Fixture integration makes the mock infrastructure accessible to all tests. This is essential for enabling comprehensive test coverage without hardware, but is secondary to the core record/replay functionality.

**Independent Test**: Can be fully tested by writing a pytest test that uses the mock fixtures, runs the test suite, and verifying tests pass without hardware.

**Acceptance Scenarios**:

1. **Given** I'm writing an integration test, **When** I use the replay fixture with a recording file, **Then** the test receives a configured mock adapter with the recording loaded
2. **Given** I'm writing a unit test, **When** I use the synthetic fixture, **Then** the test receives a mock adapter that generates data based on test parameters
3. **Given** multiple tests need different recordings, **When** I parametrize tests with different recording files, **Then** each test runs with its specified recording
4. **Given** a test completes, **When** the fixture tears down, **Then** resources are properly cleaned up

---

### Edge Cases

- What happens when a recording file is corrupted or has invalid JSON format?
- How does the system handle replay when the recording is shorter than the test duration?
- What happens if synthetic mode is configured with invalid temperature ranges or parameters?
- How does the mock adapter behave when configured for both replay and synthetic modes simultaneously?
- What happens when a recording contains CAN frames with unknown IDs not in the parameter mapping?
- How does timing work when replay speed differs from real-time (faster/slower playback)?
- What happens when recording is started but no CAN traffic is received (device disconnected)?

## Requirements

### Functional Requirements

- **FR-001**: System MUST support recording CAN traffic from physical hardware to JSON files with frame timestamps, CAN IDs, data bytes, and metadata
- **FR-002**: Recording output MUST include session metadata (duration, frame count, recording timestamp, device port, and user-provided description)
- **FR-003**: System MUST support replaying recorded CAN traffic files with timing based on original timestamps
- **FR-004**: Replay engine MUST support looping (restart from beginning when recording ends)
- **FR-005**: System MUST support generating synthetic CAN broadcasts with configurable sensor values and broadcast intervals
- **FR-006**: Synthetic generator MUST use the same CAN ID encoding and data format as real hardware
- **FR-007**: Mock adapter MUST replace USBtinAdapter at the adapter layer without modifying the adapter interface
- **FR-008**: System MUST support configuration via environment variables or configuration files to select recording/replay/synthetic mode
- **FR-009**: Mock infrastructure MUST integrate with pytest as fixtures for use in integration tests
- **FR-010**: Fixtures MUST support parametrization to specify different recordings or synthetic configurations per test
- **FR-011**: System MUST provide capability to reproduce the partial broadcast loss scenario (missing sensors causing "Unknown" states)
- **FR-012**: Recordings MUST be organized in a standard directory structure with descriptive names
- **FR-013**: Mock adapter MUST maintain realistic CAN broadcast timing patterns matching observed hardware behavior

### Key Entities

- **Recording Session**: Represents a captured session of CAN traffic with metadata (timestamp, duration, frame count, description, hardware info) and an ordered sequence of frames
- **CAN Frame Record**: Individual CAN frame with timestamp (relative to session start), CAN ID, data length, data bytes, and optional human-readable description
- **Mock Adapter**: Replacement for USBtinAdapter that provides recorded or synthetic CAN traffic instead of hardware communication
- **Replay Engine**: Component that reads recording files and plays back frames with appropriate timing
- **Synthetic Generator**: Component that generates CAN frames programmatically based on configuration parameters

## Success Criteria

### Measurable Outcomes

- **SC-001**: Developer can record 60 seconds of CAN traffic from real hardware and save to JSON format in under 90 seconds total time
- **SC-002**: Developer can start Home Assistant dev container with replayed traffic and see sensor values update within 30 seconds
- **SC-003**: Replayed traffic maintains timing accuracy within ±10% of original broadcast intervals
- **SC-004**: Developer can reproduce the "Unknown" sensor bug scenario using synthetic mode within 5 minutes of configuration
- **SC-005**: Integration tests using mock fixtures run successfully without requiring physical hardware
- **SC-006**: Test suite execution time decreases by at least 80% when using mocks compared to hardware-in-loop tests
- **SC-007**: Recordings are human-readable and can be inspected/debugged without specialized tools
- **SC-008**: Developer can create and save multiple recording scenarios (normal, startup, cycling) for different test purposes

## Assumptions

- Developers have access to physical hardware for initial recording sessions
- JSON format is acceptable for recording storage (not requiring binary formats)
- 100% timing precision is not critical - ±10% variance is acceptable for testing
- Standard pytest fixtures are the preferred integration pattern for tests
- Environment variables or config files are acceptable for mode selection
- The USBtinAdapter interface is stable and will not change during implementation
- Recorded files will be committed to the repository for shared use across the team

## Dependencies

- Existing USBtinAdapter interface and implementation (must not be modified)
- Home Assistant dev container setup (`.devcontainer/` configuration)
- Pytest testing infrastructure (existing `tests/conftest.py` fixtures)
- Access to physical heat pump hardware for recording sessions
- Existing CAN protocol implementation (`buderus_wps/can_message.py`, `buderus_wps/broadcast_monitor.py`)

## Out of Scope

- Virtual serial port emulation (explicitly excluded per user requirement)
- Real-time CAN traffic modification or injection during recording
- Network-based CAN traffic streaming or remote recording
- CAN traffic encryption or security features
- GUI or web interface for managing recordings
- Automatic test generation from recordings
- Performance profiling or optimization beyond basic timing requirements
- Support for non-USBtin CAN adapters
