# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project implements a Python library and CLI for controlling Buderus WPS heat pumps via CAN bus over USB serial connection. The goal is to provide a reliable, safe, and well-tested interface for reading and writing heat pump parameters, with future Home Assistant integration.

**Key Technologies**: Python 3.9+, CAN bus protocol, USB serial communication (USBtin adapter), pyserial

**Reference Implementation**: The FHEM plugin at `fhem/26_KM273v018.pm` is the authoritative source for the CAN protocol. All protocol implementation must maintain compatibility with this reference (1789+ parameters defined).

## Architecture

The project follows a **library-first architecture** with three distinct layers:

1. **Core Library** (`buderus_wps`): Pure Python library implementing CAN bus protocol and device control
2. **CLI Tool** (`buderus_wps_cli`): Thin wrapper providing command-line interface
3. **Home Assistant Integration** (future): Plugin leveraging the library

Expected structure:
```
buderus_wps/              # Core library package
buderus_wps_cli/          # CLI tool package
custom_components/        # Home Assistant integration (future)
tests/
├── unit/                 # Unit tests
├── integration/          # Integration tests with mocks
├── contract/             # Protocol contract tests
└── acceptance/           # End-to-end acceptance tests
fhem/                     # Reference implementation (READ-ONLY)
specs/                    # Feature specifications
```

## Development Workflow

### SpecKit Commands (Feature Development)

This project uses specification-driven development. All features follow this workflow:

```bash
/speckit.specify "feature description"    # Create feature spec
/speckit.clarify                          # Resolve ambiguities (if needed)
/speckit.plan                             # Create implementation plan
/speckit.tasks                            # Generate task breakdown
/speckit.analyze                          # Quality analysis (optional)
/speckit.implement                        # Execute implementation
```

Each feature lives under `specs/###-feature-name/` with:
- `spec.md`: Requirements, user stories, success criteria (NO implementation details)
- `plan.md`: Technical approach, design decisions, architecture
- `tasks.md`: Ordered task breakdown with dependencies
- `checklists/`: Quality validation checklists

**Always check these files first when working on a feature.**

### Testing Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=buderus_wps --cov=buderus_wps_cli

# Run specific test layers
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
pytest tests/contract/       # Protocol contract tests
pytest tests/acceptance/     # Acceptance tests

# Run single test file
pytest tests/unit/test_protocol.py

# Run tests by pattern
pytest -k "test_parameter_lookup"
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy buderus_wps buderus_wps_cli

# Run all checks
black . && ruff check . && mypy buderus_wps buderus_wps_cli
```

### Git Workflow

- Feature branches: `feature/###-descriptive-name`
- Commit messages: Conventional Commits format (`feat:`, `fix:`, `docs:`, `test:`)
- Main branch (`main`) must always be deployable
- Pull requests required for all changes

### Release Process

**CRITICAL**: All releases MUST follow the complete release checklist. See [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).

**Non-Negotiable Requirements:**
1. All pytest tests pass (unit, integration, acceptance)
2. **End-to-end validation in running Home Assistant instance** (see [DEVELOPMENT.md - E2E Validation](DEVELOPMENT.md#end-to-end-validation-required-before-release))
3. Version bumped in manifest.json and entity.py
4. Changes tested in actual HA instance - verify entities exist, check logs for errors
5. GitHub release created with release notes and E2E sign-off

**Why E2E validation is mandatory:**
- Pytest tests use mocks and don't catch runtime errors like missing attributes
- v1.3.0 was released with an `AttributeError` that broke installations because E2E validation was skipped
- Only a running HA instance can validate the complete integration startup sequence

**Never skip E2E testing**, even for "trivial" patches. The v1.3.0 bug taught us that passing tests ≠ working integration.

### Hardware Access & Deployment

**Home Assistant Host Access**:
- SSH: `hassio@homeassistant.local`
- Project path: `/home/hassio/buderus-wps-ha` (git repository)
- Serial device: `/dev/ttyACM0` (USBtin adapter, accessible via `audio` group)
- The `hassio` user is a member of the `audio` group for serial port access

**Virtual Environment Setup**:
```bash
ssh hassio@homeassistant.local
cd ~/buderus-wps-ha
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

**CLI Usage on Hardware**:
```bash
# Read parameter (no sudo needed, hassio user in audio group)
cd ~/buderus-wps-ha
source venv/bin/activate
wps-cli read COMPRESSOR_STATE

# Monitor broadcasts
wps-cli monitor

# Check git status and pull updates
cd ~/buderus-wps-ha
git status
git pull
```

## Constitution & Core Principles

**Governed by**: `.specify/memory/constitution.md` (v1.1.0)

### I. Library-First Architecture
Build reusable library first, then CLI, then Home Assistant integration. Each layer independently testable.

### II. Hardware Abstraction & Protocol Fidelity
- CAN protocol must match FHEM reference exactly
- Tag protocol-critical code with `# PROTOCOL:` comments
- Cross-reference FHEM implementation in code comments
- Document all CAN message IDs, data structures, ranges

### III. Safety & Reliability
- Validate all write operations against ranges before transmission
- Implement timeout/retry logic for CAN communication
- Provide read-only mode for safe monitoring
- Log errors with sufficient diagnostic detail

### IV. Comprehensive Test Coverage (NON-NEGOTIABLE)
- **100% test coverage for all described functionality**
- TDD required: Write tests BEFORE implementation
- Tests must cover: unit, integration, contract, acceptance layers
- Tests must run without physical hardware (use mocks)
- Every functional requirement, acceptance scenario, and edge case in spec.md MUST have tests

### V. Protocol Documentation & Traceability
Cross-reference FHEM with line numbers. Use `# PROTOCOL:` tags. Maintain protocol reference mapping element IDs to functionality.

### Testing Gates (All Must Pass)
1. All tests pass (all layers)
2. Type checking passes (`mypy`)
3. Linting passes (`ruff`)
4. Coverage does not decrease (100% for described functionality)
5. Documentation updated
6. All user story acceptance scenarios tested

## Key Implementation Details

### Parameter System
- **1789+ parameters** defined in FHEM source
- Case-insensitive lookup with uppercase normalization
- Access by human-readable name OR hexadecimal address (extid)
- Each parameter has: idx, extid, min, max, format, read flag, text name

### CAN Communication
- **Primary adapter**: USBtin via USB serial (115200 baud, 8N1)
- **Future support**: socketcand TCP/IP
- **Timeout**: 5 seconds for device operations
- **Error handling**: Immediate failure with diagnostics (no automatic retries)
- **Concurrency**: Single-threaded synchronous only (no thread-safety)

### Parameter Operations
- **Read**: name → extid → CAN message → parse response → format value
- **Write**: validate (read-only flag, min/max, type) → CAN message → verify
- **Logging**: Error-only default, verbose debug mode with 10MB rotating logs

## Active Features

Current features in `specs/`:
- **001-can-usb-serial**: CAN over USB serial connection
- **002-buderus-wps-python-class**: Parameter definitions from FHEM (completed)
- **003-program-switching-control**: DHW/heating program switching
- **004-perl-config-parser**: Parse FHEM parameter definitions
- **005-can-parameter-access**: Read/write parameters by name (in progress)

## Protocol Implementation Pattern

When adding CAN element support:
1. Document in protocol reference
2. Cross-reference FHEM implementation (file + line numbers)
3. Add `# PROTOCOL:` comment tag
4. Write contract tests for encoding/decoding
5. Test with physical hardware if available
6. Mark as hardware-verified or inferred-from-FHEM

## Important Constraints

- **DO NOT** modify files in `fhem/` directory (read-only reference)
- **DO NOT** modify `/config/custom_components/buderus_wps/` directly - HA integration is HACS-managed!
- **DO NOT** skip tests (100% coverage for described functionality mandatory)
- **DO NOT** commit without explicit user request
- **ALWAYS** write tests before implementation (TDD required)
- **ALWAYS** check constitution before architectural decisions
- **ALWAYS** use uppercase for parameter names (normalization)
- **ALWAYS** provide diagnostic context in error messages
- **ALWAYS** deploy HA integration changes via HACS/GitHub releases, never direct file copy
- Timeout after 5 seconds for all CAN operations
- Protocol-critical code requires `# PROTOCOL:` tags

## Key Files

- `.specify/memory/constitution.md`: Project governance (v1.1.0)
- `fhem/26_KM273v018.pm`: FHEM reference plugin (READ-ONLY)
- `benchmark_lookup.py`: Parameter lookup performance benchmarks
- `specs/[###-name]/`: Feature specifications and plans

## Active Technologies
- N/A (JSON configuration files only) + HACS validation requirements, GitHub Releases API (014-hacs-publishing)
- Python 3.9+ + Home Assistant Core (>=2024.3.0), homeassistant.helpers.update_coordinator, homeassistant.components.switch (015-usb-connection-switch)
- N/A (state is non-persistent by design) (015-usb-connection-switch)

## Recent Changes
- 014-hacs-publishing: Added N/A (JSON configuration files only) + HACS validation requirements, GitHub Releases API
