"""Integration tests for parameter validation across multiple parameter types.

Tests validation logic with real parameters from parameter_data to ensure it works
correctly across different parameter types (normal range, negative min, large max,
flag parameters).
"""

import pytest
from buderus_wps.parameter import Parameter
from buderus_wps.parameter_data import PARAMETER_DATA


class TestParameterValidationIntegration:
    """Integration tests for validate_value() across various parameter types."""

    def test_validation_across_normal_range_parameters(self):
        """T014: Test validation with normal range parameters from real data."""
        # ACCESS_LEVEL: min=0, max=5
        access_level_data = next(p for p in PARAMETER_DATA if p["text"] == "ACCESS_LEVEL")
        param = Parameter(**access_level_data)

        # Valid values
        assert param.validate_value(0) is True
        assert param.validate_value(2) is True
        assert param.validate_value(5) is True

        # Invalid values
        assert param.validate_value(-1) is False
        assert param.validate_value(6) is False

    def test_validation_with_negative_minimum_parameters(self):
        """T014: Test validation with parameters having negative minimum."""
        # ADDITIONAL_BLOCK_HIGH_T2_TEMP: min=-30, max=40
        temp_param_data = next(
            p for p in PARAMETER_DATA
            if p["text"] == "ADDITIONAL_BLOCK_HIGH_T2_TEMP"
        )
        param = Parameter(**temp_param_data)

        # Valid values including negative
        assert param.validate_value(-30) is True
        assert param.validate_value(-15) is True
        assert param.validate_value(0) is True
        assert param.validate_value(20) is True
        assert param.validate_value(40) is True

        # Invalid values
        assert param.validate_value(-31) is False
        assert param.validate_value(41) is False

    def test_validation_with_large_maximum_parameters(self):
        """T014: Test validation with parameters having very large maximum."""
        # Find a parameter with large max value
        large_max_params = [p for p in PARAMETER_DATA if p["max"] > 1000000]
        assert len(large_max_params) > 0, "Should have parameters with large max"

        param_data = large_max_params[0]
        param = Parameter(**param_data)

        # Valid values
        assert param.validate_value(param_data["min"]) is True
        assert param.validate_value(param_data["max"]) is True
        assert param.validate_value((param_data["min"] + param_data["max"]) // 2) is True

        # Invalid values
        if param_data["min"] > 0:
            assert param.validate_value(param_data["min"] - 1) is False
        assert param.validate_value(param_data["max"] + 1) is False

    def test_validation_with_flag_parameters_min_equals_max(self):
        """T014: Test validation with flag parameters where min=max=0."""
        # ACCESSORIES_CONNECTED_BITMASK: min=0, max=0
        flag_param_data = next(
            p for p in PARAMETER_DATA
            if p["text"] == "ACCESSORIES_CONNECTED_BITMASK"
        )
        param = Parameter(**flag_param_data)

        assert param.min == 0
        assert param.max == 0

        # Only 0 should be valid
        assert param.validate_value(0) is True

        # Everything else should be invalid
        assert param.validate_value(1) is False
        assert param.validate_value(-1) is False
        assert param.validate_value(100) is False

    def test_validation_across_multiple_writable_parameters(self):
        """T014: Test validation with multiple writable parameters."""
        # Get several writable parameters
        writable_params = [p for p in PARAMETER_DATA if p["read"] == 0][:10]
        assert len(writable_params) >= 10, "Should have at least 10 writable parameters"

        for param_data in writable_params:
            param = Parameter(**param_data)

            # Verify writable
            assert param.is_writable() is True

            # Test min and max boundaries
            assert param.validate_value(param.min) is True
            assert param.validate_value(param.max) is True

            # Test just outside boundaries (if not flag parameter)
            if param.min < param.max:
                if param.min > -1000000:  # Avoid extreme negatives
                    assert param.validate_value(param.min - 1) is False
                if param.max < 1000000:  # Avoid extreme positives
                    assert param.validate_value(param.max + 1) is False

    def test_validation_across_multiple_readonly_parameters(self):
        """T014: Test validation with multiple read-only parameters."""
        # Get several read-only parameters
        readonly_params = [p for p in PARAMETER_DATA if p["read"] == 1][:5]
        assert len(readonly_params) >= 5, "Should have at least 5 read-only parameters"

        for param_data in readonly_params:
            param = Parameter(**param_data)

            # Verify read-only
            assert param.is_writable() is False

            # Validation should still work for read-only parameters
            assert param.validate_value(param.min) is True
            assert param.validate_value(param.max) is True

    def test_validation_with_zero_min_max_range_parameters(self):
        """T014: Test validation with parameters having min=max=0 (flags/bitmasks)."""
        # Find parameters with min=max=0
        flag_params = [p for p in PARAMETER_DATA if p["min"] == 0 and p["max"] == 0]
        assert len(flag_params) > 0, "Should have flag parameters with min=max=0"

        for param_data in flag_params[:3]:  # Test first 3
            param = Parameter(**param_data)

            # Only 0 should be valid
            assert param.validate_value(0) is True

            # Non-zero should be invalid
            assert param.validate_value(1) is False
            assert param.validate_value(-1) is False

    def test_validation_preserves_fhem_constraints(self):
        """T014: Verify validation respects FHEM constraints exactly."""
        # Test a variety of parameters with different ranges
        test_cases = [
            ("ACCESS_LEVEL", 0, 5),
            ("ACCESS_LEVEL_TIMEOUT_DELAY_TIME", 1, 240),
            ("ADDITIONAL_BLOCK_HIGH_T2_TEMP", -30, 40),
        ]

        for text, expected_min, expected_max in test_cases:
            param_data = next(p for p in PARAMETER_DATA if p["text"] == text)
            param = Parameter(**param_data)

            # Verify min/max match FHEM
            assert param.min == expected_min, f"{text} min mismatch"
            assert param.max == expected_max, f"{text} max mismatch"

            # Verify validation works with FHEM constraints
            assert param.validate_value(expected_min) is True
            assert param.validate_value(expected_max) is True

            # Values outside FHEM constraints should fail
            if expected_min > -1000000:
                assert param.validate_value(expected_min - 1) is False
            if expected_max < 1000000:
                assert param.validate_value(expected_max + 1) is False
