#!/bin/bash
# Run all tests except hardware-in-loop (HIL)
#
# This script runs all unit, integration, contract, and acceptance tests
# with comprehensive mocks. No physical hardware required.
#
# Usage: ./scripts/test-all.sh [pytest args]
# Example: ./scripts/test-all.sh -v
# Example: ./scripts/test-all.sh -k "test_temperature"

set -e

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Use venv pytest if available, otherwise system pytest
if [ -f "venv/bin/pytest" ]; then
    PYTEST="./venv/bin/pytest"
else
    PYTEST="pytest"
fi

echo "Running all tests (excluding hardware-in-loop)..."
echo ""

$PYTEST --ignore=tests/hil/ "$@"
