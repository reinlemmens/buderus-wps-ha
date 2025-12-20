#!/bin/bash
# Restart Home Assistant Core via SSH
#
# Usage: ./scripts/ha-restart.sh
#
# Requires SSH access to hassio@homeassistant.local
# Uses bash -l to load login shell environment (includes supervisor token)

set -e

echo "Restarting Home Assistant Core..."
ssh hassio@homeassistant.local "bash -l -c 'ha core restart'"
echo "Restart command sent. HA will be unavailable for ~1-2 minutes."
