# Home Assistant E2E Testing Guide

## SSH Access to Production HA Instance

**Connection Details**:
- Host: `homeassistant.local`
- User: `hassio` (NOT root)
- Command: `ssh hassio@homeassistant.local`

## E2E Validation Process

### 1. Connect to HA Instance
```bash
ssh hassio@homeassistant.local
```

### 2. Install Release Artifact
```bash
# On homeassistant.local:
cd /config/custom_components/
rm -rf buderus_wps

# Copy release zip from dev machine (run from devcontainer):
scp buderus-wps-ha.zip hassio@homeassistant.local:/tmp/

# On homeassistant.local:
cd /tmp
unzip -q buderus-wps-ha.zip
cp -r custom_components/buderus_wps /config/custom_components/
rm -rf custom_components buderus-wps-ha.zip
```

### 3. Restart Home Assistant
```bash
# On homeassistant.local:
ha core restart
```

### 4. Check Logs
```bash
# On homeassistant.local:
ha core logs | grep -i buderus_wps
# OR
tail -f /config/home-assistant.log | grep buderus_wps
```

### 5. Validation Checklist
- [ ] No ModuleNotFoundError in logs
- [ ] No AttributeError in logs
- [ ] Integration loads successfully
- [ ] All entities appear in UI
- [ ] Entity attributes include staleness metadata
- [ ] Test switches/controls work

## Quick Test Commands

```bash
# One-liner to copy and install release:
scp buderus-wps-ha.zip hassio@homeassistant.local:/tmp/ && \
ssh hassio@homeassistant.local "cd /tmp && unzip -q buderus-wps-ha.zip && rm -rf /config/custom_components/buderus_wps && cp -r custom_components/buderus_wps /config/custom_components/ && rm -rf custom_components buderus-wps-ha.zip && ha core restart"
```

## Notes
- Always test the ACTUAL release zip file, not development directory
- Wait 30-60 seconds after restart for HA to fully initialize
- Check logs immediately after restart for import errors
