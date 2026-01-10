#!/bin/bash
set -e

echo "=================================================="
echo "Buderus WPS Development Environment Setup"
echo "=================================================="
echo ""

# Fix Claude config permissions (mounted directories default to root)
if [ -d "/home/vscode/.config/claude" ]; then
    echo "🔧 Fixing Claude config permissions..."
    sudo chown -R vscode:vscode /home/vscode/.config/claude
    echo "✓ Claude config permissions fixed"
fi
echo ""

# Setup SSH keys for Home Assistant access (persisted in .devcontainer/ssh/)
if [ -f ".devcontainer/ssh/id_ed25519" ]; then
    echo "🔑 Setting up SSH keys for Home Assistant..."
    mkdir -p ~/.ssh
    ln -sf "$(pwd)/.devcontainer/ssh/id_ed25519" ~/.ssh/id_ed25519
    ln -sf "$(pwd)/.devcontainer/ssh/id_ed25519.pub" ~/.ssh/id_ed25519.pub
    chmod 600 .devcontainer/ssh/id_ed25519
    # Add Home Assistant host key if not present
    ssh-keyscan -H homeassistant.local >> ~/.ssh/known_hosts 2>/dev/null || true
    echo "✓ SSH keys configured for homeassistant.local"
else
    echo "⚠️  No SSH keys found in .devcontainer/ssh/ - run scripts on HA directly"
fi
echo ""

# Install Python if not present
if ! command -v python3 &> /dev/null; then
    echo "🐍 Installing Python 3..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq python3 python3-venv python3-pip > /dev/null
    echo "✓ Python 3 installed"
else
    echo "✓ Python 3 already installed"
fi
echo ""

# Install GitHub CLI if not present
if ! command -v gh &> /dev/null; then
    echo "📦 Installing GitHub CLI..."
    ARCH=$(dpkg --print-architecture)
    wget -q "https://github.com/cli/cli/releases/download/v2.40.1/gh_2.40.1_linux_${ARCH}.deb" -O /tmp/gh.deb
    sudo dpkg -i /tmp/gh.deb 2>&1 | grep -v "Setting up\|Processing triggers" || true
    rm /tmp/gh.deb
    echo "✓ GitHub CLI installed"
else
    echo "✓ GitHub CLI already installed"
fi
echo ""

# Create venv if it doesn't exist or is corrupted
if [ -d "venv" ] && [ -x "venv/bin/python" ]; then
    # Verify venv is functional
    if venv/bin/python --version &>/dev/null; then
        echo "✓ Virtual environment already exists and is valid"
    else
        echo "⚠️  Virtual environment is corrupted, recreating..."
        rm -rf venv
        python3 -m venv venv
    fi
else
    if [ -d "venv" ]; then
        echo "⚠️  Virtual environment is corrupted, recreating..."
        rm -rf venv
    fi
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
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
