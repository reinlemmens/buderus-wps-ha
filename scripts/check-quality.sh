#!/usr/bin/env bash
#
# Run all code quality checks locally
#
# Usage:
#   ./scripts/check-quality.sh          # Run all checks
#   ./scripts/check-quality.sh --fix    # Auto-fix formatting issues
#   ./scripts/check-quality.sh --quick  # Skip tests, only lint/type-check
#
# This script checks both:
#   - buderus_wps/ (library code)
#   - custom_components/buderus_wps/ (HA integration)
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Parse arguments
FIX_MODE=false
QUICK_MODE=false
for arg in "$@"; do
    case $arg in
        --fix)
            FIX_MODE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--fix] [--quick]"
            echo ""
            echo "Options:"
            echo "  --fix    Auto-fix formatting and import issues"
            echo "  --quick  Skip tests, only run lint/type checks"
            echo ""
            exit 0
            ;;
    esac
done

# Track overall status
FAILED=0

log_section() {
    echo ""
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}======================================${NC}"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED=1
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

# Check that we have required tools
check_tool() {
    if ! $PYTHON -m "$1" --version &> /dev/null; then
        echo -e "${RED}Error: $1 not installed. Run: pip install $1${NC}"
        exit 1
    fi
}

check_tool black
check_tool ruff
check_tool mypy

# Paths to check
LIBRARY_PATH="buderus_wps/"
COMPONENT_LIB_PATH="custom_components/buderus_wps/buderus_wps/"
COMPONENT_PATH="custom_components/buderus_wps/"
TESTS_PATH="tests/"

#
# 1. Black Formatter
#
log_section "Black Formatter"

if $FIX_MODE; then
    echo "Running black with auto-fix..."
    if $PYTHON -m black --config pyproject.toml "$LIBRARY_PATH" "$COMPONENT_PATH" "$TESTS_PATH"; then
        log_success "Black formatting applied"
    else
        log_fail "Black formatting failed"
    fi
else
    echo "Checking black formatting..."
    if $PYTHON -m black --check --diff --config pyproject.toml "$LIBRARY_PATH" "$COMPONENT_PATH" "$TESTS_PATH"; then
        log_success "Black formatting OK"
    else
        log_fail "Black formatting issues found (run with --fix to auto-fix)"
    fi
fi

#
# 2. Ruff Linter
#
log_section "Ruff Linter"

if $FIX_MODE; then
    echo "Running ruff with auto-fix..."
    if $PYTHON -m ruff check --fix --config pyproject.toml "$LIBRARY_PATH" "$COMPONENT_PATH" "$TESTS_PATH"; then
        log_success "Ruff linting passed (auto-fixed where possible)"
    else
        log_fail "Ruff linting issues remain after auto-fix"
    fi
else
    echo "Checking ruff linting..."
    if $PYTHON -m ruff check --config pyproject.toml "$LIBRARY_PATH" "$COMPONENT_PATH" "$TESTS_PATH"; then
        log_success "Ruff linting OK"
    else
        log_fail "Ruff linting issues found"
    fi
fi

#
# 3. Mypy Type Checking
#
log_section "Mypy Type Checker"

echo "Type checking library ($LIBRARY_PATH)..."
if $PYTHON -m mypy "$LIBRARY_PATH" --config-file pyproject.toml; then
    log_success "Library type check OK"
else
    log_fail "Library type check failed"
fi

echo ""
echo "Type checking custom component library ($COMPONENT_LIB_PATH)..."
if $PYTHON -m mypy "$COMPONENT_LIB_PATH" --config-file pyproject.toml; then
    log_success "Custom component library type check OK"
else
    log_fail "Custom component library type check failed"
fi

#
# 4. Tests (unless --quick)
#
if ! $QUICK_MODE; then
    log_section "Tests"

    echo "Running tests (excluding hardware-in-loop)..."
    if $PYTHON -m pytest tests/ --ignore=tests/hil/ -q; then
        log_success "All tests passed"
    else
        log_fail "Some tests failed"
    fi
else
    log_section "Tests (Skipped)"
    log_warn "Tests skipped due to --quick flag"
fi

#
# Summary
#
log_section "Summary"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All quality checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Some quality checks failed. Please fix the issues above.${NC}"
    exit 1
fi
