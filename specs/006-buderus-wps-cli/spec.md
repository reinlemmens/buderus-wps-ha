# Feature Specification: Buderus WPS CLI for USBtin

**Feature Branch**: `006-buderus-wps-cli`  
**Created**: 2025-10-21  
**Status**: Draft  
**Input**: "we want to create a CLI that I can run locally on the device that has the USBtin and that gives read and write access to the parameters on the heatpump"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read Parameter (Priority: P1)
As a user on the device with USBtin, I can read a parameter by name or index and see its decoded value and raw bytes.

**Independent Test**: Run `wps-cli read ACCESS_LEVEL` and verify it connects, reads, and prints value + raw bytes + metadata; errors show clear diagnostics if parameter is unknown or connection fails.

### User Story 2 - Write Parameter (Priority: P1)
As a user, I can write a parameter by name or index with validation (range/format/read-only) and get confirmation of success/failure.

**Independent Test**: Run `wps-cli write ACCESS_LEVEL 2` and verify validation (range/format/read-only) and success/error reporting; dry-run/read-only blocks writes.

### User Story 3 - List/Search (Priority: P2)
As a user, I can list/search parameters (filter by name/format/read-only) with summaries (idx, extid, min/max, format).

**Independent Test**: Run `wps-cli list --filter access` and see rows with idx/extid/name/format/min/max/read flag; filtering works.

### User Story 4 - Dump All Values (Priority: P2)
As a user, I can dump all parameter values in one command (human-readable or JSON) for backup/diagnostics.

**Independent Test**: Run `wps-cli dump --json` and receive a JSON array of all parameters with decoded/raw values; failures are reported with a nonzero exit code and per-parameter error details.

### User Story 5 - Live Refresh (Priority: P3, optional)
As a user, I can refresh the parameter registry from the heat pump (KM273_ReadElementList) and see a summary of changes.

**Independent Test**: Run `wps-cli refresh` to trigger KM273_ReadElementList; report added/removed/modified counts; fall back to defaults on failure.

### User Story 6 - Safe Mode (Priority: P1)
As a user, I can run in read-only mode to prevent writes.

**Independent Test**: Run `wps-cli --read-only write ACCESS_LEVEL 2` and verify write is blocked with clear messaging.

---

## Requirements *(mandatory)*

- **FR-001**: CLI MUST connect to USBtin on `/dev/ttyACM0` @115200 (override via flag).
- **FR-002**: CLI MUST support read by name or index; output decoded value, raw bytes, and parameter metadata.
- **FR-003**: CLI MUST support write by name or index with validation (min/max, format, read-only).
- **FR-004**: CLI MUST provide list/search with filters; show idx, extid, name, format, min, max, read flag.
- **FR-005**: CLI MUST support a read-only/dry-run mode that blocks writes.
- **FR-006**: CLI MUST offer JSON output mode for scripting.
- **FR-007**: CLI MUST report errors clearly (connection, validation, protocol, timeout) and use nonzero exit codes on failure.
- **FR-008**: Optional refresh: trigger KM273_ReadElementList and summarize changes; fall back to defaults on failure.
- **FR-009**: Operations MUST time out within 5 seconds by default.
- **FR-010**: Output MUST be deterministic for the same inputs.
- **FR-011**: CLI MUST provide a `dump`/bulk-read command that iterates all parameters, outputs decoded + raw values (human and JSON), and reports per-parameter failures while returning nonzero on any error.

---

## Success Criteria *(mandatory)*

- **SC-001**: `read` completes under 5s with decoded value + raw bytes + metadata.
- **SC-002**: `write` enforces validation/read-only and reports success/failure; dry-run/read-only blocks transmission.
- **SC-003**: `list`/`search` shows required fields and honors filters; JSON output works.
- **SC-003a**: `dump` returns all readable parameters with decoded/raw values; JSON output is valid and includes an errors collection; exit code >0 if any parameter fails.
- **SC-004**: `refresh` (if used) reports added/removed/modified counts or a clear fallback message.
- **SC-005**: Nonzero exit codes on any error; zero on success.

---

## Assumptions

- Linux-only; USBtin/SLCAN on `/dev/ttyACM0`.
- Existing library components (`USBtinAdapter`, `HeatPumpClient`, `ParameterRegistry`) are used.
- Parameter names are case-insensitive; defaults present even if refresh fails.
- No Home Assistant or UI integration in this feature.

## Dependencies

- `buderus_wps` library (adapter, registry, heat pump client).
- USBtin hardware on `/dev/ttyACM0`.

## Out of Scope

- GUI or Home Assistant integration.
- Concurrent/multi-command sessions; one command per invocation.
- Advanced diagnostics beyond clear error messages and exit codes.
