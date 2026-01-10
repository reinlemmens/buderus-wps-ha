# Research: Element Discovery Protocol

**Date**: 2026-01-10
**Feature**: 018-element-discovery

## Research Questions

### Q1: Why do static default idx values produce wrong readings?

**Finding**: Parameter indices (idx) vary between heat pump firmware versions. The static defaults in `parameter_defaults.py` come from FHEM's reference implementation which was captured from one specific firmware version.

**Evidence**:
- GT3_TEMP: static default idx=681, but actual device uses idx=682
- GT10_TEMP/GT11_TEMP: using static idx=638/652 returns 0.1°C instead of correct ~10°C/5°C
- CAN ID is calculated as `0x04003FE0 | (idx << 14)` - wrong idx = wrong CAN ID = wrong/no response

**Decision**: Never use static idx values. Static defaults are valid ONLY for format (data type) and read (writable flag) metadata.

**Alternatives Considered**:
- Hard-code known idx variations per firmware version: Rejected - not scalable, requires firmware detection
- Use extid for CAN addressing: Rejected - CAN protocol requires idx-based addressing

---

### Q2: Where should discovery cache be stored?

**Finding**: Current implementation uses `/tmp/buderus_wps_elements.json` which is ephemeral in Docker containers. Each HA restart loses the cache, forcing full discovery.

**Evidence**:
- SSH to HA: `ls /tmp/*buderus*` returns empty - cache was lost
- HA container uses ephemeral `/tmp` - cleared on restart
- Discovery takes ~30 seconds, cache load takes <1 second

**Decision**: Use `/config/buderus_wps_elements.json` - HA's persistent configuration directory.

**Alternatives Considered**:
- `/homeassistant/` directory: Works but less standard
- Integration-specific subdirectory: More complex, no clear benefit
- In-memory only: Would require discovery on every restart

---

### Q3: How should discovery failure be handled?

**Finding**: Current implementation silently falls back to static defaults, which produces incorrect readings without any user-visible error.

**Evidence**:
- FHEM runs discovery on every startup and uses discovered values
- HA coordinator catches discovery exceptions and continues with static defaults
- Users see readings like 0.1°C and assume the sensor is faulty

**Decision**: Fail-fast on fresh install (no cache), cache-only fallback otherwise.

**Behavior Matrix**:

| Scenario | Current Behavior | New Behavior |
|----------|-----------------|--------------|
| Fresh install, discovery succeeds | Works | Works |
| Fresh install, discovery fails | Silent wrong readings | Clear error, no start |
| Existing cache, discovery succeeds | Works | Works |
| Existing cache, discovery fails | Silent wrong readings | Use cached values |

**Alternatives Considered**:
- Always fail on discovery failure: Too strict - existing cache is valid
- Warn but continue with static: Still produces wrong readings
- Partial discovery + static fill: Complex, still has wrong readings for missing params

---

### Q4: How to track parameter availability?

**Finding**: Need to distinguish between parameters with discovered/cached idx vs those only in static defaults.

**Implementation Options**:

1. **Separate registry for discovered parameters**
   - Pro: Clear separation
   - Con: Duplicate lookups, complex

2. **Add `idx_source` field to Parameter class**
   - Pro: Single registry, clear tracking
   - Con: Changes immutable dataclass

3. **Use `_discovered_names` set in HeatPump class**
   - Pro: Minimal changes, fast O(1) lookup
   - Con: Another data structure to maintain

**Decision**: Option 3 - Add `_discovered_names: Set[str]` to HeatPump class. Check membership before allowing reads.

---

### Q5: FHEM protocol compatibility verification

**Finding**: Current implementation matches FHEM protocol exactly.

**FHEM Protocol (from 26_KM273v018.pm)**:
```
1. Request element count: RTR to 0x01FD7FE0 → Response from 0x09FD7FE0 (4 bytes, big-endian count)
2. Request data: T01FD3FE0 + (size:4B + offset:4B) → Stream from 0x09FDBFE0
3. Element format: idx(2B) + extid(7B) + max(4B) + min(4B) + name_len(1B) + name
```

**HA Implementation (element_discovery.py)**:
- CAN IDs: Match exactly (0x01FD7FE0, 0x09FD7FE0, 0x01FD3FE0, 0x09FDBFE0)
- Header parsing: Match exactly (18 bytes + variable name)
- Chunk size: 4096 bytes (matches FHEM)

**Decision**: No protocol changes needed. Discovery mechanism is correct.

---

## Summary of Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Static idx usage | Never for addressing | Produces wrong readings on different firmware |
| Cache location | `/config/` | Persistent across HA restarts |
| Discovery failure | Fail-fast (fresh) / cache fallback | Prevents silent wrong readings |
| Availability tracking | `_discovered_names` set | Minimal code changes, O(1) lookup |
| Protocol | No changes | Already matches FHEM exactly |
