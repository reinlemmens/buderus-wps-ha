# CLI Interface Contract

**Feature**: 005-can-parameter-access
**Component**: `buderus-wps` command-line tool
**Version**: 1.0.0
**Date**: 2025-10-24

This document defines the command-line interface contract for the parameter access CLI.

---

## Command Structure

### Base Command

```bash
buderus-wps [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGUMENTS]
```

### Global Options

Available for all commands (specified before COMMAND):

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--format` | | choice | `human` | Output format: `human` or `json` |
| `--timeout` | | int | `5` | Operation timeout in seconds |
| `--verbose` | `-v` | flag | false | Enable debug logging |
| `--log-dir` | | path | `./logs` | Directory for log files |
| `--version` | | flag | | Show version and exit |
| `--help` | `-h` | flag | | Show help and exit |

---

## Command: `get`

Read a parameter value from the device.

### Syntax

```bash
buderus-wps get PARAMETER [OPTIONS]
```

### Arguments

- `PARAMETER` (required): Parameter name (case-insensitive)

### Options

Inherits all global options.

### Output (Human Format)

```
DHW_TEMP_SETPOINT: 55.0°C
Range: 40.0 - 70.0°C
```

### Output (JSON Format)

```json
{
  "operation": "read",
  "parameter": "DHW_TEMP_SETPOINT",
  "value": 55.0,
  "unit": "°C",
  "metadata": {
    "min": 40.0,
    "max": 70.0,
    "writable": true,
    "type": "float"
  },
  "timestamp": "2025-10-24T10:30:45Z",
  "status": "success"
}
```

### Exit Codes

| Code | Condition |
|------|-----------|
| 0 | Success |
| 2 | Invalid arguments (argparse error) |
| 3 | Parameter not found |
| 6 | CAN bus connection error |
| 7 | Device timeout (5 seconds) |
| 8 | Device error response |

### Examples

```bash
# Read temperature setpoint
buderus-wps get DHW_TEMP_SETPOINT

# Case-insensitive parameter name
buderus-wps get dhw_temp_setpoint

# JSON output for scripting
buderus-wps get DHW_TEMP_SETPOINT --format json

# With custom timeout
buderus-wps get COMPRESSOR_STATUS --timeout 10

# With debug logging
buderus-wps get DHW_TEMP_SETPOINT --verbose
```

### Error Examples

```bash
# Parameter not found (exit 3)
$ buderus-wps get INVALID_PARAM
Error: Parameter 'INVALID_PARAM' does not exist.
Tip: Use 'buderus-wps list' to see available parameters.

# CAN bus disconnected (exit 6)
$ buderus-wps get DHW_TEMP_SETPOINT
Error: CAN bus connection failed.
Check: 1) USB adapter connected, 2) Device permissions, 3) Driver loaded.

# Device timeout (exit 7)
$ buderus-wps get DHW_TEMP_SETPOINT
Error: Device did not respond within 5s timeout.
Check: 1) Heat pump powered on, 2) CAN bus wiring, 3) Termination resistors.

# JSON error output
$ buderus-wps get INVALID_PARAM --format json
{
  "status": "error",
  "error_code": 3,
  "error_type": "PARAMETER_NOT_FOUND",
  "message": "Parameter 'INVALID_PARAM' does not exist",
  "parameter": "INVALID_PARAM",
  "timestamp": "2025-10-24T10:30:45Z"
}
```

---

## Command: `set`

Write a parameter value to the device.

### Syntax

```bash
buderus-wps set PARAMETER VALUE [OPTIONS]
```

### Arguments

- `PARAMETER` (required): Parameter name (case-insensitive)
- `VALUE` (required): New value to write

### Options

Inherits all global options.

### Output (Human Format)

```
✓ Successfully set DHW_TEMP_SETPOINT to 55.0°C
Previous value: 50.0°C
```

### Output (JSON Format)

```json
{
  "operation": "write",
  "parameter": "DHW_TEMP_SETPOINT",
  "value": 55.0,
  "previous_value": 50.0,
  "unit": "°C",
  "timestamp": "2025-10-24T10:30:45Z",
  "status": "success"
}
```

### Exit Codes

| Code | Condition |
|------|-----------|
| 0 | Success (value written and confirmed) |
| 2 | Invalid arguments |
| 3 | Parameter not found |
| 4 | Parameter is read-only |
| 5 | Value validation failed (outside range) |
| 6 | CAN bus connection error |
| 7 | Device timeout |
| 8 | Device error response |

### Examples

```bash
# Write temperature value
buderus-wps set DHW_TEMP_SETPOINT 55

# With decimal values
buderus-wps set HEATING_CURVE_SLOPE 1.5

# JSON output
buderus-wps set DHW_TEMP_SETPOINT 55 --format json

# With custom timeout
buderus-wps set DHW_TEMP_SETPOINT 55 --timeout 10
```

### Error Examples

```bash
# Read-only parameter (exit 4)
$ buderus-wps set COMPRESSOR_STATUS 1
Error: Parameter 'COMPRESSOR_STATUS' is read-only and cannot be modified.

# Validation error (exit 5)
$ buderus-wps set DHW_TEMP_SETPOINT 999
Error: Value 999.0 for 'DHW_TEMP_SETPOINT' is outside valid range [40.0 - 70.0].

# JSON validation error
$ buderus-wps set DHW_TEMP_SETPOINT 999 --format json
{
  "status": "error",
  "error_code": 5,
  "error_type": "VALIDATION_ERROR",
  "message": "Value 999.0 outside valid range [40.0 - 70.0]",
  "parameter": "DHW_TEMP_SETPOINT",
  "timestamp": "2025-10-24T10:30:45Z"
}
```

---

## Command: `list`

List all available parameters.

### Syntax

```bash
buderus-wps list [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--writable-only` | flag | false | Show only writable parameters |
| `--category` | string | | Filter by category (if available) |

Inherits all global options.

### Output (Human Format)

```
Available parameters (1789 total):

DHW_TEMP_SETPOINT
  Range: 40.0 - 70.0°C
  Writable: Yes
  Description: Domestic hot water temperature setpoint

COMPRESSOR_STATUS
  Range: 0 - 5
  Writable: No
  Description: Compressor operating status

...
```

### Output (JSON Format)

```json
{
  "operation": "list",
  "total_count": 1789,
  "parameters": [
    {
      "name": "DHW_TEMP_SETPOINT",
      "min": 40.0,
      "max": 70.0,
      "unit": "°C",
      "writable": true,
      "type": "float",
      "description": "Domestic hot water temperature setpoint"
    },
    {
      "name": "COMPRESSOR_STATUS",
      "min": 0,
      "max": 5,
      "unit": null,
      "writable": false,
      "type": "int",
      "description": "Compressor operating status"
    }
  ],
  "timestamp": "2025-10-24T10:30:45Z",
  "status": "success"
}
```

### Examples

```bash
# List all parameters
buderus-wps list

# List only writable parameters
buderus-wps list --writable-only

# JSON output
buderus-wps list --format json
```

---

## Environment Variables

Configuration can be provided via environment variables:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BUDERUS_WPS_DEVICE` | path | `/dev/ttyUSB0` | Serial device path |
| `BUDERUS_WPS_TIMEOUT` | int | `5` | Default timeout (seconds) |
| `BUDERUS_WPS_LOG_LEVEL` | string | `ERROR` | Log level (ERROR or DEBUG) |
| `BUDERUS_WPS_FORMAT` | string | `human` | Default output format |

**Precedence**: CLI arguments > environment variables > config file > defaults

### Example

```bash
export BUDERUS_WPS_TIMEOUT=10
export BUDERUS_WPS_FORMAT=json
buderus-wps get DHW_TEMP_SETPOINT
# Uses 10-second timeout and JSON format
```

---

## Configuration File

Optional configuration file: `~/.buderus-wps/config.ini`

```ini
[connection]
device = /dev/ttyUSB0
baudrate = 115200
timeout = 5

[logging]
level = ERROR
file = ~/.buderus-wps/logs/buderus-wps.log
max_size = 10485760  # 10MB

[behavior]
default_format = human
```

---

## Logging Behavior

### Default (ERROR-only)

```bash
$ buderus-wps get DHW_TEMP_SETPOINT
DHW_TEMP_SETPOINT: 55.0°C
```

No log output to console (only errors).

### Verbose Mode (DEBUG)

```bash
$ buderus-wps get DHW_TEMP_SETPOINT --verbose
DEBUG: Reading parameter: DHW_TEMP_SETPOINT
DEBUG: Parameter resolved: extid=0x31D011E9
DEBUG: CAN request: extid=0x31D011E9, data=[0x01]
DEBUG: CAN response: extid=0x31E011E9, data=[0x00, 0x2D], duration=234ms
DEBUG: Parameter DHW_TEMP_SETPOINT = 45°C (raw: [0x00, 0x2D])
DHW_TEMP_SETPOINT: 55.0°C
```

### Log Files

**Location**: `./logs/buderus_wps.log` (by default)

**Rotation**: 10MB per file, 5 backups (50MB total)

**Format**:
```
2025-10-24 14:23:45 - buderus_wps.can_interface - DEBUG - read_parameter:89 - Reading parameter: DHW_TEMP_SETPOINT
2025-10-24 14:23:45 - buderus_wps.parameters - DEBUG - get_parameter_config:34 - Parameter resolved: extid=0x31D011E9
2025-10-24 14:23:46 - buderus_wps.can_interface - ERROR - CAN bus connection failed
```

---

## Help Output

### Main Help

```bash
$ buderus-wps --help
usage: buderus-wps [-h] [--format {human,json}] [--timeout SECONDS]
                   [--verbose] [--log-dir PATH] [--version]
                   {get,set,list} ...

Buderus WPS heat pump control CLI

positional arguments:
  {get,set,list}        Command to execute
    get                 Read a parameter value
    set                 Write a parameter value
    list                List available parameters

optional arguments:
  -h, --help            show this help message and exit
  --format {human,json}
                        Output format (default: human-readable)
  --timeout SECONDS     Operation timeout in seconds (default: 5)
  --verbose, -v         Enable verbose debug logging
  --log-dir PATH        Directory for log files (default: ./logs)
  --version             show program's version number and exit

Examples:
  buderus-wps get DHW_TEMP_SETPOINT
  buderus-wps set DHW_TEMP_SETPOINT 55
  buderus-wps get COMPRESSOR_ALARM --format json
  buderus-wps list --writable-only
```

### Command-Specific Help

```bash
$ buderus-wps get --help
usage: buderus-wps get [-h] [--format {human,json}] [--timeout SECONDS]
                       [--verbose]
                       PARAMETER

Read a parameter value from the device

positional arguments:
  PARAMETER             Parameter name (case-insensitive)

optional arguments:
  -h, --help            show this help message and exit
  --format {human,json}
                        Output format (default: human-readable)
  --timeout SECONDS     Operation timeout in seconds (default: 5)
  --verbose, -v         Enable verbose debug logging
```

---

## Shell Integration

### Bash Completion (Future Enhancement)

```bash
# Install completion
buderus-wps --install-completion bash

# Tab completion
$ buderus-wps get DHW<TAB>
DHW_TEMP_SETPOINT  DHW_STATUS  DHW_PUMP_STATE
```

**Note**: Shell completion is out of scope for Phase 1 but shown here for future reference.

---

## Scripting Examples

### Check Parameter Value in Bash

```bash
#!/bin/bash
# Check if DHW temperature is above threshold

TEMP=$(buderus-wps get DHW_TEMP_SETPOINT --format json | jq -r '.value')

if (( $(echo "$TEMP > 60" | bc -l) )); then
    echo "Temperature too high: ${TEMP}°C"
    exit 1
fi

echo "Temperature OK: ${TEMP}°C"
exit 0
```

### Set Parameter with Error Handling

```bash
#!/bin/bash
# Set parameter with error handling

if buderus-wps set DHW_TEMP_SETPOINT 55 --format json > /tmp/result.json; then
    NEW_VALUE=$(jq -r '.value' < /tmp/result.json)
    echo "Successfully set to ${NEW_VALUE}"
    exit 0
else
    EXIT_CODE=$?
    ERROR_MSG=$(jq -r '.message' < /tmp/result.json 2>/dev/null || echo "Unknown error")
    echo "Failed to set parameter: ${ERROR_MSG} (exit code ${EXIT_CODE})"
    exit $EXIT_CODE
fi
```

### Monitor Parameter in Loop

```bash
#!/bin/bash
# Monitor parameter every 10 seconds

while true; do
    buderus-wps get COMPRESSOR_STATUS --format json | \
        jq -r '"\(.timestamp): \(.parameter) = \(.value)"'
    sleep 10
done
```

---

## Contract Testing

CLI interface contracts verified by:
- Subprocess tests: Execute actual CLI commands
- Exit code verification: Validate all error codes
- Output parsing: Validate human and JSON formats
- Argument validation: Test invalid argument combinations
- Environment variable tests: Verify configuration precedence

See: `/tests/integration/test_cli_interface.py`

---

## Backward Compatibility

**Stability Guarantees**:
- Command names (`get`, `set`, `list`) will not change
- Global option names will not change
- Exit codes will remain stable (no re-mapping)
- JSON output schema will be versioned and backward-compatible
- Human output format may change (not guaranteed stable)

**Deprecation Policy**:
- Deprecated options will show warnings for 1 minor version
- Removed in next major version
- Deprecation notices included in `--help` output

---

## Contract Status

✅ **STABLE** - Ready for implementation in Phase 2
