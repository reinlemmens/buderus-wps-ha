<!--
Sync Impact Report
==================
Version Change: 1.2.0 → 1.2.1 (Patch - added deployment target clarification)
Modified Principles:
  - None (no principles changed)
Added Sections:
  - "Deployment Environment" subsection under Technical Standards specifying Raspberry Pi + Linux + USBtin target
Removed Sections: None
Templates Requiring Updates:
  ✅ plan-template.md - No updates needed (deployment-agnostic planning)
  ✅ spec-template.md - No updates needed (functional requirements remain platform-agnostic)
  ✅ tasks-template.md - No updates needed (implementation tasks can reference deployment target as needed)
  ✅ All templates verified for consistency
Follow-up TODOs:
  - None (clarification only, no breaking changes)
-->

# Buderus WPS Heat Pump Controller Constitution

## Core Principles

### I. Library-First Architecture

The project is structured as a layered system with clear boundaries:

- **Core Library** (`buderus_wps`): Pure Python library implementing CAN bus protocol and device control. MUST be independently usable, fully tested, and documented.
- **CLI Tool**: Thin wrapper around the library providing command-line interface. MUST support both interactive and scripted use cases.
- **Home Assistant Integration**: Plugin leveraging the library for smart home integration. MUST follow Home Assistant development guidelines and conventions.

**Rationale**: This architecture ensures code reusability, testability, and maintainability. Each layer can be developed, tested, and distributed independently while sharing core functionality.

### II. Hardware Abstraction & Protocol Fidelity

The library MUST accurately implement the Buderus WPS heat pump CAN bus protocol as documented in the FHEM plugin reference (`fhem/26_KM273v018.pm`):

- CAN message encoding/decoding MUST match the reference implementation
- Element list structure and data types MUST be preserved
- USBtin CAN controller communication MUST be reliable and well-documented
- Alternative CAN adapters (e.g., socketcand TCP/IP) SHOULD be supported through abstraction

**Rationale**: The FHEM plugin is the authoritative reference for the protocol. Deviations risk device malfunction or data corruption. Hardware abstraction enables broader compatibility.

### III. Safety & Reliability

Heat pump control involves physical equipment and home comfort:

- All write operations MUST validate ranges and constraints before transmission
- The library MUST implement timeout and retry logic for CAN communication
- Error conditions MUST be logged with sufficient detail for troubleshooting
- A "read-only" mode MUST be available for safe monitoring without control
- State changes MUST be atomic and verifiable

**Rationale**: Incorrect commands could damage equipment or create unsafe conditions. Defensive programming and comprehensive error handling are non-negotiable.

### IV. Comprehensive Test Coverage for All Described Functionality (NON-NEGOTIABLE)

TDD is mandatory for this project due to hardware dependencies and safety requirements. Every piece of functionality described in a feature specification MUST have corresponding tests:

- **All Described Functionality**: Every functional requirement, user story acceptance scenario, and edge case documented in spec.md MUST have corresponding test coverage
- **Test-First Discipline**: Unit tests MUST be written before implementation and MUST fail initially
- **Multi-Layer Testing**: Features MUST include appropriate tests at all relevant layers:
  - Unit tests for individual functions and classes
  - Integration tests for CAN communication paths with mock hardware
  - Contract tests to verify protocol compatibility with reference implementation
  - Acceptance tests validating user story scenarios end-to-end
- **Hardware Independence**: Tests MUST run without physical hardware (mocking/simulation required)
- **Continuous Integration**: CI MUST enforce test passing before merge
- **Coverage Tracking**: Test coverage MUST be measured and MUST NOT decrease with new changes

**Rationale**: Hardware interaction bugs are expensive and dangerous. Comprehensive test coverage for all described functionality ensures correctness, enables safe refactoring, and provides living documentation. Mock-based testing enables development without risking physical equipment. When functionality is specified, it MUST be tested - no exceptions.

### V. Protocol Documentation & Traceability

Every supported CAN message, element ID, and data structure MUST be documented:

- Cross-reference FHEM plugin implementation in code comments
- Document data types, ranges, and units for all readings and controls
- Maintain a protocol reference document mapping element IDs to functionality
- Tag protocol-critical code with `# PROTOCOL:` comments for easy search

**Rationale**: The CAN protocol is not publicly documented by Buderus. Maintaining comprehensive documentation ensures long-term maintainability and enables community contributions.

### VI. Home Assistant Integration Standards

The Home Assistant plugin MUST follow platform conventions:

- Use Home Assistant entity types appropriately (sensor, climate, switch, etc.)
- Implement async I/O for non-blocking operation
- Support Home Assistant configuration flow (UI-based setup)
- Follow Home Assistant naming conventions and style guide
- Provide entity metadata (device class, unit of measurement, icons)

**Rationale**: Home Assistant has established patterns for device integration. Adherence ensures compatibility, user experience consistency, and acceptance in the Home Assistant ecosystem.

### VII. CLI Design Principles

The CLI tool MUST provide both human and machine interfaces:

- Commands use verb-noun structure (e.g., `buderus-wps get temperature`)
- Support JSON output for scripting (`--format json`)
- Provide human-readable output by default with units and labels
- Exit codes follow Unix conventions (0=success, non-zero=error)
- Support `--help` and `--version` flags
- Configuration via environment variables and config files

**Rationale**: A well-designed CLI serves both interactive users and automation scripts. Following Unix conventions ensures predictability and integration with existing tools.

## Technical Standards

### Language & Dependencies

- **Language**: Python 3.9+ (for Home Assistant compatibility and modern syntax)
- **Core Dependencies**: Minimal required dependencies only
  - `pyserial` for USBtin communication
  - Standard library for CAN message handling where possible
- **Optional Dependencies**: Feature-specific extras (e.g., `[homeassistant]` extra)
- **Type Hints**: Mandatory for all public APIs and recommended for internal code
- **Async Support**: Required for Home Assistant integration, optional for library core

### Development Environment

- **Virtual Environment**: MUST use Python virtual environments for all development and testing
  - Create venv before installing dependencies: `python3 -m venv venv`
  - Activate before work: `source venv/bin/activate` (Unix) or `venv\Scripts\activate` (Windows)
  - All `pip install` commands MUST run inside activated virtual environment
  - CI/CD pipelines MUST use isolated virtual environments
- **Dependency Management**: Use `pyproject.toml` for dependency specification
- **Reproducibility**: Lock files (e.g., `requirements.txt` or `poetry.lock`) SHOULD be maintained for exact version reproduction

**Rationale**: Virtual environments prevent system Python pollution, ensure reproducible builds, avoid permission issues with system packages, and enable isolation between projects. This is a Python best practice that prevents the "works on my machine" problem and respects externally-managed Python installations.

### Deployment Environment

- **Target Platform**: Linux on Raspberry Pi (primary deployment target)
- **Hardware**: USBtin CAN adapter connected via USB port
- **Serial Port**: Typically `/dev/ttyACM0` or `/dev/ttyUSB0` on Linux
- **Permissions**: User must be member of `dialout` group for serial port access
- **System Requirements**: Python 3.9+ available on target system
- **USB Auto-detection**: Library SHOULD support automatic USB device detection
- **Cross-Platform Support**: While Raspberry Pi/Linux is the primary target, library MUST remain cross-platform compatible (Linux/macOS/Windows)

**Rationale**: Raspberry Pi provides reliable, low-cost, always-on hardware for home automation integration. Linux environment ensures compatibility with Home Assistant OS. Documenting the primary deployment target guides implementation decisions (e.g., serial port paths, permission handling) while maintaining cross-platform library design.

### Code Quality & Style

- **Formatting**: `black` with default settings (88 char line length)
- **Linting**: `ruff` for fast, comprehensive linting
- **Type Checking**: `mypy` in strict mode for public APIs
- **Documentation**: Docstrings (Google style) for all public functions and classes
- **Testing**: `pytest` with coverage reporting (target: 80%+ for library core, 100% for all described functionality)

### Project Structure

```
buderus_wps/              # Core library package
├── __init__.py
├── protocol.py           # CAN protocol implementation
├── device.py             # Device abstraction
├── can_adapter.py        # Hardware abstraction layer
└── elements.py           # Element definitions from FHEM

buderus_wps_cli/          # CLI tool package
├── __init__.py
├── cli.py                # Command-line interface
└── formatters.py         # Output formatting

custom_components/        # Home Assistant integration
└── buderus_wps/
    ├── __init__.py
    ├── climate.py
    ├── sensor.py
    └── manifest.json

tests/
├── unit/                 # Unit tests
├── integration/          # Integration tests with mocks
├── contract/             # Protocol contract tests
└── acceptance/           # End-to-end acceptance tests

fhem/                     # Reference implementation
└── 26_KM273v018.pm       # FHEM plugin for reference
```

## Development Workflow

### Branching & Commits

- **Main Branch**: `main` is always deployable
- **Feature Branches**: `feature/###-descriptive-name` for new work
- **Commit Messages**: Conventional Commits format (e.g., `feat:`, `fix:`, `docs:`)
- **Pull Requests**: Required for all changes, must pass CI

### Testing Gates

Before any feature is considered complete:

1. All tests pass (unit + integration + contract + acceptance)
2. Type checking passes with no errors
3. Linting passes with no violations
4. Coverage does not decrease (and covers all described functionality)
5. Documentation is updated
6. All user story acceptance scenarios have corresponding tests

### Protocol Changes

When adding support for new CAN elements:

1. Document the element in protocol reference
2. Cross-reference FHEM implementation
3. Add contract tests verifying encoding/decoding
4. Test with physical hardware if available
5. Mark hardware-verified vs. inferred from FHEM

### Test Requirements for Features

When a feature specification includes:

- **Functional Requirements**: MUST have unit tests for each requirement
- **User Story Acceptance Scenarios**: MUST have acceptance/integration tests for each scenario
- **Edge Cases**: MUST have tests covering each documented edge case
- **Success Criteria**: MUST have tests validating measurable outcomes

No feature is complete without tests for all described functionality.

## Governance

### Constitution Authority

This constitution supersedes all other practices and conventions. When conflicts arise:

1. Constitution takes precedence
2. Team discusses whether constitution needs amendment
3. Amendment requires documented rationale and migration plan
4. Version is incremented per semantic versioning rules

### Amendment Process

- **Minor Changes** (clarifications, typos): Single-reviewer approval
- **Major Changes** (new principles, removed constraints): Team consensus required
- **Breaking Changes**: Migration plan mandatory, major version increment

### Compliance Review

- All pull requests MUST verify constitution compliance
- Violations MUST be justified in "Complexity Tracking" section of plan.md
- Repeated violations trigger constitution review
- This document is living: update as project learns

### Versioning Rules

- **MAJOR**: Backward incompatible governance changes, principle removal/redefinition
- **MINOR**: New principles added, materially expanded guidance
- **PATCH**: Clarifications, wording improvements, non-semantic refinements

**Version**: 1.2.1 | **Ratified**: 2025-10-21 | **Last Amended**: 2025-10-24
