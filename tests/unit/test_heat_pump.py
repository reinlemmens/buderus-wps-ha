"""Unit tests for HeatPump class.

Tests the HeatPump container class including parameter loading, lookup by index and name,
existence checks, listing methods, and error handling.
"""

import pytest
import time
from buderus_wps.parameter import HeatPump, Parameter


class TestHeatPumpInitialization:
    """Test HeatPump initialization and parameter loading."""

    def test_heat_pump_initialization_loads_all_parameters(self):
        """Test that HeatPump loads all 1789 parameters on init."""
        heat_pump = HeatPump()

        # Verify all parameters loaded
        assert heat_pump.parameter_count() == 1789

    def test_heat_pump_initialization_creates_both_indices(self):
        """Test that both index and name dictionaries are populated."""
        heat_pump = HeatPump()

        # Verify both lookups work
        param_by_idx = heat_pump.get_parameter_by_index(1)
        param_by_name = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

        # Should be the same parameter
        assert param_by_idx == param_by_name


class TestGetParameterByIndex:
    """Test get_parameter_by_index() method."""

    def test_get_parameter_by_index_returns_correct_parameter(self):
        """T017: Test get_parameter_by_index returns correct parameter."""
        heat_pump = HeatPump()

        param = heat_pump.get_parameter_by_index(1)

        assert param.idx == 1
        assert param.text == "ACCESS_LEVEL"
        assert param.min == 0
        assert param.max == 5

    def test_get_parameter_by_index_with_various_indices(self):
        """T017: Test get_parameter_by_index with different indices."""
        heat_pump = HeatPump()

        # Test first parameter
        param_0 = heat_pump.get_parameter_by_index(0)
        assert param_0.idx == 0
        assert param_0.text == "ACCESSORIES_CONNECTED_BITMASK"

        # Test parameter with negative min
        param_11 = heat_pump.get_parameter_by_index(11)
        assert param_11.idx == 11
        assert param_11.min == -30
        assert param_11.max == 40

        # Test last parameter
        param_2600 = heat_pump.get_parameter_by_index(2600)
        assert param_2600.idx == 2600
        assert param_2600.text == "TIMER_COMPRESSOR_START_DELAY_AT_CASCADE"

    def test_get_parameter_by_index_raises_keyerror_for_invalid_index(self):
        """T017: Test get_parameter_by_index raises KeyError for missing index."""
        heat_pump = HeatPump()

        # Try to get parameter with non-existent index
        with pytest.raises(KeyError):
            heat_pump.get_parameter_by_index(99999)

    def test_get_parameter_by_index_raises_keyerror_for_gap_in_sequence(self):
        """T017: Test get_parameter_by_index raises KeyError for gap (idx=13)."""
        heat_pump = HeatPump()

        # idx=13 should not exist (gap between 12 and 14)
        with pytest.raises(KeyError):
            heat_pump.get_parameter_by_index(13)

        # But 12 and 14 should exist
        param_12 = heat_pump.get_parameter_by_index(12)
        assert param_12.idx == 12

        param_14 = heat_pump.get_parameter_by_index(14)
        assert param_14.idx == 14


class TestGetParameterByName:
    """Test get_parameter_by_name() method."""

    def test_get_parameter_by_name_returns_correct_parameter(self):
        """T018: Test get_parameter_by_name returns correct parameter."""
        heat_pump = HeatPump()

        param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

        assert param.idx == 1
        assert param.text == "ACCESS_LEVEL"
        assert param.min == 0
        assert param.max == 5

    def test_get_parameter_by_name_with_various_names(self):
        """T018: Test get_parameter_by_name with different parameter names."""
        heat_pump = HeatPump()

        # Test various parameters
        param1 = heat_pump.get_parameter_by_name("ACCESSORIES_CONNECTED_BITMASK")
        assert param1.idx == 0

        param2 = heat_pump.get_parameter_by_name("ADDITIONAL_BLOCK_HIGH_T2_TEMP")
        assert param2.idx == 11
        assert param2.min == -30

        param3 = heat_pump.get_parameter_by_name("TIMER_COMPRESSOR_START_DELAY_AT_CASCADE")
        assert param3.idx == 2600

    def test_get_parameter_by_name_raises_keyerror_for_invalid_name(self):
        """T018: Test get_parameter_by_name raises KeyError for missing name."""
        heat_pump = HeatPump()

        with pytest.raises(KeyError):
            heat_pump.get_parameter_by_name("INVALID_PARAMETER_NAME")

    def test_get_parameter_by_name_is_case_sensitive(self):
        """T018: Test get_parameter_by_name is case-sensitive."""
        heat_pump = HeatPump()

        # Correct case should work
        param = heat_pump.get_parameter_by_name("ACCESS_LEVEL")
        assert param.idx == 1

        # Wrong case should fail
        with pytest.raises(KeyError):
            heat_pump.get_parameter_by_name("access_level")

        with pytest.raises(KeyError):
            heat_pump.get_parameter_by_name("Access_Level")


class TestIndexAndNameAccessConsistency:
    """Test that index and name access return identical parameters."""

    def test_index_and_name_access_return_same_parameter(self):
        """Verify get_parameter_by_index and get_parameter_by_name return same object."""
        heat_pump = HeatPump()

        param_by_idx = heat_pump.get_parameter_by_index(1)
        param_by_name = heat_pump.get_parameter_by_name("ACCESS_LEVEL")

        # Should be identical
        assert param_by_idx == param_by_name
        assert param_by_idx is param_by_name  # Same object in memory


class TestHasParameterMethods:
    """Test has_parameter_index() and has_parameter_name() methods."""

    def test_has_parameter_index_returns_true_for_existing_index(self):
        """T019: Test has_parameter_index returns True for existing indices."""
        heat_pump = HeatPump()

        assert heat_pump.has_parameter_index(0) is True
        assert heat_pump.has_parameter_index(1) is True
        assert heat_pump.has_parameter_index(2600) is True

    def test_has_parameter_index_returns_false_for_missing_index(self):
        """T019: Test has_parameter_index returns False for missing indices."""
        heat_pump = HeatPump()

        assert heat_pump.has_parameter_index(13) is False  # Gap in sequence
        assert heat_pump.has_parameter_index(99999) is False

    def test_has_parameter_name_returns_true_for_existing_name(self):
        """T019: Test has_parameter_name returns True for existing names."""
        heat_pump = HeatPump()

        assert heat_pump.has_parameter_name("ACCESS_LEVEL") is True
        assert heat_pump.has_parameter_name("ACCESSORIES_CONNECTED_BITMASK") is True

    def test_has_parameter_name_returns_false_for_missing_name(self):
        """T019: Test has_parameter_name returns False for missing names."""
        heat_pump = HeatPump()

        assert heat_pump.has_parameter_name("INVALID_NAME") is False
        assert heat_pump.has_parameter_name("access_level") is False  # Case sensitive


class TestListParameters:
    """Test list_all_parameters(), list_writable_parameters(), list_readonly_parameters()."""

    def test_list_all_parameters_returns_all_parameters(self):
        """Test list_all_parameters returns all 1789 parameters."""
        heat_pump = HeatPump()

        all_params = heat_pump.list_all_parameters()

        assert len(all_params) == 1789
        assert all(isinstance(p, Parameter) for p in all_params)

    def test_list_all_parameters_sorted_by_index(self):
        """Test list_all_parameters returns parameters sorted by idx."""
        heat_pump = HeatPump()

        all_params = heat_pump.list_all_parameters()

        # Verify sorted
        indices = [p.idx for p in all_params]
        assert indices == sorted(indices)

        # First and last should match
        assert all_params[0].idx == 0
        assert all_params[-1].idx == 2600

    def test_list_writable_parameters_returns_only_writable(self):
        """Test list_writable_parameters returns only writable parameters."""
        heat_pump = HeatPump()

        writable = heat_pump.list_writable_parameters()

        # All should be writable
        assert all(p.is_writable() for p in writable)
        assert all(p.read == 0 for p in writable)

    def test_list_readonly_parameters_returns_only_readonly(self):
        """Test list_readonly_parameters returns only read-only parameters."""
        heat_pump = HeatPump()

        readonly = heat_pump.list_readonly_parameters()

        # All should be read-only
        assert all(not p.is_writable() for p in readonly)
        assert all(p.read != 0 for p in readonly)

    def test_writable_and_readonly_lists_are_mutually_exclusive(self):
        """Test that writable and readonly lists don't overlap."""
        heat_pump = HeatPump()

        writable = heat_pump.list_writable_parameters()
        readonly = heat_pump.list_readonly_parameters()
        all_params = heat_pump.list_all_parameters()

        # No overlap
        writable_ids = {p.idx for p in writable}
        readonly_ids = {p.idx for p in readonly}
        assert len(writable_ids & readonly_ids) == 0

        # Together they should equal total
        assert len(writable) + len(readonly) == len(all_params)


class TestPerformance:
    """Test lookup performance meets < 1 second requirement (SC-002, SC-003)."""

    def test_lookup_by_index_performance(self):
        """T022: Verify lookup by index completes < 1 second."""
        heat_pump = HeatPump()

        # Test multiple lookups
        start_time = time.time()
        for _ in range(1000):
            heat_pump.get_parameter_by_index(1)
            heat_pump.get_parameter_by_index(100)
            heat_pump.get_parameter_by_index(2600)
        elapsed = time.time() - start_time

        # 1000 lookups should complete well under 1 second
        assert elapsed < 1.0, f"1000 index lookups took {elapsed:.3f}s (should be < 1s)"

    def test_lookup_by_name_performance(self):
        """T022: Verify lookup by name completes < 1 second."""
        heat_pump = HeatPump()

        # Test multiple lookups
        start_time = time.time()
        for _ in range(1000):
            heat_pump.get_parameter_by_name("ACCESS_LEVEL")
            heat_pump.get_parameter_by_name("ADDITIONAL_BLOCK_HIGH_T2_TEMP")
            heat_pump.get_parameter_by_name("TIMER_COMPRESSOR_START_DELAY_AT_CASCADE")
        elapsed = time.time() - start_time

        # 1000 lookups should complete well under 1 second
        assert elapsed < 1.0, f"1000 name lookups took {elapsed:.3f}s (should be < 1s)"

    def test_initialization_performance(self):
        """Test HeatPump initialization completes quickly."""
        start_time = time.time()
        heat_pump = HeatPump()
        elapsed = time.time() - start_time

        # Initialization should be fast (loading 1789 parameters)
        assert elapsed < 1.0, f"Initialization took {elapsed:.3f}s (should be < 1s)"
