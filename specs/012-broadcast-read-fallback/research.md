# Research: CLI Broadcast Read Fallback

**Feature**: 012-broadcast-read-fallback
**Date**: 2025-12-06

## Problem Analysis

### Current Behavior

The CLI `read` command sends RTR (Remote Transmission Request) CAN frames to the heat pump and expects data responses. For temperature parameters like `GT2_TEMP`, the heat pump returns only 1 byte (0x01) instead of the expected 2-byte temperature value, resulting in a displayed value of 0.1°C.

**Evidence from testing** (rpiheatpump.local):
```
$ wps-cli read GT2_TEMP
GT2_TEMP = 0.1°C  (raw=0x01, idx=672)  # WRONG - should be 10.5°C

$ wps-cli monitor --temps-only --duration 5
0x00030060  0x0060   12     OUTDOOR_TEMP_C0          2     0x0069       10.5°C  # CORRECT
```

### Root Cause

The heat pump CAN protocol has two data delivery mechanisms:
1. **RTR Request/Response**: Direct queries that sometimes return incomplete data
2. **Broadcast**: Periodic broadcasts of sensor values with complete data

Temperature sensors are primarily delivered via broadcast, not RTR response. The 1-byte RTR response appears to be an acknowledgment rather than actual data.

## Technical Decisions

### Decision 1: Mapping Strategy

**Problem**: Need to find broadcast data for a given parameter name (e.g., GT2_TEMP → OUTDOOR_TEMP_C0)

**Options Evaluated**:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Static mapping dictionary | Fast lookup, explicit | Manual maintenance |
| B | Name matching heuristics | Auto-discovery | Unreliable, complex |
| C | Runtime learning | Adaptive | Requires training period |

**Decision**: Option A - Static mapping dictionary `PARAM_TO_BROADCAST_MAP`

**Rationale**:
- The number of temperature parameters is finite and well-known
- Explicit mapping ensures correctness
- Easy to extend when new parameters are identified

### Decision 2: Invalid Response Detection

**Problem**: How to detect when RTR response is invalid and fallback is needed

**Options Evaluated**:

| Option | Detection Method | Pros | Cons |
|--------|-----------------|------|------|
| A | Response length == 1 byte | Simple | May miss some cases |
| B | Value == 0.1°C for temp params | Semantic | 0.1°C could be valid in extreme cold |
| C | Length == 1 AND format == "tem" | Combined | More robust |

**Decision**: Option C - Check response length AND parameter format

**Implementation**:
```python
def is_invalid_rtr_response(param, raw_data):
    # Temperature params should return 2+ bytes
    if param.format == "tem" and len(raw_data) == 1:
        return True
    return False
```

### Decision 3: Broadcast Collection Duration

**Problem**: How long to wait for broadcast data

**Analysis**:
- Heat pump broadcasts at ~1-2 second intervals
- Some parameters broadcast less frequently
- User experience requires reasonable response time

**Options Evaluated**:

| Duration | Coverage | UX | Recommendation |
|----------|----------|-----|----------------|
| 3 seconds | ~50% | Good | Risky |
| 5 seconds | ~80% | Acceptable | Default |
| 10 seconds | ~95% | Poor | Optional via --duration |

**Decision**: 5 seconds default, configurable via `--duration`

### Decision 4: CLI Flag Design

**Problem**: How to expose broadcast read functionality

**Design**:
```
wps-cli read PARAM [--broadcast] [--duration SECS] [--no-fallback] [--json]
```

| Flag | Purpose | Default |
|------|---------|---------|
| `--broadcast` | Force broadcast mode (skip RTR) | Off |
| `--duration` | Broadcast collection time | 5.0 seconds |
| `--no-fallback` | Disable auto-fallback | Off (fallback enabled) |
| `--json` | Existing flag, add source field | Off |

## Existing Code Analysis

### BroadcastMonitor (buderus_wps/broadcast_monitor.py)

Key components available for reuse:
- `BroadcastCache`: Stores readings by CAN ID
- `BroadcastReading`: Contains temperature, raw_value, timestamp
- `KNOWN_BROADCASTS`: Maps (base, idx) → (name, format)
- `collect(duration)`: Collects broadcast traffic for specified time

### Parameter Registry (buderus_wps/parameter_registry.py)

- `Parameter.format`: "tem" for temperature parameters
- `Parameter.text`: Parameter name (e.g., "GT2_TEMP")

### HeatPumpClient (buderus_wps/heat_pump.py)

- `read_value()`: Current RTR-based read
- `_decode_value()`: Decodes raw bytes to typed value

## Parameter-to-Broadcast Mapping

Based on observed broadcasts and FHEM reference:

| Parameter Name | Broadcast Base | Broadcast Idx | Broadcast Name |
|---------------|----------------|---------------|----------------|
| GT2_TEMP | 0x0060 | 12 | OUTDOOR_TEMP_C0 |
| GT3_TEMP | 0x0060 | 58 | DHW_TEMP_ACTUAL |
| GT8_TEMP | TBD | TBD | (needs investigation) |

**Note**: Full mapping to be completed during implementation based on hardware testing.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Parameter not in broadcast | Read fails | Clear error message, suggest manual monitor |
| Timing misses broadcast | No data captured | Configurable duration, retry guidance |
| Mapping incorrect | Wrong value returned | Hardware verification before release |

## References

- [FHEM 26_KM273v018.pm](../../fhem/26_KM273v018.pm) - Reference implementation
- [broadcast_monitor.py](../../buderus_wps/broadcast_monitor.py) - Existing broadcast handling
- Testing session on rpiheatpump.local - 2025-12-06
