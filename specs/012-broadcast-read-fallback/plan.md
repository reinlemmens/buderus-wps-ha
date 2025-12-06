# Implementation Plan: CLI Broadcast Read Fallback

**Branch**: `012-broadcast-read-fallback` | **Date**: 2025-12-06 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/012-broadcast-read-fallback/spec.md`

## Summary

Enhance the CLI `read` command to source temperature data from CAN bus broadcasts when RTR requests return invalid 1-byte responses. Add `--broadcast` flag for explicit broadcast mode, `--duration` for configurable collection time, and automatic fallback when RTR returns 0.1°C for temperature parameters. Output includes source indication (RTR vs broadcast).

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: pyserial (for USBtin), existing `BroadcastMonitor` class
**Storage**: N/A (stateless read operations)
**Testing**: pytest with unit/integration/contract/acceptance structure
**Target Platform**: Linux on Raspberry Pi (primary), cross-platform compatible
**Project Type**: Single (library + CLI packages)
**Performance Goals**: Read command completes within duration + 2 seconds overhead
**Constraints**: Must work without physical hardware in tests (mock-based)
**Scale/Scope**: Enhancement to existing CLI read command

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Library-First Architecture | PASS | Enhances CLI using existing BroadcastMonitor library class |
| Hardware Abstraction | PASS | Uses existing CAN adapter abstraction |
| Safety & Reliability | PASS | Read-only operation, no write impact |
| Comprehensive Test Coverage | REQUIRED | Must add tests for all acceptance scenarios |
| Protocol Documentation | PASS | Broadcast mappings already documented in KNOWN_BROADCASTS |
| CLI Design Principles | PASS | Follows verb-noun structure, supports JSON output |

**Pre-Phase 0 Gate**: PASS - All applicable gates satisfied, test coverage gate enforced during implementation.

## Project Structure

### Documentation (this feature)

```
specs/012-broadcast-read-fallback/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - internal CLI, no external API)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```
buderus_wps/
├── broadcast_monitor.py   # EXISTING - BroadcastMonitor, KNOWN_BROADCASTS, BroadcastCache
├── heat_pump.py           # EXISTING - HeatPumpClient with read_value()
└── parameter_registry.py  # EXISTING - Parameter definitions with format="tem"

buderus_wps_cli/
└── main.py               # MODIFY - Add broadcast flags, fallback logic to cmd_read()

tests/
├── unit/
│   ├── test_broadcast_monitor.py  # EXISTING - May need new tests
│   └── test_cli.py               # MODIFY - Add broadcast read tests
├── integration/
│   └── test_broadcast_read.py    # NEW - Integration tests for fallback behavior
├── contract/
│   └── test_broadcast_read_contract.py  # NEW - Contract tests for output format
└── acceptance/
    └── test_broadcast_read_acceptance.py  # NEW - Acceptance tests for user stories
```

**Structure Decision**: Single project structure following existing conventions. Modifications to `buderus_wps_cli/main.py` for CLI changes, no library changes needed (uses existing `BroadcastMonitor`).

## Complexity Tracking

*No constitution violations - feature uses existing patterns and components.*

---

## Phase 0: Research

### Technical Decisions

**Decision 1: Broadcast-to-Parameter Mapping Strategy**
- **Decision**: Extend existing `KNOWN_BROADCASTS` mapping to support reverse lookup (parameter name → broadcast base/idx)
- **Rationale**: The current mapping goes from (base, idx) → name, but we need name → (base, idx) for the read command to find the right broadcast
- **Alternatives Considered**:
  - Create separate reverse dictionary: Rejected (data duplication, maintenance burden)
  - Search KNOWN_BROADCASTS on each lookup: Acceptable for small dictionary size

**Decision 2: Invalid RTR Response Detection**
- **Decision**: Detect invalid response when temperature parameter returns raw single byte (0x01) resulting in 0.1°C
- **Rationale**: Valid temperature readings are 2 bytes (10ths of degree). Single-byte response (0x01 = 0.1°C) indicates protocol failure.
- **Alternatives Considered**:
  - Check response length only: Partial (doesn't account for valid 1-byte non-temp params)
  - Check both length and value for temp params: Chosen approach

**Decision 3: Broadcast Collection Integration**
- **Decision**: Reuse existing `BroadcastMonitor.collect()` method within `cmd_read()`
- **Rationale**: The monitor already handles CAN frame parsing, caching, and temperature decoding
- **Alternatives Considered**:
  - Create new broadcast reader: Rejected (code duplication)
  - Modify BroadcastMonitor: Not needed (existing API sufficient)

**Decision 4: Parameter-to-Broadcast Name Mapping**
- **Decision**: Create a mapping from standard parameter names (GT2_TEMP, etc.) to their broadcast equivalents (OUTDOOR_TEMP_C0, etc.)
- **Rationale**: The KNOWN_BROADCASTS uses different names than the parameter registry. Need explicit mapping.
- **Implementation**: Add `PARAM_TO_BROADCAST_MAP` dictionary in broadcast_monitor.py

**Decision 5: Default Broadcast Duration**
- **Decision**: Use 5 seconds as default broadcast collection duration
- **Rationale**: Heat pump broadcasts occur at regular intervals (~1-2 second cycles). 5 seconds ensures at least 2-3 broadcast cycles captured.
- **Alternatives Considered**:
  - 10 seconds (monitor default): Too long for simple reads
  - 3 seconds: May miss broadcasts depending on timing

### Unknowns Resolved

1. **Q: How to map parameter names to broadcast entries?**
   - A: Create explicit `PARAM_TO_BROADCAST_MAP` dictionary mapping parameter names to (base, idx) tuples

2. **Q: Which parameters support broadcast fallback?**
   - A: Temperature parameters with format="tem" that have entries in KNOWN_BROADCASTS mapping

3. **Q: How to handle parameters not in broadcast mapping?**
   - A: Return error "Parameter not available via broadcast" if --broadcast specified, or return RTR result with warning if fallback fails

---

## Phase 1: Design

### Data Model

See [data-model.md](data-model.md) for detailed entity definitions.

Key entities:
- **ReadResult**: Extended to include `source` field ("rtr" or "broadcast")
- **BroadcastMapping**: Mapping from parameter name to broadcast (base, idx)

### Contracts

No external API contracts needed - this is an internal CLI enhancement. The output format contract is defined by existing CLI patterns:

**Text Output Format**:
```
PARAM_NAME = VALUE  (raw=0xXX, idx=NNN, source=SOURCE)
```

**JSON Output Format**:
```json
{
  "name": "PARAM_NAME",
  "idx": 123,
  "raw": "xxxx",
  "decoded": 12.3,
  "source": "rtr|broadcast"
}
```

### Quickstart

See [quickstart.md](quickstart.md) for implementation guide.

---

## Post-Design Constitution Re-Check

| Gate | Status | Notes |
|------|--------|-------|
| Library-First Architecture | PASS | CLI uses library's BroadcastMonitor |
| Comprehensive Test Coverage | PENDING | Tests defined in structure, must be implemented |
| CLI Design Principles | PASS | --broadcast, --duration, --no-fallback flags follow conventions |

**Post-Phase 1 Gate**: PASS - Ready for task generation.
