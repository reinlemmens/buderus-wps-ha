# Implementation Plan: Element Discovery Protocol

**Branch**: `018-element-discovery` | **Date**: 2026-01-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/018-element-discovery/spec.md`

## Summary

Implement reliable element discovery for Buderus WPS heat pumps that automatically retrieves parameter indices at runtime. The key changes from current implementation:

1. **Fail-fast on fresh install** - No silent fallback to static idx values
2. **Cache-only fallback** - Use last successful discovery, never static defaults for idx
3. **Persistent cache location** - Move from `/tmp/` to `/config/` for HA containers
4. **Parameter availability tracking** - Mark parameters unavailable if idx not discovered

## Technical Context

**Language/Version**: Python 3.9+ (Home Assistant compatibility requirement)
**Primary Dependencies**: pyserial (CAN adapter), struct (binary parsing), json (caching)
**Storage**: JSON file cache at `/config/buderus_wps_elements.json`
**Testing**: pytest with mocked CAN adapter
**Target Platform**: Home Assistant (Linux, Docker containers)
**Project Type**: Single project (Python library + HA integration)
**Performance Goals**: Discovery < 30s, cache load < 5s
**Constraints**: Must work in HA container where /tmp is ephemeral
**Scale/Scope**: ~2000 parameters per heat pump, single device per integration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution not yet defined for this project. Proceeding with standard Python best practices:
- [x] Changes isolated to element discovery module
- [x] No new external dependencies required
- [x] Backward compatible (cache format already supports metadata)
- [x] Tests exist for element discovery (test_element_discovery.py)

## Project Structure

### Documentation (this feature)

```text
specs/018-element-discovery/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
buderus_wps/
├── element_discovery.py    # Main discovery protocol (MODIFY)
├── parameter.py            # Parameter registry (MODIFY)
├── parameter_defaults.py   # Static defaults - format/read only (NO CHANGE)
├── exceptions.py           # Custom exceptions (MODIFY - add DiscoveryRequiredError)
└── cache.py               # Cache utilities (REVIEW)

custom_components/buderus_wps/
├── coordinator.py          # HA integration coordinator (MODIFY)
└── __init__.py            # Integration setup (REVIEW)

tests/
├── unit/
│   ├── test_element_discovery.py  # Discovery unit tests (MODIFY)
│   └── test_parameter.py          # Registry tests (MODIFY)
└── hil/
    └── debug_element_list.py      # Hardware-in-loop debug tool
```

**Structure Decision**: Existing single-project Python structure. Changes primarily in `buderus_wps/` library with integration updates in `custom_components/`.

## Complexity Tracking

No constitution violations to justify.

## Implementation Changes Required

### Change 1: Fail-Fast on Fresh Install (FR-009)

**File**: `buderus_wps/element_discovery.py` (discover_with_cache method)
**Current**: Falls back to static defaults when discovery fails
**Required**: Raise `DiscoveryRequiredError` if no cache exists and discovery fails

### Change 2: Cache-Only Fallback (FR-010)

**File**: `buderus_wps/element_discovery.py`
**Current**: Uses static defaults from parameter_defaults.py
**Required**: Only fall back to previous successful discovery cache

### Change 3: Persistent Cache Location (FR-005)

**File**: `custom_components/buderus_wps/coordinator.py`
**Current**: Cache at `/tmp/buderus_wps_elements.json`
**Required**: Cache at `/config/buderus_wps_elements.json` (HA persistent storage)

### Change 4: Parameter Availability Tracking (FR-011)

**File**: `buderus_wps/parameter.py`
**Current**: All parameters considered available (may use static idx)
**Required**: Track which parameters have discovered/cached idx, mark others unavailable

### Change 5: New Exception Type

**File**: `buderus_wps/exceptions.py`
**Add**: `DiscoveryRequiredError` for when discovery fails without valid cache
