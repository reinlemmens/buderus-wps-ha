# Implementation Plan: CAN over USB Serial Connection

**Branch**: `001-can-usb-serial` | **Date**: 2025-10-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-can-usb-serial/spec.md`

## Summary

Implement Python library for CAN bus communication with Buderus WPS heat pumps via USBtin adapter. The library provides connection management, message transmission/reception, and value encoding/decoding using the SLCAN (Lawicel) protocol. Technical approach: pyserial for serial communication, dataclasses for type-safe message representation, context managers for resource cleanup, standard library `struct` module for value encoding.

## Technical Context

**Language/Version**: Python 3.9+ (constitution requirement)
**Primary Dependencies**: `pyserial` for USBtin communication; standard library only for all other functionality
**Storage**: N/A (stateless communication layer)
**Testing**: `pytest` with `unittest.mock` for serial port mocking
**Target Platform**: Cross-platform (Linux/macOS/Windows) via pyserial
**Project Type**: Single library project (library-first architecture per constitution)
**Performance Goals**: 100 messages/second without loss (SC-005), <2s connection establishment (SC-001), 99.9% reliability (SC-002)
**Constraints**: 5-second timeout for operations (FR-005), single-threaded usage (FR-010), no async (constitution)
**Scale/Scope**: Single device connection, foundational CAN communication layer for heat pump control

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Phase 0 Check (Before Research)

✅ **Principle I: Library-First Architecture**
- Feature is core library functionality
- No external dependencies beyond pyserial
- Independently testable without CLI or Home Assistant

✅ **Principle II: Hardware Abstraction & Protocol Fidelity**
- SLCAN protocol standard
- USBtin reference available
- Abstraction allows future adapter support

✅ **Principle III: Safety & Reliability**
- Input validation required (FR-012)
- Timeout mechanisms specified (FR-005)
- Error detection and reporting (FR-006, FR-007)
- Read-only mode supported (FR-009)

✅ **Principle IV: Test-First Development**
- All functional requirements have acceptance scenarios
- Test coverage mandatory per constitution
- Mock-based testing feasible (no hardware required)

✅ **Principle V: Protocol Documentation**
- SLCAN protocol well-documented
- FHEM reference available
- USBtin firmware documentation exists

**Result**: All gates PASS. Proceed to Phase 0 research.

### Phase 1 Check (After Design)

✅ **Principle I: Library-First Architecture**
- Design confirms library-only scope
- Single dependency (pyserial) maintained
- API supports both library and CLI use cases

✅ **Principle II: Hardware Abstraction & Protocol Fidelity**
- SLCAN protocol correctly implemented per research
- Message encoding follows CAN 2.0A/2.0B specs
- Adapter abstraction enables future extensions

✅ **Principle III: Safety & Reliability**
- CANMessage validation in `__post_init__`
- Connection state machine prevents invalid operations
- Error messages include diagnostic information
- Single-threaded guard implemented

✅ **Principle IV: Test-First Development**
- Test strategy defined in research.md
- Unit/integration/contract test layers planned
- Mock patterns established
- 100% coverage target for described functionality

✅ **Principle V: Protocol Documentation**
- research.md documents SLCAN protocol completely
- data-model.md defines all entities
- contracts/ specifies public API

**Result**: All gates PASS. Ready for Phase 2 (task generation).

## Project Structure

### Documentation (this feature)

```
specs/001-can-usb-serial/
├── spec.md              # Feature specification
├── plan.md              # This file (Phase 0+1 complete)
├── research.md          # Research findings (Phase 0 output) ✅
├── data-model.md        # Domain model (Phase 1 output) ✅
├── quickstart.md        # Developer guide (Phase 1 output) ✅
├── contracts/           # API contracts (Phase 1 output) ✅
│   ├── library_api.md   # Public API signatures
│   └── exceptions.md    # Exception hierarchy
└── tasks.md             # Implementation tasks (Phase 2 - use /speckit.tasks)
```

### Source Code (repository root)

```
buderus_wps/
├── __init__.py
├── can_message.py          # CANMessage dataclass with validation
├── value_encoder.py        # ValueEncoder for temp/int encoding
├── can_adapter.py          # USBtinAdapter serial communication
├── protocol.py             # CAN protocol layer (future)
├── device.py               # Device abstraction (future)
└── elements.py             # Parameter definitions (Feature 002)

tests/
├── unit/
│   ├── test_can_message.py       # Message validation tests
│   ├── test_value_encoder.py     # Encoding/decoding tests
│   └── test_usbtin_format.py     # SLCAN format tests
├── integration/
│   └── test_can_adapter_mock.py  # Adapter with mocked serial
└── contract/
    └── test_usbtin_protocol.py   # SLCAN protocol compliance
```

**Structure Decision**: Single project structure (Option 1) selected. Python library with layered architecture: core classes (can_message, value_encoder), adapter layer (can_adapter), and protocol layer (future). Tests mirror source structure with unit/integration/contract divisions per constitution Principle IV.

## Complexity Tracking

*No constitution violations.*

All requirements align with constitution principles:
- Single external dependency (pyserial) - minimal deps per Principle I
- Standard library for encoding - no unnecessary dependencies
- Synchronous blocking I/O - constitution explicitly states "async support is out of scope"
- Single-threaded model - simplicity per spec assumptions

---

## Phase 0: Research (COMPLETE)

**Status**: ✅ Complete
**Output**: [research.md](./research.md)

### Research Questions Resolved

1. **USBtin Protocol**: SLCAN (Lawicel) ASCII protocol documented
   - Initialization sequence: C, V, v, S4, O
   - Message format: t/T for standard/extended frames
   - 115200 baud, 8N1 serial configuration

2. **pyserial Best Practices**: Resource management and timeout patterns
   - Context managers + atexit + __del__ for cleanup
   - Polling with `in_waiting` for precise timeout control
   - Not thread-safe - defensive guards implemented

3. **CAN Message Format**: Dataclass with validation
   - Standard (11-bit) vs Extended (29-bit) IDs
   - 0-8 byte payloads
   - Big-endian encoding for multi-byte values

### Key Decisions

- **Protocol**: SLCAN over USB serial (industry standard)
- **Dependencies**: pyserial only (no python-can)
- **Message Structure**: Python dataclass with `__post_init__` validation
- **Resource Management**: Triple-layer cleanup (context manager + atexit + __del__)
- **Testing**: unittest.mock for serial port mocking

---

## Phase 1: Design & Contracts (COMPLETE)

**Status**: ✅ Complete
**Outputs**:
- [data-model.md](./data-model.md) - Domain entities and relationships
- [contracts/library_api.md](./contracts/library_api.md) - Public API
- [contracts/exceptions.md](./contracts/exceptions.md) - Exception hierarchy
- [quickstart.md](./quickstart.md) - Developer onboarding guide

### Domain Model

**Core Entities**:
1. **CANMessage**: Immutable message representation with validation
2. **Connection**: Serial port lifecycle management with state machine
3. **AdapterConfiguration**: Hardware-specific settings (USBtin)

**Value Objects**:
- **Temperature**: 3 encoding formats (temp, temp_byte, temp_uint)
- **Integer**: 1/2/4/8 byte encoding, signed/unsigned

**State Machine** (Connection):
```
CLOSED → CONNECTING → CONNECTED → CLOSING → CLOSED
                          ↓
                       ERROR → CLOSED
```

### API Contracts

**Public Classes**:
- `CANMessage`: Dataclass with to/from SLCAN format conversion
- `USBtinAdapter`: Connection management and frame transmission
- `ValueEncoder`: Static encoding/decoding utilities

**Exception Hierarchy**:
- `BuderusCANException` (base)
  - `ConnectionError` (DeviceNotFound, DevicePermission, DeviceDisconnected, DeviceInitialization)
  - `TimeoutError` (ReadTimeout, WriteTimeout)
  - `CANError` (CANBusOff, CANBitrate, CANFrame)
  - `ConcurrencyError`

### Implementation Patterns

From research and design:
- **Connection**: Context manager with atexit registration
- **Timeout**: Polling with 10ms intervals, 5s application-level timeout
- **Validation**: Eager validation in `__post_init__`
- **Thread Safety**: Defensive guard preventing concurrent operations
- **Error Messages**: Include diagnostic context and troubleshooting steps

---

## Phase 2: Task Generation (PENDING)

**Status**: ⏳ Pending
**Command**: `/speckit.tasks`
**Output**: `tasks.md` with dependency-ordered implementation tasks

**Expected Task Categories**:
1. Core message classes (CANMessage, ValueEncoder)
2. Serial adapter implementation (USBtinAdapter)
3. Unit tests for each class
4. Integration tests with mocked serial
5. Contract tests for SLCAN protocol

**Test Requirements** (per constitution):
- Unit tests: 100% coverage for all described functionality
- Integration tests: Mock-based serial communication
- Contract tests: SLCAN protocol compliance
- All acceptance scenarios from spec.md must have tests

---

## Agent Context Update

**Technology Stack Added**:
- Python 3.9+ (already in context)
- pyserial (USB serial communication library)
- pytest + unittest.mock (testing framework + mocking)
- dataclasses (Python standard library)
- struct (binary encoding, standard library)

**Domain Knowledge**:
- SLCAN (Lawicel) ASCII protocol
- CAN 2.0A (11-bit) and CAN 2.0B (29-bit extended) specifications
- USBtin hardware initialization sequence
- Buderus heat pump encoding formats

---

## Next Steps

1. Run `/speckit.tasks` to generate implementation tasks from this plan
2. Implement core classes following test-first discipline
3. Run tests to ensure 100% coverage per constitution
4. Integration testing with physical USBtin hardware (optional)
5. Update documentation with any implementation learnings

---

**Plan Status**: Phase 0 and Phase 1 COMPLETE. Ready for Phase 2 (task generation).
