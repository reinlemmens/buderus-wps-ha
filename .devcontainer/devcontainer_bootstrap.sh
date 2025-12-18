#!/bin/bash
set -e

echo "=================================================="
echo "Buderus WPS Development Environment Setup"
echo "=================================================="
echo ""

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel --quiet

# Install project in editable mode with all dev dependencies
echo "📚 Installing project dependencies..."
pip install -e ".[dev]" --quiet

# Install Home Assistant for integration testing
echo "🏠 Installing Home Assistant for testing..."
pip install homeassistant>=2024.3.0 --quiet

echo ""
echo "=================================================="
echo "✅ Development environment ready!"
echo "=================================================="
echo ""
echo "Virtual environment is activated. To run tests:"
echo "  pytest tests/unit/           # Unit tests only"
echo "  pytest tests/integration/    # Integration tests (mocked hardware)"
echo "  pytest tests/acceptance/     # Acceptance tests"
echo "  pytest --ignore=tests/hil/   # All tests except hardware-in-loop"
echo "  RUN_HIL_TESTS=1 pytest tests/hil/  # Hardware tests (requires USB device)"
echo ""
echo "Convenience scripts:"
echo "  ./scripts/test-all.sh        # Run all non-HIL tests"
echo "  ./scripts/test-ha.sh         # Run only Home Assistant tests"
echo "  ./scripts/test-hil.sh        # Run hardware-in-loop tests"
echo ""
echo "See DEVELOPMENT.md for complete documentation"
echo "=================================================="
