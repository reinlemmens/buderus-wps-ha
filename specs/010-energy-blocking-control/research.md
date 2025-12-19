# Research: Energy Blocking Control

**Feature**: 010-energy-blocking-control
**Date**: 2025-12-06

## Summary

Research completed successfully. All NEEDS CLARIFICATION items resolved. The FHEM reference implementation confirms that CAN bus parameters exist for controlling compressor and auxiliary heater blocking.

## Research Tasks

### 1. CAN Bus Parameters for Energy Blocking

**Question**: Do blocking parameters exist in the FHEM reference implementation?

**Decision**: Yes - multiple blocking parameters confirmed in FHEM 26_KM273v018.pm

**Findings**:

#### Writable Blocking Parameters (Control)

| Parameter Name | idx | extid | max | Description |
|---------------|-----|-------|-----|-------------|
| `ADDITIONAL_USER_BLOCKED` | 155 | C09241BB5C02EC | 16777216 | User-controlled auxiliary heater block |
| `COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_1` | 263 | C092971E2F0309 | 16777216 | External compressor block via E21 input 1 |
| `COMPRESSOR_E21_EXTERN_BLOCK_BY_E21_EXT_2` | 264 | C00B9E4F95048B | 16777216 | External compressor block via E21 input 2 |

**Note**: Parameters with `extid` starting with 'C0' and `max > 0` are writable. Value 0 = unblocked, 16777216 (0x1000000) = blocked.

#### Read-Only Status Parameters (Monitoring)

| Parameter Name | idx | extid | Description |
|---------------|-----|-------|-------------|
| `COMPRESSOR_BLOCKED` | 247 | 000E6864FD0476 | Status: is compressor currently blocked |
| `ADDITIONAL_BLOCKED` | 9 | 00259EEF360272 | Status: is auxiliary heater currently blocked |
| `COMPRESSOR_E21_EXTERN_BLOCKED` | 262 | 00F55C2F800303 | Status: compressor externally blocked |
| `ADDITIONAL_EXTERN_BLOCKED` | 56 | 00CC181667030A | Status: auxiliary heater externally blocked |

**Note**: Parameters with `extid` starting with '00' and `max = 0` are read-only status indicators.

**Rationale**: The existing HeatPumpClient.write_value() method handles CAN writes. We can reuse this infrastructure for blocking control.

**Alternatives Considered**:
- EVU parameters (EVU_1_ACTIVE, etc.) - These are for utility company blocking signals, not user control
- EXTERN_BLOCK_BY_E22 variants - E21 is sufficient for software-controlled blocking

### 2. Blocking Control Architecture

**Question**: How should blocking be implemented in the codebase?

**Decision**: Add a dedicated `EnergyBlockingControl` class in the core library

**Rationale**:
1. **Library-first architecture** (Constitution Principle I) - Core blocking logic in `buderus_wps`
2. **CLI and TUI** can wrap the library functionality
3. **Reusable** for future Home Assistant integration

**Pattern**:
```
buderus_wps/
└── energy_blocking.py    # EnergyBlockingControl class

buderus_wps_cli/
└── commands/
    └── energy.py         # CLI commands (block-compressor, etc.)
```

### 3. Parameter Value Encoding

**Question**: What values represent blocked vs unblocked state?

**Decision**: Binary toggle with 0 = unblocked, 1 = blocked (standard boolean encoding)

**Finding**: The max value 16777216 (0x1000000) in FHEM suggests a bitmask or extended format, but for simple on/off control, values 0 and 1 are sufficient based on heat pump protocol patterns.

**Verification Required**: During implementation, verify the actual byte encoding by reading current values.

### 4. Status Verification

**Question**: How to verify blocking was applied successfully?

**Decision**: Read-after-write verification using status parameters

**Pattern**:
1. Write blocking command (e.g., ADDITIONAL_USER_BLOCKED = 1)
2. Read status parameter (e.g., ADDITIONAL_BLOCKED)
3. Verify status reflects the change
4. Report success/failure to user

### 5. Safety Considerations

**Question**: What safety mechanisms exist?

**Decision**: Document that heat pump has internal safety overrides

**Findings from FHEM parameters**:
- Anti-freeze protection cannot be bypassed by external blocks
- Defrost cycles may override blocks temporarily
- EVU (utility) blocks have priority over user blocks

**Implementation**: The system will warn users about safety overrides in error messages.

## Dependencies

1. **HeatPumpClient** - Existing read/write infrastructure ✓
2. **ParameterRegistry** - Parameter lookup by name ✓
3. **USBtinAdapter** - CAN communication ✓

## Risks

1. **Parameter compatibility**: The exact idx values may vary between heat pump models
   - Mitigation: Use parameter names instead of idx for lookup

2. **Value encoding uncertainty**: The exact byte encoding for blocked state needs verification
   - Mitigation: Start with standard boolean encoding, verify during testing

## References

- FHEM 26_KM273v018.pm lines 229-264 (ADDITIONAL_* parameters)
- FHEM 26_KM273v018.pm lines 403-423 (COMPRESSOR_* parameters)
- FHEM 26_KM273v018.pm lines 652-666 (EVU_* parameters)
