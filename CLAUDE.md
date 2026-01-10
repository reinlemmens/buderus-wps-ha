# buderus-wps-ha Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-24

## Active Technologies
- Python 3.9+ (per constitution for Home Assistant compatibility) + Python standard library only (typing, dataclasses) (002-buderus-wps-python-class)
- Python 3.9+ (Home Assistant compatibility, per constitution) + pyserial (existing), struct (stdlib), json (stdlib for cache) (002-buderus-wps-python-class)
- JSON file for parameter cache (filesystem-based, portable) (002-buderus-wps-python-class)
- Python 3.9+ (Home Assistant compatibility requirement) + homeassistant, pyserial (existing) (017-dhw-setpoint-temp)
- N/A (reads/writes to heat pump via CAN bus) (017-dhw-setpoint-temp)

## Project Structure
```
src/
tests/
```

## Commands
cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style
Python 3.9+ (per constitution for Home Assistant compatibility): Follow standard conventions

## Recent Changes
- 017-dhw-setpoint-temp: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]
- 017-dhw-setpoint-temp: Added Python 3.9+ (Home Assistant compatibility requirement) + homeassistant, pyserial (existing)
- 002-buderus-wps-python-class: Added Python 3.9+ (Home Assistant compatibility, per constitution) + pyserial (existing), struct (stdlib), json (stdlib for cache)

<!-- MANUAL ADDITIONS START -->

## Home Assistant Deployment

4. **Reload or restart** HA:
   ```bash
   # Reload automations only:
   source hass-env.sh && curl -X POST -H "Authorization: Bearer $HASS_TOKEN" "$HASS_SERVER/api/services/automation/reload"

   # Full restart:
   ssh -p 22 hassio@homeassistant.local "bash -l -c 'ha core restart'"
   ```

5. **Commit and push** to git after verifying changes work

## Quick Commands

```bash
# SSH access
ssh -p 22 hassio@homeassistant.local

# Supervisor CLI (requires login shell)
ssh -p 22 hassio@homeassistant.local "bash -l -c 'ha <command>'"

# Local hass-cli
source hass-env.sh && hass-cli state list
```

## Sensitive Files (not in git)

- `hass-env.sh` - Contains `HASS_SERVER` and `HASS_TOKEN`

<!-- MANUAL ADDITIONS END -->
