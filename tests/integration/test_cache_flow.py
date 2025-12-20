"""Integration tests for parameter cache flow.

Tests the complete save/load cycle, checksum verification, and cache
invalidation scenarios.
"""

import json

import pytest

from buderus_wps.cache import ParameterCache
from buderus_wps.parameter_data import PARAMETER_DATA


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def sample_params():
    """Get first 10 parameters from real data."""
    return PARAMETER_DATA[:10]


class TestCacheSaveLoadCycle:
    """T043: Test complete save/load cycle."""

    def test_save_then_load_returns_same_data(self, temp_cache_dir, sample_params):
        """Verify save followed by load returns identical data."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)

        # Save
        result = cache.save(sample_params)
        assert result is True

        # Load
        loaded = cache.load()

        assert loaded is not None
        assert len(loaded) == len(sample_params)

        # Compare each parameter
        for original, loaded_param in zip(sample_params, loaded):
            assert original["idx"] == loaded_param["idx"]
            assert original["text"] == loaded_param["text"]
            assert original["extid"] == loaded_param["extid"]
            assert original["min"] == loaded_param["min"]
            assert original["max"] == loaded_param["max"]

    def test_save_load_with_large_dataset(self, temp_cache_dir):
        """Verify save/load works with full parameter set."""
        cache_path = temp_cache_dir / "full_params.json"
        cache = ParameterCache(cache_path)

        # Use all parameters
        result = cache.save(PARAMETER_DATA)
        assert result is True

        loaded = cache.load()
        assert loaded is not None
        assert len(loaded) == len(PARAMETER_DATA)

    def test_overwrite_existing_cache(self, temp_cache_dir, sample_params):
        """Verify save overwrites existing cache file."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)

        # Save initial
        cache.save(sample_params)

        # Modify and save again
        modified = sample_params[:5]
        cache.save(modified)

        # Load should return modified data
        loaded = cache.load()
        assert len(loaded) == 5


class TestCacheChecksumVerification:
    """Test checksum verification on load."""

    def test_modified_parameters_detected(self, temp_cache_dir, sample_params):
        """Verify checksum catches modified parameter values."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params)

        # Manually modify a parameter value
        with open(cache_path) as f:
            data = json.load(f)
        data["parameters"][0]["max"] = 99999  # Modify max value
        with open(cache_path, "w") as f:
            json.dump(data, f)

        # Load should fail due to checksum mismatch
        loaded = cache.load()
        assert loaded is None

    def test_added_parameter_detected(self, temp_cache_dir, sample_params):
        """Verify checksum catches added parameters."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params)

        # Add a parameter
        with open(cache_path) as f:
            data = json.load(f)
        data["parameters"].append({"idx": 9999, "text": "FAKE"})
        with open(cache_path, "w") as f:
            json.dump(data, f)

        loaded = cache.load()
        assert loaded is None

    def test_removed_parameter_detected(self, temp_cache_dir, sample_params):
        """Verify checksum catches removed parameters."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params)

        # Remove a parameter
        with open(cache_path) as f:
            data = json.load(f)
        data["parameters"].pop()
        with open(cache_path, "w") as f:
            json.dump(data, f)

        loaded = cache.load()
        assert loaded is None


class TestCacheInvalidation:
    """Test cache invalidation scenarios."""

    def test_invalidate_then_is_valid_returns_false(
        self, temp_cache_dir, sample_params
    ):
        """Verify invalidate makes cache invalid."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params)

        assert cache.is_valid() is True

        cache.invalidate()

        assert cache.is_valid() is False

    def test_invalidate_then_load_returns_none(self, temp_cache_dir, sample_params):
        """Verify load returns None after invalidation."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params)

        cache.invalidate()

        loaded = cache.load()
        assert loaded is None

    def test_save_after_invalidate_creates_new_cache(
        self, temp_cache_dir, sample_params
    ):
        """Verify save works after invalidation."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params)
        cache.invalidate()

        # Save again
        result = cache.save(sample_params)
        assert result is True
        assert cache.is_valid() is True


class TestCacheMetadata:
    """Test cache metadata handling."""

    def test_device_id_persisted(self, temp_cache_dir, sample_params):
        """Verify device_id is saved and retrievable."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params, device_id="BUDERUS_001")

        with open(cache_path) as f:
            data = json.load(f)

        assert data["device_id"] == "BUDERUS_001"

    def test_firmware_version_persisted(self, temp_cache_dir, sample_params):
        """Verify firmware version is saved and retrievable."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params, firmware="v2.0.1")

        with open(cache_path) as f:
            data = json.load(f)

        assert data["firmware"] == "v2.0.1"

    def test_element_count_matches_parameters(self, temp_cache_dir, sample_params):
        """Verify element_count matches actual parameter count."""
        cache_path = temp_cache_dir / "params.json"
        cache = ParameterCache(cache_path)
        cache.save(sample_params)

        with open(cache_path) as f:
            data = json.load(f)

        assert data["element_count"] == len(sample_params)
        assert data["element_count"] == len(data["parameters"])
