# Quickstart: HACS Publishing Validation

**Feature**: 014-hacs-publishing
**Date**: 2025-12-15

## Prerequisites

- GitHub repository is public
- HACS installed on a Home Assistant instance (for testing)
- Access to create GitHub releases

## Step 1: Create hacs.json

Create `hacs.json` in the repository root:

```json
{
  "name": "Buderus WPS Heat Pump",
  "render_readme": true
}
```

Validate JSON:
```bash
python -c "import json; json.load(open('hacs.json'))" && echo "Valid JSON"
```

## Step 2: Verify manifest.json

Check all required fields are present:

```bash
python3 -c "
import json
manifest = json.load(open('custom_components/buderus_wps/manifest.json'))
required = ['domain', 'name', 'codeowners', 'documentation', 'issue_tracker', 'version']
missing = [f for f in required if f not in manifest]
if missing:
    print(f'Missing fields: {missing}')
else:
    print('All required fields present')
    for f in required:
        print(f'  {f}: {manifest[f]}')
"
```

## Step 3: Update README with HACS Badge

Add to the top of README.md:

```markdown
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
```

Add HACS installation section:

```markdown
## Installation via HACS

1. Open HACS in your Home Assistant instance
2. Click the three dots in the top right corner
3. Select "Custom repositories"
4. Add repository URL: `https://github.com/reinlemmens/buderus-wps-ha`
5. Select category: "Integration"
6. Click "Add"
7. Search for "Buderus WPS" and install
8. Restart Home Assistant
9. Add integration via Settings → Devices & Services → Add Integration → Buderus WPS
```

## Step 4: Commit and Push

```bash
git add hacs.json README.md
git commit -m "feat: add HACS support for integration distribution"
git push origin main
```

## Step 5: Create GitHub Release

### Via GitHub UI:
1. Go to repository → Releases → "Create a new release"
2. Tag: `v1.0.0`
3. Title: `v1.0.0 - Initial HACS Release`
4. Description: Release notes with features and installation
5. Click "Publish release"

### Via GitHub CLI:
```bash
gh release create v1.0.0 \
  --title "v1.0.0 - Initial HACS Release" \
  --notes "## Buderus WPS Heat Pump Integration

First release compatible with HACS installation.

### Features
- Temperature sensors (Outdoor, Supply, Return, DHW, Brine)
- Compressor status monitoring
- Energy blocking control
- DHW extra production control

### Installation via HACS
1. Add this repository as a custom repository in HACS
2. Search for 'Buderus WPS'
3. Install and restart Home Assistant
4. Add integration via Settings → Devices & Services"
```

## Step 6: Test HACS Installation

### Add as Custom Repository:
1. Open Home Assistant
2. Navigate to HACS → Integrations
3. Click three-dot menu → "Custom repositories"
4. Enter: `https://github.com/reinlemmens/buderus-wps-ha`
5. Category: "Integration"
6. Click "Add"

### Verify:
- [ ] No validation errors appear
- [ ] Integration shows in HACS with correct name
- [ ] Version matches manifest.json (1.0.0)
- [ ] README renders correctly (if `render_readme: true`)
- [ ] Documentation link works
- [ ] "Install" button is available

### Test Install:
1. Click on the integration in HACS
2. Click "Download"
3. Select version (v1.0.0)
4. Click "Download"
5. Restart Home Assistant when prompted

### Verify Installation:
- [ ] Files appear in `config/custom_components/buderus_wps/`
- [ ] Integration available in Settings → Devices & Services → Add Integration
- [ ] Integration configures successfully

## Step 7: Optional - Submit Branding

### Fork and Clone home-assistant/brands:
```bash
gh repo fork home-assistant/brands --clone
cd brands
```

### Create Integration Directory:
```bash
mkdir -p custom_integrations/buderus_wps
cp /path/to/buderus-wps-ha/custom_components/buderus_wps/branding/icon.png custom_integrations/buderus_wps/
cp /path/to/buderus-wps-ha/custom_components/buderus_wps/branding/icon@2x.png custom_integrations/buderus_wps/
```

### Commit and Create PR:
```bash
git add custom_integrations/buderus_wps/
git commit -m "Add buderus_wps integration branding"
git push origin main
gh pr create --title "Add Buderus WPS Heat Pump branding" \
  --body "Adds icon for the Buderus WPS Heat Pump custom integration.

Integration repository: https://github.com/reinlemmens/buderus-wps-ha

Icon represents a heat pump unit with Buderus brand colors."
```

## Troubleshooting

### HACS Validation Errors

**"Invalid manifest.json"**:
- Check JSON syntax: `python -c "import json; json.load(open('custom_components/buderus_wps/manifest.json'))"`
- Verify required fields are present

**"Repository structure invalid"**:
- Ensure `custom_components/buderus_wps/` exists
- Verify `__init__.py` is present in the directory

**"Version mismatch"**:
- Ensure release tag version matches manifest.json version
- Use `v1.0.0` tag format (with 'v' prefix)

### Installation Issues

**"Integration not loading"**:
- Check Home Assistant logs: Settings → System → Logs
- Verify dependencies installed: `pip list | grep pyserial`

**"Configuration failed"**:
- Verify serial port exists: `ls /dev/tty*`
- Check USB permissions: `sudo usermod -a -G dialout homeassistant`

## Success Criteria

- [x] `hacs.json` created and valid
- [x] README updated with HACS badge and instructions
- [x] GitHub release v1.0.0 created
- [ ] HACS validation passes (0 errors)
- [ ] Integration installs via HACS
- [ ] Integration configures successfully after HACS install
