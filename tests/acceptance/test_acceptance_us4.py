"""Acceptance tests for User Story 4: Cache Discovered Parameters.

User Story 4 - Cache Discovered Parameters (Priority: P2)
A developer wants discovered parameters to be cached to avoid re-running
the 30+ second discovery protocol on every connection.

Acceptance Scenarios:
1. Discovered parameters persist to cache storage
2. Valid cache loads without device discovery
3. Corrupted/invalid cache falls back to discovery or static data
4. Firmware version change invalidates cache
"""

import json

import pytest

from buderus_wps.cache import ParameterCache
from buderus_wps.parameter_data import PARAMETER_DATA


@pytest.fixture
def temp_cache_path(tmp_path):
    """Create temporary cache file path."""
    return tmp_path / "buderus" / "params_cache.json"


@pytest.fixture
def sample_discovered_params():
    """Simulate discovered parameters."""
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


class TestAcceptanceScenario1:
    """Scenario 1: Discovered parameters persist to cache storage."""

    def test_parameters_persisted_after_save(
        self, temp_cache_path, sample_discovered_params
    ):
        """Given parameters are discovered successfully,
        When the discovery completes,
        Then the system persists discovered parameters to cache storage."""
        cache = ParameterCache(temp_cache_path)

        # Simulate discovery completion
        result = cache.save(sample_discovered_params)

        assert result is True
        assert temp_cache_path.exists()

    def test_persisted_parameters_contain_all_fields(
        self, temp_cache_path, sample_discovered_params
    ):
        """Persisted cache contains all parameter fields."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params)

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "parameters" in data
        assert len(data["parameters"]) == 3

        # Verify all fields preserved
        first_param = data["parameters"][0]
        assert "idx" in first_param
        assert "extid" in first_param
        assert "max" in first_param
        assert "min" in first_param
        assert "format" in first_param
        assert "text" in first_param

    def test_cache_includes_integrity_checksum(
        self, temp_cache_path, sample_discovered_params
    ):
        """Cache includes checksum for integrity verification."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params)

        with open(temp_cache_path) as f:
            data = json.load(f)

        assert "checksum" in data
        assert data["checksum"].startswith("sha256:")


class TestAcceptanceScenario2:
    """Scenario 2: Valid cache loads without device discovery."""

    def test_valid_cache_loads_parameters(
        self, temp_cache_path, sample_discovered_params
    ):
        """Given a valid cache exists,
        When the developer initializes the heat pump class,
        Then parameters are loaded from cache without device discovery."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params)

        # Simulate new session - create new cache instance
        new_cache = ParameterCache(temp_cache_path)
        assert new_cache.is_valid() is True

        loaded = new_cache.load()
        assert loaded is not None
        assert len(loaded) == 3

    def test_loaded_parameters_match_original(
        self, temp_cache_path, sample_discovered_params
    ):
        """Loaded parameters match what was originally saved."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params)

        loaded = cache.load()

        for original, loaded_param in zip(sample_discovered_params, loaded):
            assert original["idx"] == loaded_param["idx"]
            assert original["text"] == loaded_param["text"]
            assert original["min"] == loaded_param["min"]
            assert original["max"] == loaded_param["max"]


class TestAcceptanceScenario3:
    """Scenario 3: Corrupted/invalid cache falls back to discovery or static data."""

    def test_corrupted_cache_detected(self, temp_cache_path, sample_discovered_params):
        """Given cache data is corrupted,
        When the developer initializes the class,
        Then the system falls back to discovery or static data."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params)

        # Corrupt the cache file
        with open(temp_cache_path, "w") as f:
            f.write("corrupted data {{{")

        new_cache = ParameterCache(temp_cache_path)
        assert new_cache.is_valid() is False
        assert new_cache.load() is None

    def test_tampered_parameters_detected(
        self, temp_cache_path, sample_discovered_params
    ):
        """Modified parameters are detected via checksum."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params)

        # Tamper with parameters
        with open(temp_cache_path) as f:
            data = json.load(f)
        data["parameters"][0]["max"] = 12345
        with open(temp_cache_path, "w") as f:
            json.dump(data, f)

        new_cache = ParameterCache(temp_cache_path)
        assert new_cache.is_valid() is False

    def test_missing_cache_detected(self, temp_cache_path):
        """Missing cache file is detected."""
        cache = ParameterCache(temp_cache_path)
        assert cache.is_valid() is False
        assert cache.load() is None

    def test_static_fallback_available(self):
        """Static fallback data is always available.

        When cache is invalid and discovery fails, PARAMETER_DATA
        provides static fallback from FHEM reference.
        """
        # PARAMETER_DATA contains fallback
        assert len(PARAMETER_DATA) == 1788
        assert PARAMETER_DATA[0]["idx"] == 0
        assert PARAMETER_DATA[0]["text"] == "ACCESSORIES_CONNECTED_BITMASK"


class TestAcceptanceScenario4:
    """Scenario 4: Firmware version change invalidates cache."""

    def test_version_mismatch_invalidates_cache(
        self, temp_cache_path, sample_discovered_params
    ):
        """Given the device firmware version changes,
        When the developer connects,
        Then the system invalidates cache and re-discovers parameters."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params, firmware="v1.0.0")

        # Simulate cache version mismatch
        with open(temp_cache_path) as f:
            data = json.load(f)
        data["version"] = "0.9.0"  # Old version
        with open(temp_cache_path, "w") as f:
            json.dump(data, f)

        new_cache = ParameterCache(temp_cache_path)
        assert new_cache.is_valid() is False

    def test_invalidate_removes_cache(self, temp_cache_path, sample_discovered_params):
        """Cache invalidation removes the cache file."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params)
        assert temp_cache_path.exists()

        cache.invalidate()
        assert not temp_cache_path.exists()

    def test_can_recreate_cache_after_invalidation(
        self, temp_cache_path, sample_discovered_params
    ):
        """Cache can be recreated after invalidation."""
        cache = ParameterCache(temp_cache_path)
        cache.save(sample_discovered_params)
        cache.invalidate()

        # Recreate cache
        result = cache.save(sample_discovered_params)
        assert result is True
        assert cache.is_valid() is True
