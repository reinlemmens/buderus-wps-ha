# Feature Specification: Indefinite Last-Known-Good Data Caching Implementation

**Feature Branch**: `016-indefinite-caching-implementation`
**Created**: 2025-12-17
**Status**: In Progress
**Parent Spec**: [011-ha-integration](../011-ha-integration/spec.md)

## Overview

Implement indefinite last-known-good data caching for the Home Assistant integration to eliminate "Unknown" sensor states when CAN bus communication is temporarily unavailable.

**Parent Requirements**: See [011-ha-integration/spec.md](../011-ha-integration/spec.md) FR-007 and FR-011

## User Story - Indefinite Data Retention (Priority: P1)

As a homeowner, I want my Home Assistant sensors to continue showing the last known values (with staleness indicators) when the heat pump communication is temporarily interrupted, so that I don't lose visibility into slow-changing values like temperatures.

**Why this priority**: Seeing "Unknown" instead of slightly stale temperature data is inconvenient and loses valuable information. Heat pump values change slowly, making stale data more useful than no data.

**Independent Test**: Can be fully tested by simulating 5+ consecutive CAN bus timeouts and verifying sensors retain their last values with staleness attributes.

**Acceptance Scenarios**:

1. **Given** sensors have successful readings, **When** 5+ consecutive CAN bus fetch failures occur, **Then** sensors continue showing last known values (not "Unknown")
2. **Given** cached data is being shown, **When** I view sensor attributes, **Then** I see `last_update_age_seconds`, `last_successful_update` timestamp, and `data_is_stale: true`
3. **Given** stale data is showing, **When** CAN bus communication recovers, **Then** sensors update to fresh values and `data_is_stale` changes to `false`
4. **Given** the integration has never successfully read data, **When** I view sensors, **Then** they show "unavailable" (no cache exists yet)

## Requirements

### Functional Requirements

- **FR-001**: Coordinator MUST remove the 3-failure threshold (`_stale_data_threshold`)
- **FR-002**: Coordinator MUST always return `_last_known_good_data` when available, never abandoning cache
- **FR-003**: Coordinator MUST provide `get_data_age_seconds()` helper method
- **FR-004**: Coordinator MUST provide `is_data_stale()` helper method
- **FR-005**: Entity base class MUST add `extra_state_attributes` property with staleness metadata
- **FR-006**: All sensor entities MUST inherit staleness attributes from base class
- **FR-007**: Tests MUST verify indefinite caching behavior (5+ failures scenario)
- **FR-008**: Tests MUST verify staleness attributes are present and accurate

### Success Criteria

- **SC-001**: After 10 consecutive CAN bus failures, sensors still show last known values
- **SC-002**: Entity attributes show accurate staleness metadata (age, timestamp, boolean flag)
- **SC-003**: All existing tests continue to pass
- **SC-004**: New tests verify indefinite caching and staleness attributes
- **SC-005**: No memory leaks from indefinite cache retention (cache is single BuderusData object)

## Implementation Scope

### In Scope
- Remove 3-failure threshold from coordinator
- Update error handling to always return cached data
- Add staleness helper methods to coordinator
- Add staleness attributes to entity base class
- Update integration tests for indefinite caching
- Update acceptance tests to match new spec

### Out of Scope
- Changes to sensor/binary_sensor/switch/number entity files (no changes needed)
- UI configuration flow (YAML only per parent spec)
- Alternative caching strategies (indefinite retention is the chosen approach)
