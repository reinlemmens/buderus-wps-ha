# Quickstart: Element Discovery Protocol

**Date**: 2026-01-10
**Feature**: 018-element-discovery

## Overview

This feature ensures the Buderus WPS integration correctly reads heat pump parameters by discovering their actual indices at runtime, rather than relying on potentially incorrect static defaults.

## Key Changes

### 1. Fail-Fast on Fresh Install

**Before**: Discovery failure silently uses static defaults → wrong readings
**After**: Discovery failure on fresh install raises clear error → integration won't start with bad data

### 2. Cache-Only Fallback

**Before**: Falls back to static idx values
**After**: Falls back only to last successful discovery cache

### 3. Persistent Cache

**Before**: Cache at `/tmp/` (lost on restart)
**After**: Cache at `/config/` (persists across restarts)

### 4. Parameter Availability

**Before**: All parameters considered available
**After**: Only discovered/cached parameters are available

## Usage

### Normal Operation

No user action required. Discovery runs automatically on first start:

1. Integration starts
2. Discovery protocol queries heat pump for element list
3. Results cached to `/config/buderus_wps_elements.json`
4. Parameter registry updated with discovered indices
5. Subsequent starts load from cache (fast)

### Troubleshooting

**Error: "Discovery required - no valid cache"**

This means:
- First-time setup AND
- Discovery failed (CAN bus issue, heat pump offline, etc.)

**Fix**: Ensure CAN adapter is connected and heat pump is powered on, then restart integration.

**Symptom: Wrong temperature readings (e.g., 0.1°C)**

This means discovery didn't run or cache is stale.

**Fix**:
1. Delete cache: `rm /config/buderus_wps_elements.json`
2. Restart integration
3. Verify discovery completes in logs

### Manual Cache Refresh

To force fresh discovery (e.g., after firmware update):

```bash
# SSH to Home Assistant
rm /config/buderus_wps_elements.json
# Restart integration via UI or:
ha core restart
```

## Development

### Running Tests

```bash
pytest tests/unit/test_element_discovery.py -v
pytest tests/unit/test_parameter.py -v
```

### Verifying Discovery

Check logs for:
```
INFO Element discovery: 2000 elements, 15 indices updated
INFO Updated GT3_TEMP: idx 681 -> 682 (CAN ID 0x0AAC3FE0 -> 0x0AAC7FE0)
```

### Comparing with FHEM

FHEM shows correct values? HA shows wrong values?
→ Discovery likely didn't run. Check for cache file and restart.

## Files Modified

| File | Change |
|------|--------|
| `buderus_wps/element_discovery.py` | Fail-fast, cache-only fallback |
| `buderus_wps/parameter.py` | Availability tracking |
| `buderus_wps/exceptions.py` | New `DiscoveryRequiredError` |
| `custom_components/buderus_wps/coordinator.py` | Cache path change |
| `tests/unit/test_element_discovery.py` | New test cases |
