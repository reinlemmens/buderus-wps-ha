#!/bin/bash
# Safe diagnostic run with USB disconnect/reconnect

set -e

echo "========================================================================"
echo "BUDERUS WPS GT10/GT11 DIAGNOSTIC - USB SAFE MODE"
echo "========================================================================"

echo ""
echo "[1/5] Stopping Home Assistant to release USB device..."
ssh hassio@homeassistant.local "ha core stop"
echo "✓ Home Assistant stopped"
sleep 5

echo ""
echo "[2/5] Verifying USB device is available..."
if ssh hassio@homeassistant.local "test -e /dev/ttyACM0"; then
    echo "✓ USB device found at /dev/ttyACM0"
else
    echo "✗ ERROR: USB device not found!"
    echo "Restarting Home Assistant..."
    ssh hassio@homeassistant.local "ha core start"
    exit 1
fi

echo ""
echo "[3/5] Running diagnostic script..."
echo "--------------------------------------------------------------------"
ssh hassio@homeassistant.local "cd /config/custom_components/buderus_wps && python3 diagnose_brine_temps.py" || {
    echo "✗ Diagnostic failed!"
    echo ""
    echo "[ERROR] Restarting Home Assistant..."
    ssh hassio@homeassistant.local "ha core start"
    exit 1
}
echo "--------------------------------------------------------------------"

echo ""
echo "[4/5] Waiting 5 seconds before restart..."
sleep 5

echo ""
echo "[5/5] Restarting Home Assistant..."
ssh hassio@homeassistant.local "ha core start"
echo "✓ Home Assistant restarting (will take ~30-60 seconds)"

echo ""
echo "========================================================================"
echo "DIAGNOSTIC COMPLETE - Check output above for GT10/GT11 details"
echo "========================================================================"
echo ""
echo "Home Assistant is restarting now. Wait 1-2 minutes before checking."
