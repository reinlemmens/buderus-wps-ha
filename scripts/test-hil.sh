#!/bin/bash
# Run hardware-in-loop (HIL) tests
#
# These tests require physical hardware:
# - USBtin CAN adapter at /dev/ttyACM0 (or set USBTIN_PORT env var)
# - Buderus WPS heat pump on CAN bus
#
# Usage: ./scripts/test-hil.sh [pytest args]
# Example: ./scripts/test-hil.sh -v
# Example: USBTIN_PORT=/dev/ttyUSB0 ./scripts/test-hil.sh

set -e

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Use venv pytest if available, otherwise system pytest
if [ -f "venv/bin/pytest" ]; then
    PYTEST="./venv/bin/pytest"
else
    PYTEST="pytest"
fi

# Check if hardware is available
USBTIN_PORT=${USBTIN_PORT:-/dev/ttyACM0}

if [ ! -e "$USBTIN_PORT" ]; then
    echo "⚠️  WARNING: USB device not found at $USBTIN_PORT"
    echo ""
    echo "Hardware-in-loop tests require:"
    echo "  - USBtin CAN adapter connected"
    echo "  - Buderus WPS heat pump on CAN bus"
    echo ""
    echo "If your device is at a different path, set USBTIN_PORT:"
    echo "  USBTIN_PORT=/dev/ttyUSB0 ./scripts/test-hil.sh"
    echo ""
    echo "Tests will be skipped if hardware is not available."
    echo ""
fi

echo "Running hardware-in-loop tests..."
echo "Device: $USBTIN_PORT"
echo ""

RUN_HIL_TESTS=1 $PYTEST tests/hil/ "$@"
