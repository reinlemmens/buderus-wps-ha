#!/bin/bash
# Post-create setup script for Buderus WPS HA devcontainer
# This runs once when the container is created

set -e

echo "=== Setting up Buderus WPS HA development environment ==="

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install homeassistant voluptuous pyserial pytest pytest-asyncio pytest-cov ruff mypy

# Install project in development mode
echo "Installing buderus-wps-ha in development mode..."
cd /workspaces/buderus-wps-ha
pip install -e .

# Create HA config directory
echo "Creating Home Assistant config directory..."
mkdir -p /config/custom_components

echo "=== Setup complete! ==="
