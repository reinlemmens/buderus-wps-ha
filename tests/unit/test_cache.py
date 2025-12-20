"""Unit tests for ParameterCache class.

# PROTOCOL: Cache structure for discovered parameters

Tests the ParameterCache class which manages persistent storage of discovered
parameters to avoid slow 30+ second discovery on every connection.

Cache structure (JSON):
{
    "version": "1.0.0",
    "created": "2025-12-18T10:30:00Z",
    "device_id": "BUDERUS_WPS_SN12345",
    "firmware": "v1.23",
    "checksum": "sha256:abc123...",
    "element_count": 1789,
    "parameters": [...]
}
"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from buderus_wps.cache import ParameterCache


@pytest.fixture
def temp_cache_path(tmp_path):
    """Create temporary cache file path."""
    return tmp_path / "params_cache.json"


@pytest.fixture
def sample_parameters():
    """Sample parameter data for testing."""
    return [
        {
            "idx": 0,
            "extid": "814A53C66A0802",
            "max": 0,
            "min": 0,
            "format": "int",
            "read": 0,
            "text": "ACCESSORIES_CONNECTED_BITMASK",
        },
        {
            "idx": 1,
            "extid": "61E1E1FC660023",
            "max": 5,
            "min": 0,
            "format": "int",
            "read": 0,
            "text": "ACCESS_LEVEL",
        },
        {
            "idx": 11,
            "extid": "E555E4E11002E9",
            "max": 40,
            "min": -30,
            "format": "int",
            "read": 0,
            "text": "ADDITIONAL_BLOCK_HIGH_T2_TEMP",
        },
    ]


class TestParameterCacheSave:
    """T038: Test ParameterCache.save() JSON serialization."""

    def test_save_creates_file(self, temp_cache_path, sample_parameters):
        """Verify save() creates cache file."""
        cache = ParameterCache(temp_cache_path)
        result = cache.save(sample_parameters)

        assert result is True
        assert temp_cache_path.exists()

    def test_save_creates_valid_json(self, temp_cache_path, sample_parameters):
        """Verify saved file contains valid JSON."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert isinstance(data, dict)

    def test_save_includes_version(self, temp_cache_path, sample_parameters):
        """Verify saved data includes version field."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_save_includes_created_timestamp(self, temp_cache_path, sample_parameters):
        """Verify saved data includes created timestamp."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "created" in data
        # Verify it's a valid ISO format timestamp
        datetime.fromisoformat(data["created"])

    def test_save_includes_checksum(self, temp_cache_path, sample_parameters):
        """Verify saved data includes checksum."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "checksum" in data
        assert data["checksum"].startswith("sha256:")

    def test_save_includes_parameters(self, temp_cache_path, sample_parameters):
        """Verify saved data includes parameters."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "parameters" in data
        assert len(data["parameters"]) == 3

    def test_save_includes_element_count(self, temp_cache_path, sample_parameters):
        """Verify saved data includes element count."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "element_count" in data
        assert data["element_count"] == 3

    def test_save_with_device_id(self, temp_cache_path, sample_parameters):
        """Verify save includes optional device_id."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters, device_id="BUDERUS_WPS_001")

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert data.get("device_id") == "BUDERUS_WPS_001"

    def test_save_with_firmware(self, temp_cache_path, sample_parameters):
        """Verify save includes optional firmware version."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters, firmware="v1.23")

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert data.get("firmware") == "v1.23"

    def test_save_returns_false_on_write_error(self, sample_parameters):
        """Verify save returns False when write fails."""
        # Use a path that can't be written to
        cache = ParameterCache(Path("/nonexistent/dir/cache.json"))
        result = cache.save(sample_parameters)

        assert result is False


class TestParameterCacheLoad:
    """T039: Test ParameterCache.load() deserialization."""

    def test_load_returns_parameters(self, temp_cache_path, sample_parameters):
        """Verify load() returns saved parameters."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        loaded = cache.load()

        assert loaded is not None
        assert len(loaded) == 3
        assert loaded[0]["idx"] == 0
        assert loaded[1]["text"] == "ACCESS_LEVEL"

    def test_load_returns_none_for_missing_file(self, temp_cache_path):
        """Verify load() returns None for missing cache file."""
        cache = ParameterCache(temp_cache_path)
        loaded = cache.load()

        assert loaded is None

    def test_load_validates_checksum(self, temp_cache_path, sample_parameters):
        """Verify load() validates checksum."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        # Corrupt the checksum
        with open(temp_cache_path) as f:
            data = json.load(f)
        data["checksum"] = "sha256:invalid_checksum"
        with open(temp_cache_path, "w") as f:
            json.dump(data, f)

        loaded = cache.load()
        assert loaded is None

    def test_load_returns_none_for_invalid_json(self, temp_cache_path):
        """Verify load() returns None for invalid JSON."""
        with open(temp_cache_path, "w") as f:
            f.write("not valid json {{{")

        cache = ParameterCache(temp_cache_path)
        loaded = cache.load()

        assert loaded is None

    def test_load_returns_none_for_missing_parameters(self, temp_cache_path):
        """Verify load() returns None if parameters missing."""
        with open(temp_cache_path, "w") as f:
            json.dump({"version": "1.0.0"}, f)

        cache = ParameterCache(temp_cache_path)
        loaded = cache.load()

        assert loaded is None


class TestParameterCacheIsValid:
    """T040: Test cache invalidation."""

    def test_is_valid_returns_true_for_valid_cache(
        self, temp_cache_path, sample_parameters
    ):
        """Verify is_valid() returns True for valid cache."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        assert cache.is_valid() is True

    def test_is_valid_returns_false_for_missing_file(self, temp_cache_path):
        """Verify is_valid() returns False for missing file."""
        cache = ParameterCache(temp_cache_path)
        assert cache.is_valid() is False

    def test_is_valid_returns_false_for_corrupted_file(self, temp_cache_path):
        """Verify is_valid() returns False for corrupted file."""
        with open(temp_cache_path, "w") as f:
            f.write("corrupted content")

        cache = ParameterCache(temp_cache_path)
        assert cache.is_valid() is False

    def test_is_valid_returns_false_for_wrong_version(
        self, temp_cache_path, sample_parameters
    ):
        """Verify is_valid() returns False for wrong version."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        # Modify version
        with open(temp_cache_path) as f:
            data = json.load(f)
        data["version"] = "2.0.0"
        with open(temp_cache_path, "w") as f:
            json.dump(data, f)

        assert cache.is_valid() is False

    def test_is_valid_returns_false_for_bad_checksum(
        self, temp_cache_path, sample_parameters
    ):
        """Verify is_valid() returns False for checksum mismatch."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        # Corrupt checksum
        with open(temp_cache_path) as f:
            data = json.load(f)
        data["checksum"] = "sha256:0000000000000000"
        with open(temp_cache_path, "w") as f:
            json.dump(data, f)

        assert cache.is_valid() is False


class TestParameterCacheInvalidate:
    """Test cache invalidation."""

    def test_invalidate_removes_file(self, temp_cache_path, sample_parameters):
        """Verify invalidate() removes cache file."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        assert temp_cache_path.exists()

        cache.invalidate()

        assert not temp_cache_path.exists()

    def test_invalidate_succeeds_for_missing_file(self, temp_cache_path):
        """Verify invalidate() succeeds even if file doesn't exist."""
        cache = ParameterCache(temp_cache_path)
        cache.invalidate()  # Should not raise

        assert not temp_cache_path.exists()


class TestParameterCacheChecksum:
    """T042: Test checksum computation."""

    def test_checksum_is_deterministic(self, temp_cache_path, sample_parameters):
        """Verify checksum is deterministic for same data."""
        cache1 = ParameterCache(temp_cache_path)
        cache1.save(sample_parameters)

        with open(temp_cache_path) as f:
            data1 = json.load(f)
        checksum1 = data1["checksum"]

        # Save again
        cache2 = ParameterCache(temp_cache_path)
        cache2.save(sample_parameters)

        with open(temp_cache_path) as f:
            data2 = json.load(f)
        checksum2 = data2["checksum"]

        assert checksum1 == checksum2

    def test_checksum_changes_with_data(self, temp_cache_path, sample_parameters):
        """Verify checksum changes when data changes."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_parameters)

        with open(temp_cache_path) as f:
            data1 = json.load(f)
        checksum1 = data1["checksum"]

        # Modify parameters
        modified = sample_parameters.copy()
        modified[0]["max"] = 100
        cache.save(modified)

        with open(temp_cache_path) as f:
            data2 = json.load(f)
        checksum2 = data2["checksum"]

        assert checksum1 != checksum2
