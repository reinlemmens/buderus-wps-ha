#!/bin/bash
# Run Home Assistant integration tests only
#
# This script runs all tests related to the Home Assistant custom component,
# including unit, integration, and acceptance tests for HA entities.
# All tests use comprehensive mocks - no physical hardware required.
#
# Usage: ./scripts/test-ha.sh [pytest args]
# Example: ./scripts/test-ha.sh -v
# Example: ./scripts/test-ha.sh -k "test_switch"

set -e

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Use venv pytest if available, otherwise system pytest
if [ -f "venv/bin/pytest" ]; then
    PYTEST="./venv/bin/pytest"
else
    PYTEST="pytest"
fi

echo "Running Home Assistant integration tests..."
echo ""

$PYTEST \
    tests/unit/test_ha_*.py \
    tests/integration/test_ha_*.py \
    tests/acceptance/test_ha_*.py \
    "$@"
