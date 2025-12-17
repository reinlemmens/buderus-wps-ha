# CRITICAL: HACS Deployment Process

## DO NOT Modify HA Integration Files Directly!

The Home Assistant integration at `/config/custom_components/buderus_wps/` is managed by HACS.

**❌ NEVER DO THIS:**
```bash
# DO NOT copy files directly to /config/custom_components/buderus_wps/
rsync ... /config/custom_components/buderus_wps/
```

**✅ CORRECT PROCESS:**

### 1. Make changes in source repository
All changes go into:
- `/mnt/supervisor/addons/local/buderus-wps-ha/buderus_wps/` (core library)
- `/mnt/supervisor/addons/local/buderus-wps-ha/custom_components/buderus_wps/` (HA integration)

### 2. Commit and push to GitHub
```bash
git add .
git commit -m "fix: correct DHW temperature sensor mapping (idx 58→78)"
git push
```

### 3. Create GitHub Release
Tag the release (e.g., v1.2.0) so HACS can detect it

### 4. Update via HACS in Home Assistant
- Go to HACS → Integrations
- Find "Buderus WPS Heat Pump"
- Click "Update"
- Restart Home Assistant

## Current Fix Status

### Changes Made in Source (Ready to Commit)
✅ `buderus_wps/config.py` - DHW sensor mapping corrected
✅ `buderus_wps/broadcast_monitor.py` - Broadcast mappings updated
✅ `custom_components/buderus_wps/coordinator.py` - Debug logging added

### Files Incorrectly Modified (Need to Revert)
❌ `/config/custom_components/buderus_wps/config.py` - REVERT
❌ `/config/custom_components/buderus_wps/broadcast_monitor.py` - REVERT
❌ `/config/custom_components/buderus_wps/coordinator.py` - REVERT

## Testing Before Release

Use the testing environment at `~/buderus-testing/` on homeassistant.local:
```bash
ssh hassio@homeassistant.local
cd ~/buderus-testing
source venv/bin/activate

# Test with the fixed code
sudo venv/bin/python3 -c "
from buderus_wps.config import get_default_sensor_map
print(get_default_sensor_map())
"
```

## Deployment Checklist

- [ ] All changes committed to source repository
- [ ] Tests pass
- [ ] GitHub release created with version tag
- [ ] HACS repository updated (if first release)
- [ ] Users can update via HACS
- [ ] Release notes document the DHW temp fix

## Why This Matters

HACS tracks integration versions. Direct file modifications:
- Will be overwritten on next HACS update
- Break version tracking
- Confuse users about what version they're running
- Make debugging harder

Always use the proper HACS deployment pipeline!
