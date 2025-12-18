#!/usr/bin/env bash
#
# Build HACS-compatible release with bundled buderus_wps library
#
# Usage:
#   ./scripts/build-release.sh v1.2.0-beta.4
#   ./scripts/build-release.sh v1.2.0
#
# This script:
# 1. Creates staging directory with integration + bundled library
# 2. Updates imports to use bundled library (relative imports)
# 3. Creates GitHub release with packaged zip
# 4. Cleans up staging directory
#
# The source tree remains unchanged - all bundling happens in staging.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
STAGING=".build/release"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

#
# Helper Functions
#

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

die() {
    log_error "$1"
    exit 1
}

validate_version() {
    local version="$1"
    # Check semver format (v1.2.3 or v1.2.3-beta.4)
    if ! [[ "$version" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
        die "Invalid version format: $version. Expected vX.Y.Z or vX.Y.Z-beta.N"
    fi
    log_info "Version format valid: $version"
}

check_git_clean() {
    if [ -n "$(git status --porcelain)" ]; then
        log_warn "Git working tree has uncommitted changes"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            die "Aborted by user"
        fi
    else
        log_info "Git working tree is clean"
    fi
}

verify_manifest_version() {
    local version="$1"
    local manifest_version
    manifest_version=$(grep -o '"version": "[^"]*"' custom_components/buderus_wps/manifest.json | cut -d'"' -f4)

    log_info "Manifest version: $manifest_version"
    log_info "Release version: ${version#v}"

    if [ "$manifest_version" != "${version#v}" ]; then
        log_warn "manifest.json version ($manifest_version) doesn't match release version (${version#v})"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            die "Aborted by user. Update manifest.json version first."
        fi
    else
        log_info "Manifest version matches release version"
    fi
}

copy_integration() {
    log_info "Copying integration files to staging..."
    mkdir -p "$STAGING/custom_components"
    cp -r custom_components/buderus_wps "$STAGING/custom_components/"
    log_info "Integration files copied"
}

bundle_library() {
    log_info "Bundling buderus_wps library..."
    cp -r buderus_wps "$STAGING/custom_components/buderus_wps/"

    # Count files
    local file_count
    file_count=$(find "$STAGING/custom_components/buderus_wps/buderus_wps" -name "*.py" | wc -l)
    log_info "Bundled $file_count Python library files"
}

patch_coordinator_imports() {
    local coordinator_file="$STAGING/custom_components/buderus_wps/coordinator.py"
    log_info "Patching coordinator.py imports..."

    # Create a temporary file with the new import section
    cat > /tmp/new_import.txt << 'EOF'
    def _sync_connect(self) -> None:
        """Synchronous connection setup (runs in executor)."""
        # Import bundled library using relative imports
        from .buderus_wps import (
            BroadcastMonitor,
            HeatPumpClient,
            ParameterRegistry,
            USBtinAdapter,
        )
        from .buderus_wps.menu_api import MenuAPI
        from .buderus_wps.exceptions import (
            TimeoutError as BuderusTimeoutError,
            DeviceCommunicationError,
            DeviceDisconnectedError,
            DeviceInitializationError,
            DeviceNotFoundError,
            DevicePermissionError,
            ReadTimeoutError,
        )
EOF

    # Use awk to replace the old _sync_connect function with the new one
    awk '
        BEGIN { in_function = 0; skip_until_logger = 0 }

        # Start of function
        /def _sync_connect\(self\)/ {
            in_function = 1
            # Read and print the new function from the temp file
            while ((getline line < "/tmp/new_import.txt") > 0) {
                print line
            }
            close("/tmp/new_import.txt")
            skip_until_logger = 1
            next
        }

        # End of old import section - resume printing
        skip_until_logger && /_LOGGER\.debug\("Connecting to heat pump/ {
            skip_until_logger = 0
            print
            next
        }

        # Skip lines in the old import section
        skip_until_logger { next }

        # Print all other lines
        { print }
    ' "$coordinator_file" > "$coordinator_file.tmp"

    mv "$coordinator_file.tmp" "$coordinator_file"

    # Cleanup
    rm -f /tmp/new_import.txt

    # Patch ALL remaining absolute imports throughout the file
    # This catches imports outside the _sync_connect function
    sed -i 's/from buderus_wps\./from .buderus_wps./g' "$coordinator_file"

    log_info "Coordinator imports patched"
}

patch_switch_imports() {
    local switch_file="$STAGING/custom_components/buderus_wps/switch.py"
    log_info "Patching switch.py imports..."

    # Replace: from buderus_wps.exceptions import
    # With: from .buderus_wps.exceptions import
    sed -i 's/from buderus_wps\.exceptions import/from .buderus_wps.exceptions import/g' "$switch_file"

    log_info "Switch imports patched"
}

patch_config_flow_imports() {
    local config_flow_file="$STAGING/custom_components/buderus_wps/config_flow.py"
    log_info "Patching config_flow.py imports..."

    # Replace all buderus_wps absolute imports with relative imports
    sed -i 's/from buderus_wps\./from .buderus_wps./g' "$config_flow_file"

    log_info "Config flow imports patched"
}

test_import_in_staging() {
    log_info "Testing imports in staging directory..."

    cd "$STAGING"

    # Test 1: Check library bundled
    if [ ! -d "custom_components/buderus_wps/buderus_wps" ]; then
        die "Library not bundled correctly"
    fi

    # Test 2: Check menu_structure.py exists with fix
    if ! grep -q "XDHW_TIME" "custom_components/buderus_wps/buderus_wps/menu_structure.py"; then
        die "DHW parameter fix not found in bundled library"
    fi

    # Test 3: Verify no sys.path hack
    if grep -q "sys.path" "custom_components/buderus_wps/coordinator.py"; then
        die "sys.path manipulation still present in coordinator.py"
    fi

    # Test 4: Verify relative imports in coordinator.py
    if ! grep -q "from \.buderus_wps import" "custom_components/buderus_wps/coordinator.py"; then
        die "Relative imports not found in coordinator.py"
    fi

    # Test 5: Verify relative imports in config_flow.py
    if ! grep -q "from \.buderus_wps\." "custom_components/buderus_wps/config_flow.py"; then
        die "Relative imports not found in config_flow.py"
    fi

    cd "$REPO_ROOT"
    log_info "All validation checks passed ✓"
}

create_archive() {
    local version="$1"
    local archive_name="buderus-wps-ha-${version}.zip"
    local generic_name="buderus-wps-ha.zip"  # HACS expects this

    log_info "Creating release archive: $archive_name"

    # CRITICAL: For zip_release: true, HACS extracts zip contents directly into /config/custom_components/<integration_name>/
    # So the zip must contain integration FILES at root, NOT wrapped in a directory
    cd "$STAGING/custom_components/buderus_wps"
    zip -r "../../../../$archive_name" . > /dev/null

    # Also create generic name for HACS compatibility
    cp "../../../../$archive_name" "../../../../$generic_name"
    cd "$REPO_ROOT"

    log_info "Archive created: $archive_name ($(du -h "$archive_name" | cut -f1))"
    log_info "HACS archive: $generic_name"
}

create_git_tag() {
    local version="$1"

    if git rev-parse "$version" >/dev/null 2>&1; then
        log_warn "Tag $version already exists"
        read -p "Skip tagging? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            die "Tag already exists. Delete it first: git tag -d $version"
        fi
        return
    fi

    log_info "Creating git tag: $version"
    git tag -a "$version" -m "Release $version"

    log_info "Pushing tag to origin..."
    git push origin "$version"
}

create_github_release() {
    local version="$1"
    local archive_name="buderus-wps-ha-${version}.zip"

    log_info "Creating GitHub release..."

    # Determine if this is a pre-release
    local prerelease_flag=""
    if [[ "$version" == *"beta"* ]] || [[ "$version" == *"alpha"* ]] || [[ "$version" == *"rc"* ]]; then
        prerelease_flag="--prerelease"
        log_info "Marking as pre-release (beta/alpha/rc detected)"
    fi

    # Create release notes
    local notes="Release $version

## Changes
- ✅ Bundled buderus_wps library for HACS compatibility
- ✅ Fixed DHW parameter bug (XDHW_TIME vs DHW_EXTRA_DURATION)
- ✅ USB Connection Control Switch (toggle for CLI access)

## Installation
Install via HACS custom repository: https://github.com/reinlemmens/buderus-wps-ha

## Testing
- [x] Library bundled correctly
- [x] Imports use relative paths
- [x] DHW parameter accessible
- [x] USB connection switch functional"

    # Create release
    gh release create "$version" $prerelease_flag \
        --title "Buderus WPS $version" \
        --notes "$notes" \
        "$archive_name" \
        "buderus-wps-ha.zip"  # Generic name for HACS

    log_info "GitHub release created: $version"
}

cleanup() {
    local version="$1"
    local archive_name="buderus-wps-ha-${version}.zip"
    local generic_name="buderus-wps-ha.zip"

    log_info "Cleaning up..."
    rm -rf "$STAGING"
    rm -f "$archive_name"
    rm -f "$generic_name"
    log_info "Cleanup complete"
}

#
# Main Script
#

main() {
    if [ $# -ne 1 ]; then
        echo "Usage: $0 <version>"
        echo "Example: $0 v1.2.0-beta.4"
        exit 1
    fi

    local version="$1"

    log_info "============================================"
    log_info "Building HACS Release: $version"
    log_info "============================================"

    # Phase 1: Validation
    log_info ""
    log_info "Phase 1: Validation"
    validate_version "$version"
    check_git_clean
    verify_manifest_version "$version"

    # Phase 2: Build
    log_info ""
    log_info "Phase 2: Build"
    rm -rf "$STAGING"
    mkdir -p "$STAGING"
    copy_integration
    bundle_library
    patch_coordinator_imports
    patch_switch_imports
    patch_config_flow_imports

    # Phase 3: Test
    log_info ""
    log_info "Phase 3: Test"
    test_import_in_staging

    # Phase 4: Package
    log_info ""
    log_info "Phase 4: Package"
    create_archive "$version"

    # Phase 5: Review
    log_info ""
    log_info "Phase 5: Review"
    log_info "Staging directory: $STAGING"
    log_info "Archive ready for inspection"
    echo ""
    read -p "Proceed with tagging and GitHub release? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_warn "Release aborted by user"
        log_info "Staging directory preserved for inspection: $STAGING"
        exit 0
    fi

    # Phase 6: Release
    log_info ""
    log_info "Phase 6: Release"
    create_git_tag "$version"
    create_github_release "$version"
    cleanup "$version"

    # Success!
    log_info ""
    log_info "============================================"
    log_info "✅ Release $version published successfully!"
    log_info "============================================"
    log_info "View at: https://github.com/reinlemmens/buderus-wps-ha/releases/tag/$version"
}

main "$@"
