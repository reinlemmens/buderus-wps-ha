#!/bin/bash
# Deploy beta release to Home Assistant without HACS
#
# Usage: ./scripts/deploy-beta.sh [--restart]
#
# This script:
# 1. Builds the release zip from custom_components/buderus_wps/
# 2. Transfers it to the HA host via SSH pipe (SCP doesn't work on HA OS)
# 3. Removes the old integration and extracts the new one
# 4. Optionally restarts HA Core
#
# Requires SSH access to hassio@homeassistant.local with sudo privileges

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HA_HOST="hassio@homeassistant.local"
REMOTE_TMP="/home/hassio"
INSTALL_DIR="/config/custom_components"

# Get version from manifest.json
VERSION=$(grep '"version"' "$PROJECT_ROOT/custom_components/buderus_wps/manifest.json" | sed 's/.*: "\(.*\)".*/\1/')
ZIP_NAME="buderus-wps-ha-v${VERSION}.zip"
ZIP_PATH="$PROJECT_ROOT/$ZIP_NAME"

echo "=== Buderus WPS Beta Deployment ==="
echo "Version: $VERSION"
echo ""

# Step 1: Bundle library from source
echo "[1/5] Bundling library from source..."
rm -rf "$PROJECT_ROOT/custom_components/buderus_wps/buderus_wps"
cp -r "$PROJECT_ROOT/buderus_wps" "$PROJECT_ROOT/custom_components/buderus_wps/buderus_wps"
echo "      Library bundled from buderus_wps/ to custom_components/buderus_wps/buderus_wps/"

# Step 2: Build the zip
echo "[2/5] Building release zip..."
cd "$PROJECT_ROOT/custom_components"
rm -f "$ZIP_PATH"
zip -r "$ZIP_PATH" buderus_wps/ -x "*.pyc" -x "*__pycache__*" > /dev/null
echo "      Created: $ZIP_NAME ($(du -h "$ZIP_PATH" | cut -f1))"

# Step 3: Cleanup bundled library (source remains in buderus_wps/)
echo "[3/5] Cleaning up bundled library..."
rm -rf "$PROJECT_ROOT/custom_components/buderus_wps/buderus_wps"
echo "      Bundled library removed (source preserved in buderus_wps/)"

# Step 4: Transfer to HA host
echo "[4/5] Transferring to HA host..."
rsync -az "$ZIP_PATH" "$HA_HOST:$REMOTE_TMP/$ZIP_NAME"
echo "      Transferred to $HA_HOST:$REMOTE_TMP/$ZIP_NAME"

# Step 5: Install on HA
echo "[5/5] Installing integration..."
ssh "$HA_HOST" "sudo rm -rf $INSTALL_DIR/buderus_wps && cd $INSTALL_DIR && sudo unzip -o $REMOTE_TMP/$ZIP_NAME > /dev/null"
echo "      Installed to $INSTALL_DIR/buderus_wps/"

# Optional: Restart HA
if [[ "$1" == "--restart" ]]; then
    echo "      Restarting Home Assistant..."
    ssh "$HA_HOST" "bash -l -c 'ha core restart'"
    echo "      Restart command sent. HA will be unavailable for ~1-2 minutes."
else
    echo "      Skipping restart (use --restart to auto-restart)"
    echo ""
    echo "To restart manually:"
    echo "  ./scripts/ha-restart.sh"
    echo "  OR: Settings → System → Restart in HA UI"
fi

echo ""
echo "=== Deployment complete ==="
