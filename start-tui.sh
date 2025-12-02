#!/bin/bash
# Start the Buderus WPS TUI
#
# Usage: ./start-tui.sh [device] [options]
#   device: USB serial device path (default: /dev/ttyACM0)
#   --read-only: Disable write operations
#   --verbose: Enable verbose logging

cd "$(dirname "$0")"

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the TUI
python -m buderus_wps_cli.tui.app "$@"
