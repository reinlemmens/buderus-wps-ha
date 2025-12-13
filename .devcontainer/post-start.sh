#!/bin/bash
# Post-start script for Buderus WPS HA devcontainer
# This runs each time the container starts

set -e

WORKSPACE="/workspaces/buderus-wps-ha"

echo "=== Configuring Home Assistant environment ==="

# Ensure config directory exists
mkdir -p /config/custom_components

# Link our custom component (recreate on each start to handle updates)
rm -f /config/custom_components/buderus_wps
ln -sf "${WORKSPACE}/custom_components/buderus_wps" /config/custom_components/buderus_wps

# Copy default configuration if not exists
if [ ! -f "/config/configuration.yaml" ]; then
    echo "Creating default configuration.yaml..."
    cp "${WORKSPACE}/.devcontainer/config/configuration.yaml" /config/configuration.yaml
fi

echo "=== Environment ready ==="
echo ""
echo "Commands:"
echo "  Start HA:    hass -c /config"
echo "  Run tests:   pytest tests/"
echo "  Type check:  mypy buderus_wps buderus_wps_cli"
echo "  Lint:        ruff check ."
echo ""
echo "Home Assistant will be available at http://localhost:8123"
