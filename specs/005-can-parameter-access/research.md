# Research: CAN Bus Parameter Read/Write Access

**Feature**: 005-can-parameter-access
**Date**: 2025-10-24
**Status**: Complete

This document consolidates research findings for implementing parameter read/write operations with human-readable names.

---

## 1. CLI Command Structure

### Decision: Use `buderus-wps get PARAMETER` and `buderus-wps set PARAMETER VALUE`

**Rationale**:
- **Verb clarity**: `get`/`set` are universally understood in technical contexts
- **Constitution compliance**: Follows required verb-noun structure
- **Industry precedent**: Aligns with git, etcd, Docker patterns
- **Semantic precision**: `get` implies retrieval, `set` implies modification

**Command Structure**:
```bash
# Read operations
buderus-wps get DHW_TEMP_SETPOINT
buderus-wps get COMPRESSOR_ALARM --format json

# Write operations
buderus-wps set DHW_TEMP_SETPOINT 55
buderus-wps set HEATING_CURVE_SLOPE 1.5 --timeout 10
```

**Global Options** (before subcommand):
- `--format {human|json}`: Output format (default: human)
- `--timeout SECONDS`: Operation timeout (default: 5)
- `--verbose, -v`: Enable debug logging
- `--log-dir PATH`: Log file directory (default: ./logs)
- `--version`: Show version

**Alternatives Considered**:
- `read`/`write`: More explicit but longer, less idiomatic
- `param get`/`param set`: Adds namespace but verbose
- `show`/`update`: Less precise semantics

---

## 2. Error Handling & Exit Codes

### Decision: Use Standard Unix Exit Codes with Domain-Specific Extensions

**Exit Code Mapping**:
```python
class ExitCode(IntEnum):
    SUCCESS = 0              # Successful operation
    GENERAL_ERROR = 1        # Generic error
    USAGE_ERROR = 2          # Invalid arguments (argparse default)
    PARAMETER_NOT_FOUND = 3  # Unknown parameter name
    PARAMETER_READ_ONLY = 4  # Write to read-only parameter
    VALIDATION_ERROR = 5     # Value outside valid range
    CONNECTION_ERROR = 6     # CAN bus not connected
    TIMEOUT_ERROR = 7        # Device timeout (5 seconds)
    DEVICE_ERROR = 8         # Device returned error
```

**Rationale**:
- **POSIX compliance**: Uses standard 0-127 range
- **Scriptability**: Scripts can distinguish error types
- **argparse alignment**: Preserves code 2 for usage errors
- **Clarity**: Each error category has distinct code

**Error Message Best Practices**:
```python
# Include context and actionable suggestions
"Parameter 'INVALID_NAME' does not exist.\n"
"Tip: Use 'buderus-wps list' to see available parameters."

"CAN bus connection failed.\n"
"Check: 1) USB adapter connected, 2) Device permissions, 3) Driver loaded."
```

---

## 3. Output Formatting

### Decision: Default human-readable with `--format json` flag

**Human-Readable Format**:
```
DHW_TEMP_SETPOINT: 55.0°C
Range: 40.0 - 70.0°C
Description: Domestic hot water temperature setpoint
```

**JSON Format**:
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

**Rationale**:
- **User-first**: Interactive users get readable output by default
- **Script-friendly**: JSON provides machine-parseable output
- **Industry standard**: AWS CLI, kubectl use similar patterns

---

## 4. Logging Strategy

### Decision: Plain text logging with RotatingFileHandler, ERROR-only default, DEBUG with --verbose

**Configuration**:
- **File handler**: RotatingFileHandler with 10MB max, 5 backups (50MB total)
- **Storage location**: `./logs/` by default, user-configurable via `--log-dir`
- **Default level**: ERROR (minimal production volume)
- **Verbose mode**: DEBUG (logs all CAN operations, requests, responses)
- **Format**: Plain text (not JSON) for human readability

**Rationale**:
- **10MB + 5 backups**: Balances retention with disk space (50MB total)
- **./logs/ location**: Avoids permission issues, flexible for both library and CLI
- **ERROR default**: Meets NFR-001 requirement for minimal production logging
- **DEBUG mode**: Meets NFR-002 requirement for comprehensive troubleshooting
- **Plain text**: More readable than JSON for debugging, 33-50% smaller

**Log Format**:
```
# File (detailed)
2025-10-24 14:23:45 - buderus_wps.can_interface - DEBUG - read_parameter:89 - Reading parameter: DHW_TEMP_SETPOINT

# Console (simple)
ERROR: CAN bus connection failed
```

**Library vs CLI Pattern**:
- **Library**: Uses NullHandler pattern (no handlers in library code)
- **CLI**: Configures all handlers and levels at entry point
- **Prevents duplicates**: Proper propagation with `propagate=False`

---

## 5. Parameter Lookup Optimization

### Decision: Simple `dict` with uppercase keys and thin wrapper class

**Performance**:
- Simple dict lookup: **~1 microsecond** (0.001ms)
- Target requirement: 100 milliseconds
- **Margin: 100,000x faster than required**

**Memory**: ~600KB for 1,789 parameters (negligible)

**Implementation**:
```python
from types import MappingProxyType

class ParameterRegistry:
    """Case-insensitive parameter lookup."""

    def __init__(self, parameters: list[dict]):
        # Normalize to uppercase at load time (once)
        self._params = {
            param['text'].upper(): param
            for param in parameters
        }
        # Immutable view (prevents accidental modification)
        self.params = MappingProxyType(self._params)

    def get(self, name: str, default=None):
        """Get parameter by name (case-insensitive). ~1µs."""
        return self.params.get(name.upper(), default)

    def __getitem__(self, name: str):
        """Dict-like access with KeyError on miss."""
        key = name.upper()
        if key not in self.params:
            raise KeyError(f"Parameter '{name}' not found")
        return self.params[key]

    def __contains__(self, name: str):
        """Check existence (case-insensitive)."""
        return name.upper() in self.params
```

**Rationale**:
- **No optimization needed**: Even simplest approach exceeds target by 100,000x
- **Case normalization negligible**: `.upper()` takes ~50 nanoseconds
- **Thread-safe**: MappingProxyType provides immutability with zero overhead
- **Simplicity wins**: 20 lines vs 100+ for SQLite, with better performance

**Alternatives Considered**:
- **OrderedDict**: No benefit (Python 3.7+ dict preserves order)
- **Caching**: Doubles memory to save 0.0000005 seconds
- **SQLite in-memory**: 100-1000x slower (still meets requirement, but complex)

---

## 6. Argument Parsing Architecture

### Decision: Parent parser pattern for global options with subcommand-specific arguments

**Structure**:
```python
def create_parser():
    # Parent parser for shared options
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--format', choices=['human', 'json'], default='human')
    parent_parser.add_argument('--timeout', type=int, default=5)
    parent_parser.add_argument('--verbose', '-v', action='store_true')

    # Main parser
    parser = argparse.ArgumentParser(prog='buderus-wps')
    parser.add_argument('--version', action='version', version='1.0.0')

    # Subcommands inherit parent options
    subparsers = parser.add_subparsers(dest='command', required=True)

    get_parser = subparsers.add_parser('get', parents=[parent_parser])
    get_parser.add_argument('parameter')
    get_parser.set_defaults(func=cmd_get)

    set_parser = subparsers.add_parser('set', parents=[parent_parser])
    set_parser.add_argument('parameter')
    set_parser.add_argument('value')
    set_parser.set_defaults(func=cmd_set)

    return parser
```

**Rationale**:
- **Parent parser pattern**: Avoids repeating global options
- **Functional dispatch**: `set_defaults(func=...)` routes cleanly
- **Type safety**: Type hints enable IDE support
- **Configuration layering**: CLI args > env vars > config file

**Configuration Support**:
- **Environment variables**: `BUDERUS_WPS_DEVICE`, `BUDERUS_WPS_TIMEOUT`, etc.
- **Config file**: `~/.buderus-wps/config.ini` (optional)
- **Precedence**: CLI args > env vars > config file > defaults

---

## 7. Implementation Dependencies

### Python Standard Library (No External Dependencies)
- `argparse`: CLI argument parsing
- `logging`: Logging framework
- `logging.handlers.RotatingFileHandler`: Log rotation
- `json`: JSON output formatting
- `sys`: Exit codes, stderr
- `pathlib.Path`: Cross-platform path handling
- `types.MappingProxyType`: Immutable dict wrapper
- `datetime`: Timestamp formatting

### Project Dependencies (Existing Features)
- **Feature 001**: CAN bus communication primitives
- **Feature 002**: Parameter definitions and metadata
- `pyserial`: USB serial communication (from Feature 001)

**No new external dependencies required** - all research solutions use Python standard library.

---

## 8. Key Design Decisions Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **CLI Commands** | `get`/`set` verbs | Clear, idiomatic, constitution-compliant |
| **Exit Codes** | 0-8 range with semantic meanings | Scriptable, POSIX-compliant |
| **Output Format** | Human default, `--format json` | User-friendly with machine option |
| **Logging Level** | ERROR default, DEBUG with `-v` | Meets NFR-001 and NFR-002 |
| **Log Rotation** | 10MB × 5 files = 50MB total | Meets FR-014, balances retention |
| **Log Format** | Plain text (not JSON) | Readable, efficient, sufficient |
| **Parameter Lookup** | Simple dict with uppercase keys | 100,000x faster than needed |
| **Thread Safety** | MappingProxyType immutability | Zero overhead, prevents bugs |
| **Library Pattern** | NullHandler (no config in lib) | Best practice, prevents conflicts |
| **CLI Pattern** | Configure all at entry point | Single source of truth |

---

## 9. Phase 1 Implementation Priorities

Based on research findings, Phase 1 should focus on:

1. **Parameter Registry Class** (`parameter_access.py`)
   - Implement `ParameterRegistry` with dict-based lookup
   - Load parameter definitions from Feature 002
   - Provide case-insensitive access with uppercase normalization

2. **CLI Argument Parser** (`cli.py`)
   - Implement parent parser pattern for global options
   - Create `get` and `set` subcommands with functional dispatch
   - Add `list` command for parameter discovery (bonus)

3. **Output Formatters** (`formatters.py`)
   - Human-readable formatter with units and ranges
   - JSON formatter with ISO timestamps
   - Error formatter for both modes

4. **Logging Configuration** (`logging_config.py`)
   - NullHandler setup for library package
   - CLI logging configuration with rotation
   - ERROR default, DEBUG with `--verbose`

5. **Exception Hierarchy** (`exceptions.py`)
   - Custom exceptions for domain errors
   - Map to appropriate exit codes

---

## 10. Testing Strategy Implications

Research findings inform test design:

**Unit Tests**:
- Parameter lookup performance (<100ms) - should complete in <1ms
- Case normalization (input lowercase, output uppercase)
- Error message formatting with context
- Exit code mapping for all error scenarios

**Integration Tests**:
- CLI command execution with subprocess
- JSON output parsing and validation
- Exit code verification for error conditions
- Log file rotation behavior (write >10MB, verify rotation)

**Contract Tests**:
- Parameter metadata compatibility with Feature 002
- CAN communication contract with Feature 001
- CLI output format stability (JSON schema validation)

**Acceptance Tests**:
- All 11 user story scenarios from spec.md
- All 8 edge cases (4 resolved, 4 remaining)
- Timeout behavior (verify 5-second timeout)
- Verbose logging (verify DEBUG output appears)

---

## 11. Open Questions for Phase 1 Design

Research has resolved most ambiguities, but Phase 1 design should address:

1. **Special characters in parameter names**: Current FHEM reference uses underscores; need to verify if spaces/hyphens exist
2. **Slow write operations**: How to provide progress feedback during long writes?
3. **Unsupported parameters**: How to handle parameters in config but not supported by device firmware?
4. **Complex data types**: Strategy for non-scalar parameter values (arrays, structs)

These should be addressed in `data-model.md` during Phase 1.

---

## Research Conclusion

All NEEDS CLARIFICATION items from Technical Context have been resolved:

✅ CLI command structure (get/set verbs)
✅ Exit code strategy (0-8 semantic codes)
✅ Output formatting (human default, JSON optional)
✅ Logging architecture (NullHandler in lib, configure in CLI)
✅ Log rotation strategy (10MB × 5 = 50MB)
✅ Parameter lookup optimization (simple dict, 100,000x margin)
✅ Argument parsing pattern (parent parser with subcommands)

**Phase 0 Status**: ✅ COMPLETE - Ready to proceed to Phase 1 (Design & Contracts)
