"""Integration tests for add-on installation validation.

These tests verify the add-on has all required files and structure
for successful installation via Home Assistant Add-on Store.
"""

import pytest
from pathlib import Path


@pytest.fixture
def addon_dir() -> Path:
    """Get addon directory path."""
    return Path(__file__).parent.parent.parent / "addon"


class TestAddonStructure:
    """Test add-on directory structure."""

    def test_addon_directory_exists(self, addon_dir: Path) -> None:
        """Addon directory must exist."""
        assert addon_dir.exists(), "addon/ directory must exist"
        assert addon_dir.is_dir()

    def test_config_yaml_exists(self, addon_dir: Path) -> None:
        """config.yaml is required for add-on installation."""
        config_file = addon_dir / "config.yaml"
        assert config_file.exists(), "addon/config.yaml is required"

    def test_dockerfile_exists(self, addon_dir: Path) -> None:
        """Dockerfile is required for container build."""
        dockerfile = addon_dir / "Dockerfile"
        assert dockerfile.exists(), "addon/Dockerfile is required"

    def test_build_yaml_exists(self, addon_dir: Path) -> None:
        """build.yaml should exist for multi-arch builds."""
        build_file = addon_dir / "build.yaml"
        assert build_file.exists(), "addon/build.yaml is recommended"


class TestDocumentation:
    """Test documentation files."""

    def test_docs_md_exists(self, addon_dir: Path) -> None:
        """DOCS.md is required for Add-on Store documentation."""
        docs_file = addon_dir / "DOCS.md"
        assert docs_file.exists(), "addon/DOCS.md is required for Add-on Store"

    def test_docs_has_content(self, addon_dir: Path) -> None:
        """DOCS.md should have substantial content."""
        docs_file = addon_dir / "DOCS.md"
        content = docs_file.read_text()
        assert len(content) > 500, "DOCS.md should have substantial documentation"
        assert "## Installation" in content or "## Configuration" in content

    def test_changelog_exists(self, addon_dir: Path) -> None:
        """CHANGELOG.md should exist for version history."""
        changelog = addon_dir / "CHANGELOG.md"
        assert changelog.exists(), "addon/CHANGELOG.md is recommended"


class TestTranslations:
    """Test translation files."""

    def test_translations_directory_exists(self, addon_dir: Path) -> None:
        """Translations directory should exist."""
        trans_dir = addon_dir / "translations"
        assert trans_dir.exists(), "addon/translations/ directory should exist"

    def test_english_translation_exists(self, addon_dir: Path) -> None:
        """English translation should be present."""
        en_file = addon_dir / "translations" / "en.yaml"
        assert en_file.exists(), "addon/translations/en.yaml is required"


class TestS6Overlay:
    """Test S6 overlay service configuration."""

    def test_rootfs_exists(self, addon_dir: Path) -> None:
        """rootfs directory should exist for S6 overlay."""
        rootfs = addon_dir / "rootfs"
        assert rootfs.exists(), "addon/rootfs/ is required for S6 overlay"

    def test_s6_service_directory_exists(self, addon_dir: Path) -> None:
        """S6 service directory should exist."""
        service_dir = addon_dir / "rootfs" / "etc" / "s6-overlay" / "s6-rc.d" / "buderus-wps"
        assert service_dir.exists(), "S6 service directory must exist"

    def test_s6_service_type_exists(self, addon_dir: Path) -> None:
        """S6 service type file should exist."""
        type_file = addon_dir / "rootfs" / "etc" / "s6-overlay" / "s6-rc.d" / "buderus-wps" / "type"
        assert type_file.exists(), "S6 service type file is required"

    def test_s6_service_type_is_longrun(self, addon_dir: Path) -> None:
        """S6 service should be a longrun service."""
        type_file = addon_dir / "rootfs" / "etc" / "s6-overlay" / "s6-rc.d" / "buderus-wps" / "type"
        content = type_file.read_text().strip()
        assert content == "longrun", "Service should be 'longrun' type"

    def test_s6_user_contents_exists(self, addon_dir: Path) -> None:
        """S6 user contents registration should exist."""
        contents_file = (
            addon_dir / "rootfs" / "etc" / "s6-overlay" / "s6-rc.d" / "user" / "contents.d" / "buderus-wps"
        )
        assert contents_file.exists(), "S6 service must be registered in user/contents.d/"


class TestPythonPackage:
    """Test Python package structure."""

    def test_python_package_exists(self, addon_dir: Path) -> None:
        """Python package directory should exist."""
        package_dir = addon_dir / "buderus_wps_addon"
        assert package_dir.exists(), "addon/buderus_wps_addon/ package must exist"

    def test_init_py_exists(self, addon_dir: Path) -> None:
        """__init__.py should exist."""
        init_file = addon_dir / "buderus_wps_addon" / "__init__.py"
        assert init_file.exists(), "Package must have __init__.py"

    def test_entity_config_exists(self, addon_dir: Path) -> None:
        """entity_config.py should exist."""
        entity_file = addon_dir / "buderus_wps_addon" / "entity_config.py"
        assert entity_file.exists(), "entity_config.py must exist"

    def test_config_module_exists(self, addon_dir: Path) -> None:
        """config.py should exist."""
        config_file = addon_dir / "buderus_wps_addon" / "config.py"
        assert config_file.exists(), "config.py must exist"
