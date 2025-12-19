# Research: Sensor Configuration and Installation Settings

**Feature**: 009-sensor-config
**Date**: 2024-12-02

## Configuration File Format

### Decision: YAML

**Rationale**:
- Human-readable and editable with any text editor
- Supports comments (unlike JSON) - critical for documenting sensor mappings
- Python has mature support via PyYAML library
- Widely used in similar projects (Home Assistant uses YAML extensively)
- Supports complex nested structures cleanly

**Alternatives Considered**:
- **JSON**: No comments, less readable for humans, requires escaping
- **TOML**: Good but less familiar to users, PyYAML more mature
- **INI**: Too flat for nested structures (circuits, sensors)

## Configuration File Location

### Decision: Hierarchical search with override

**Search Order**:
1. Explicit path via `--config` CLI flag or `BUDERUS_WPS_CONFIG` env var
2. `./buderus-wps.yaml` (current working directory)
3. `~/.config/buderus-wps/config.yaml` (XDG standard)
4. Built-in defaults (no file needed)

**Rationale**:
- Follows XDG Base Directory Specification for Linux
- Local file allows per-project configuration
- Environment variable supports containerized deployments
- Graceful fallback ensures system always works

**Alternatives Considered**:
- Single fixed location: Less flexible for different deployment scenarios
- Only environment variable: Harder for interactive users

## Default Sensor Mappings

### Decision: Extract from current TUI implementation

The current hardcoded mappings in `app.py` represent verified working values:

```python
TEMP_BROADCAST_MAP = {
    (0x0402, 38): "outdoor",      # GT2 - Outdoor temperature
    (0x0060, 58): "dhw",          # GT3 - DHW tank temperature
    (0x0061, 58): "dhw",          # GT3 - DHW (alternative)
    (0x0062, 58): "dhw",          # GT3 - DHW (alternative)
    (0x0063, 58): "dhw",          # GT3 - DHW (alternative)
    (0x0060, 12): "brine_in",     # GT1 - Brine inlet
    (0x0061, 12): "brine_in",     # GT1 - Brine inlet (alternative)
    (0x0063, 12): "brine_in",     # GT1 - Brine inlet (alternative)
    (0x0270, 1): "supply",        # GT8 - Supply/flow temperature
    (0x0270, 7): "supply",        # GT8 - Supply (alternative)
    (0x0270, 0): "return_temp",   # GT9 - Return temperature
}
```

**Rationale**:
- These mappings were verified against actual CAN bus traffic on 2024-12-02
- Multiple sources for same sensor provide resilience to intermittent broadcasts
- Sensor names match GT sensor naming convention from FHEM

## Validation Strategy

### Decision: Warn and fallback, don't fail

**Rationale**:
- Heat pump monitoring should not crash due to config typos
- Invalid entries are logged with warnings
- System continues with valid entries + defaults
- Follows constitution principle III (Safety & Reliability)

**Validation Rules**:
1. Sensor names must be in known set: `outdoor`, `supply`, `return_temp`, `dhw`, `brine_in`
2. Circuit numbers must be 1-4
3. CAN addresses must be valid integers (base: 0x0000-0xFFFF, idx: 0-2047)
4. Unknown keys are logged and ignored (forward compatibility)

## PyYAML Dependency

### Decision: Add PyYAML as required dependency

**Rationale**:
- PyYAML is stable, widely used, well-maintained
- Already a transitive dependency in many Python environments
- Small footprint (~200KB)
- Safe loading via `yaml.safe_load()` prevents code execution

**Security Note**:
- MUST use `yaml.safe_load()` not `yaml.load()` to prevent arbitrary code execution
- Configuration files contain only data, never executable code

## Compressor Status Detection

### Verified Parameters (2024-12-02)

Testing was performed while DHW charging was active. The compressor switched off at 13:20 after reaching 53°C DHW target temperature.

| Parameter | Idx | Value (Running) | Value (Stopped) | Purpose |
|-----------|-----|-----------------|-----------------|---------|
| **COMPRESSOR_REAL_FREQUENCY** | 278 | >0 (Hz) | 0 | **Primary running indicator** |
| **COMPRESSOR_DHW_REQUEST** | 261 | >0 | 0 or >0 | DHW mode active |
| **COMPRESSOR_HEATING_REQUEST** | 273 | >0 | 0 | Heating mode active |
| **COMPRESSOR_STATE** | 294 | 15 | 15 | State code (not boolean) |
| **HW_COMPRESSOR_WORKING_FREQ** | 955 | >0 | 0 | Working frequency |

### Key Findings

1. **`COMPRESSOR_REAL_FREQUENCY > 0`** is the reliable indicator for "compressor is running"
   - Returns actual frequency in Hz when running
   - Returns 0 when stopped

2. **`COMPRESSOR_DHW_REQUEST`** indicates DHW mode is active
   - Non-zero value means DHW charging requested
   - Compressor may cycle on/off within DHW mode

3. **`COMPRESSOR_HEATING_REQUEST`** indicates heating mode is active
   - Similar to DHW request but for space heating

4. **`COMPRESSOR_STATE`** returns a state code, not a boolean
   - Value 15 (0x0F) observed during idle DHW mode
   - Should not be used for simple running/stopped detection

### Usage in Code

```python
# Check if compressor is running
frequency = client.read_parameter("COMPRESSOR_REAL_FREQUENCY")
running = int(frequency.get("decoded", 0)) > 0

# Determine mode
dhw = client.read_parameter("COMPRESSOR_DHW_REQUEST")
heating = client.read_parameter("COMPRESSOR_HEATING_REQUEST")

if int(dhw.get("decoded", 0)) > 0:
    mode = "DHW"
elif int(heating.get("decoded", 0)) > 0:
    mode = "Heating"
else:
    mode = "Idle"
```

### Monitoring Tool

A monitoring script is available at `monitor_compressor.py`:

```bash
python monitor_compressor.py --port /dev/ttyACM0
```

This displays real-time compressor status with 2-second updates.
