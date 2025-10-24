# Quickstart Guide: CAN Bus Parameter Read/Write Access

**Feature**: 005-can-parameter-access
**Audience**: Developers implementing this feature
**Date**: 2025-10-24

This guide provides a fast path to implementing the parameter read/write functionality.

---

## Prerequisites

Before starting implementation:

✅ **Feature 001**: CAN bus communication via USB serial (complete)
✅ **Feature 002**: Buderus WPS Python class with parameter definitions (complete)
✅ **Python 3.9+**: Installed and configured
✅ **Development environment**: pytest, mypy, black, ruff configured

---

## Implementation Order

Follow this sequence to implement the feature:

### Phase 2A: Core Library (Week 1)

1. **Exceptions** (`buderus_wps/exceptions.py`) - 1 hour
   - Define exception hierarchy with exit codes
   - Inherit from base `ParameterError`
   - Add docstrings for each exception type

2. **Models** (`buderus_wps/models.py`) - 2 hours
   - Implement `Parameter` frozen dataclass
   - Implement `ParameterValue` dataclass
   - Add `validate_value()` and `is_read_only()` methods
   - Add `format_human()` and `format_json()` methods

3. **Registry** (`buderus_wps/registry.py`) - 3 hours
   - Implement `ParameterRegistry` class with dict storage
   - Use `MappingProxyType` for immutability
   - Implement `get()`, `__getitem__()`, `__contains__()`, `list_all()`
   - Case-insensitive lookup with uppercase normalization

4. **Logging Configuration** (`buderus_wps/logging_config.py`) - 2 hours
   - Implement `setup_library_logging()` with NullHandler
   - Implement `setup_cli_logging()` with RotatingFileHandler
   - Configure ERROR default, DEBUG with verbose flag
   - 10MB file size, 5 backups

5. **Parameter Accessor** (`buderus_wps/parameter_access.py`) - 4 hours
   - Implement `ParameterAccessor` class
   - Implement `read_parameter()` with:
     - Parameter lookup
     - CAN request via Feature 001
     - 5-second timeout
     - Value conversion
     - Error handling
   - Implement `write_parameter()` with:
     - Validation against min/max
     - Writable check
     - CAN write request
     - Read-back confirmation
     - Error handling

**Subtotal**: ~12 hours for core library

### Phase 2B: CLI Tool (Week 1-2)

6. **Output Formatters** (`buderus_wps_cli/formatters.py`) - 2 hours
   - Implement `OutputFormatter` class
   - Implement `format_get_human()` and `format_get_json()`
   - Implement `format_set_human()` and `format_set_json()`
   - Implement `format_error_json()`

7. **CLI Argument Parser** (`buderus_wps_cli/cli.py`) - 3 hours
   - Implement `create_parser()` with parent parser pattern
   - Add global options (--format, --timeout, --verbose, --log-dir)
   - Add `get` subcommand
   - Add `set` subcommand
   - Add `list` subcommand
   - Implement functional dispatch with `set_defaults(func=...)`

8. **CLI Command Handlers** (`buderus_wps_cli/cli.py`) - 3 hours
   - Implement `cmd_get()` handler
   - Implement `cmd_set()` handler
   - Implement `cmd_list()` handler
   - Add error handling with appropriate exit codes
   - Format output based on `--format` flag

9. **CLI Entry Point** (`buderus_wps_cli/__main__.py`) - 1 hour
   - Implement `main()` function
   - Setup logging at entry point
   - Initialize ParameterAccessor
   - Handle KeyboardInterrupt
   - Return appropriate exit codes

**Subtotal**: ~9 hours for CLI tool

### Phase 2C: Tests (Week 2)

10. **Unit Tests** - 8 hours
    - `test_parameter_model.py`: Parameter validation, is_read_only()
    - `test_parameter_registry.py`: Lookup, case-insensitivity, list_all()
    - `test_parameter_accessor.py`: Read/write with mocked CAN interface
    - `test_cli_formatters.py`: Human/JSON output formatting
    - `test_exceptions.py`: Exception hierarchy, exit codes

11. **Integration Tests** - 6 hours
    - `test_parameter_read_write.py`: End-to-end with mock CAN
    - `test_cli_commands.py`: Subprocess execution of CLI
    - `test_logging.py`: Log rotation, ERROR/DEBUG levels

12. **Contract Tests** - 4 hours
    - `test_parameter_metadata.py`: Compatibility with Feature 002
    - `test_can_communication.py`: Compatibility with Feature 001
    - `test_cli_output_schema.py`: JSON schema validation

13. **Acceptance Tests** - 6 hours
    - `test_us1_read_parameters.py`: User Story 1 scenarios
    - `test_us2_write_parameters.py`: User Story 2 scenarios
    - `test_us3_cli_commands.py`: User Story 3 scenarios
    - `test_edge_cases.py`: All 8 edge cases from spec

**Subtotal**: ~24 hours for tests

### Phase 2D: Documentation & Polish (Week 2-3)

14. **Docstrings** - 2 hours
    - Add Google-style docstrings to all public APIs
    - Include examples in docstrings
    - Document all exceptions raised

15. **README** - 1 hour
    - Update project README with usage examples
    - Add CLI command reference
    - Link to full API documentation

16. **Type Checking** - 1 hour
    - Run mypy in strict mode
    - Fix any type errors
    - Add type: ignore comments with justification

17. **Code Formatting & Linting** - 1 hour
    - Run black on all files
    - Run ruff and fix violations
    - Verify all tests pass

**Subtotal**: ~5 hours for polish

**Total Implementation Time**: ~50 hours (~1.5-2 weeks for 1 developer)

---

## Quick Reference: File Structure

```
buderus_wps/
├── __init__.py                  # Add imports, version
├── exceptions.py                # NEW: Exception hierarchy
├── models.py                    # NEW: Parameter, ParameterValue
├── registry.py                  # NEW: ParameterRegistry
├── parameter_access.py          # NEW: ParameterAccessor
└── logging_config.py            # NEW: Logging setup

buderus_wps_cli/
├── __init__.py                  # NEW: Package init
├── cli.py                       # NEW: Argument parser, command handlers
├── formatters.py                # NEW: Output formatting
└── __main__.py                  # NEW: Entry point

tests/
├── unit/
│   ├── test_parameter_model.py          # NEW
│   ├── test_parameter_registry.py       # NEW
│   ├── test_parameter_accessor.py       # NEW
│   ├── test_cli_formatters.py           # NEW
│   └── test_exceptions.py               # NEW
├── integration/
│   ├── test_parameter_read_write.py     # NEW
│   ├── test_cli_commands.py             # NEW
│   └── test_logging.py                  # NEW
├── contract/
│   ├── test_parameter_metadata.py       # NEW
│   ├── test_can_communication.py        # NEW
│   └── test_cli_output_schema.py        # NEW
└── acceptance/
    ├── test_us1_read_parameters.py      # NEW
    ├── test_us2_write_parameters.py     # NEW
    ├── test_us3_cli_commands.py         # NEW
    └── test_edge_cases.py               # NEW

logs/                            # NEW: Log directory (created at runtime)
└── buderus_wps.log              # NEW: Rotating log file
```

---

## Code Templates

### Template 1: Exception Hierarchy

```python
# buderus_wps/exceptions.py

class ParameterError(Exception):
    """Base exception for parameter operations."""
    exit_code: int = 1

class ParameterNotFoundError(ParameterError):
    """Parameter name doesn't exist in registry."""
    exit_code: int = 3

    def __init__(self, name: str):
        super().__init__(f"Parameter '{name}' not found")
        self.parameter_name = name

# ... add remaining exceptions (ReadOnly, Validation, CANBus, Timeout, Device)
```

### Template 2: Parameter Model

```python
# buderus_wps/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any

@dataclass(frozen=True)
class Parameter:
    """Immutable parameter definition."""
    idx: int
    extid: int
    text: str  # UPPERCASE
    min_value: int | float
    max_value: int | float
    format: str
    writable: bool
    unit: str | None = None
    description: str | None = None

    def validate_value(self, value: Any) -> bool:
        """Check if value within allowed range."""
        try:
            numeric = float(value)
            return self.min_value <= numeric <= self.max_value
        except (ValueError, TypeError):
            return False

    def is_read_only(self) -> bool:
        """Check if parameter is read-only."""
        return not self.writable or (self.min_value == 0 and self.max_value == 0)
```

### Template 3: Parameter Registry

```python
# buderus_wps/registry.py
from types import MappingProxyType
from typing import Optional

class ParameterRegistry:
    """Fast case-insensitive parameter lookup."""

    def __init__(self, parameters: list[Parameter]):
        self._params = {p.text.upper(): p for p in parameters}
        if len(self._params) != len(parameters):
            raise ValueError("Duplicate parameter names found")
        self.params = MappingProxyType(self._params)

    def get(self, name: str, default: Optional[Parameter] = None) -> Optional[Parameter]:
        """Get parameter by name (case-insensitive)."""
        return self.params.get(name.upper(), default)

    def __getitem__(self, name: str) -> Parameter:
        """Dict-like access."""
        key = name.upper()
        if key not in self.params:
            raise KeyError(f"Parameter '{name}' not found")
        return self.params[key]

    # ... add __contains__(), __len__(), list_all()
```

### Template 4: CLI Parser

```python
# buderus_wps_cli/cli.py
import argparse

def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    # Parent parser for shared options
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--format', choices=['human', 'json'], default='human')
    parent_parser.add_argument('--timeout', type=int, default=5)
    parent_parser.add_argument('--verbose', '-v', action='store_true')
    parent_parser.add_argument('--log-dir', default='./logs')

    # Main parser
    parser = argparse.ArgumentParser(prog='buderus-wps')
    parser.add_argument('--version', action='version', version='1.0.0')

    # Subcommands
    subparsers = parser.add_subparsers(dest='command', required=True)

    # GET command
    get_parser = subparsers.add_parser('get', parents=[parent_parser])
    get_parser.add_argument('parameter')
    get_parser.set_defaults(func=cmd_get)

    # ... add SET and LIST subparsers

    return parser

def cmd_get(args):
    """Handle GET command."""
    # Implementation here
    pass
```

---

## Testing Quick Start

### Run All Tests

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# All tests with coverage
pytest tests/ --cov=buderus_wps --cov=buderus_wps_cli --cov-report=html

# Type checking
mypy buderus_wps/ buderus_wps_cli/ --strict

# Linting
ruff check buderus_wps/ buderus_wps_cli/

# Formatting
black buderus_wps/ buderus_wps_cli/ tests/
```

### Test Writing Pattern

```python
# tests/unit/test_parameter_registry.py
import pytest
from buderus_wps.models import Parameter
from buderus_wps.registry import ParameterRegistry

def test_case_insensitive_lookup():
    """Test that parameter lookup is case-insensitive."""
    params = [
        Parameter(idx=1, extid=0x123, text="DHW_TEMP", min_value=0, max_value=100,
                 format="int", writable=True)
    ]
    registry = ParameterRegistry(params)

    # All these should return the same parameter
    assert registry.get("DHW_TEMP") is not None
    assert registry.get("dhw_temp") is not None
    assert registry.get("Dhw_Temp") is not None
    assert registry["DHW_TEMP"].text == "DHW_TEMP"  # Normalized to uppercase
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Circular Imports

**Problem**: Importing `ParameterAccessor` in `cli.py` while `cli.py` imports `exceptions.py` which imports `ParameterAccessor`.

**Solution**: Use late imports inside functions or use `typing.TYPE_CHECKING`.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from buderus_wps.parameter_access import ParameterAccessor

def cmd_get(args):
    # Import here to avoid circular dependency
    from buderus_wps import ParameterAccessor
    accessor = ParameterAccessor(...)
```

### Pitfall 2: Logging Not Configured

**Problem**: Library logs don't appear when CLI is run.

**Solution**: Always call `setup_cli_logging()` at CLI entry point BEFORE any library operations.

```python
def main():
    parser = create_parser()
    args = parser.parse_args()

    # FIRST: Setup logging
    setup_cli_logging(verbose=args.verbose, log_dir=args.log_dir)

    # THEN: Execute command
    args.func(args)
```

### Pitfall 3: Case Normalization Inconsistency

**Problem**: Sometimes comparing lowercase, sometimes uppercase.

**Solution**: ALWAYS normalize to uppercase at registry level. All other code uses uppercase.

```python
# GOOD: Consistent uppercase
def get(self, name: str) -> Parameter:
    return self.params.get(name.upper())

# BAD: Inconsistent case handling
def get(self, name: str) -> Parameter:
    return self.params.get(name.lower())  # Wrong! Registry uses uppercase
```

### Pitfall 4: Mutable Default Arguments

**Problem**: Using `default={}` or `default=[]` in function signatures.

**Solution**: Use `None` and create new object inside function.

```python
# BAD
def read_parameter(self, name: str, options: dict = {}) -> ParameterValue:
    options['timeout'] = 5  # Mutates shared default!

# GOOD
def read_parameter(self, name: str, options: dict | None = None) -> ParameterValue:
    if options is None:
        options = {}
    options['timeout'] = 5  # Safe
```

### Pitfall 5: Not Testing Exit Codes

**Problem**: Tests check output but not exit codes.

**Solution**: Always verify exit codes in CLI integration tests.

```python
def test_parameter_not_found_exit_code():
    """Test that invalid parameter returns exit code 3."""
    result = subprocess.run(
        ['buderus-wps', 'get', 'INVALID_PARAM'],
        capture_output=True
    )
    assert result.returncode == 3  # PARAMETER_NOT_FOUND
```

---

## Debugging Tips

### Enable Verbose Logging

```bash
# Run with verbose flag to see all operations
buderus-wps get DHW_TEMP_SETPOINT --verbose

# Check log file for detailed trace
tail -f logs/buderus_wps.log
```

### Use Python Debugger

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use built-in breakpoint (Python 3.7+)
breakpoint()
```

### Test with Mock CAN Interface

```python
# tests/unit/test_parameter_accessor.py
from unittest.mock import Mock, MagicMock

def test_read_parameter_success():
    """Test reading parameter with mocked CAN interface."""
    # Create mock CAN interface
    can_mock = Mock()
    can_mock.send_request.return_value = bytes([0x00, 0x2D])  # Mock response

    # Create accessor with mock
    accessor = ParameterAccessor(registry, can_mock, timeout=5.0)

    # Test read
    value = accessor.read_parameter("DHW_TEMP_SETPOINT")

    # Verify CAN interface was called correctly
    can_mock.send_request.assert_called_once_with(0x31D011E9, [0x01], timeout=5.0)
    assert value.value == 45.0
```

---

## Performance Optimization

**Do NOT optimize prematurely!** Follow this priority:

1. **Correctness**: Make it work correctly first
2. **Clarity**: Make code readable and maintainable
3. **Performance**: Only optimize if needed

**Performance targets already exceeded**:
- ✅ Parameter lookup: <1ms (target: 100ms) - **100x margin**
- ✅ Total read operation: ~1s (target: 2s) - **2x margin**

**If you need to optimize**:
- Profile first: `python -m cProfile cli.py get DHW_TEMP`
- Focus on hot paths (CAN communication, not dict lookup)
- Add caching only if measurements justify it

---

## Definition of Done Checklist

Before considering this feature complete:

- ✅ All 14 functional requirements implemented and tested
- ✅ All 5 non-functional requirements met
- ✅ All 11 user story acceptance scenarios have passing tests
- ✅ All 8 edge cases handled and tested
- ✅ Unit test coverage ≥ 90% (aiming for 100%)
- ✅ Integration tests cover happy path and error scenarios
- ✅ Contract tests verify Feature 001 and 002 compatibility
- ✅ Acceptance tests validate end-to-end user workflows
- ✅ Type checking passes with mypy --strict
- ✅ Linting passes with ruff (no violations)
- ✅ All code formatted with black
- ✅ Public APIs have complete docstrings
- ✅ CLI help output is clear and accurate
- ✅ Logging produces expected output in ERROR and DEBUG modes
- ✅ Exit codes match specification
- ✅ JSON output matches schema
- ✅ Constitution Check passes (re-evaluated in plan.md)

---

## Resources

- **Spec**: [spec.md](spec.md) - Feature specification with requirements
- **Research**: [research.md](research.md) - CLI design, logging, optimization decisions
- **Data Model**: [data-model.md](data-model.md) - Entity definitions and relationships
- **Contracts**: [contracts/](contracts/) - API and CLI interface contracts
- **Plan**: [plan.md](plan.md) - Implementation plan with constitution check

---

## Getting Help

1. **Review research.md** for design decisions and rationale
2. **Check data-model.md** for entity definitions
3. **Read contracts/** for API specifications
4. **Run existing tests** to see examples
5. **Ask team** if stuck (constitution encourages collaboration)

---

## Next Steps

1. Read through all Phase 1 documents (research, data-model, contracts)
2. Set up development environment (Python 3.9+, pytest, mypy, black, ruff)
3. Start with Phase 2A (core library) following implementation order above
4. Write tests FIRST (TDD per constitution Principle IV)
5. Run constitution check before submitting for review

**Good luck! 🚀**
