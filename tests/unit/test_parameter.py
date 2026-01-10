"""Unit tests for Parameter class.

Tests the Parameter dataclass including creation, attribute access, is_writable() method,
and validate_value() method with various edge cases.
"""

import pytest

from buderus_wps.parameter import Parameter


class TestParameterCreation:
    """Test Parameter dataclass creation and attribute access."""

    def test_create_parameter_with_valid_data(self):
        """T005: Test creating Parameter with valid data (ACCESS_LEVEL example)."""
        # Example from FHEM: idx=1, ACCESS_LEVEL
        param = Parameter(
            idx=1,
            extid="61E1E1FC660023",
            min=0,
            max=5,
            format="int",
            read=0,
            text="ACCESS_LEVEL",
        )

        assert param.idx == 1
        assert param.extid == "61E1E1FC660023"
        assert param.min == 0
        assert param.max == 5
        assert param.format == "int"
        assert param.read == 0
        assert param.text == "ACCESS_LEVEL"

    def test_parameter_is_immutable(self):
        """Test that Parameter is frozen (immutable)."""
        param = Parameter(
            idx=1,
            extid="61E1E1FC660023",
            min=0,
            max=5,
            format="int",
            read=0,
            text="ACCESS_LEVEL",
        )

        # Attempting to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            param.idx = 999

    def test_parameter_with_negative_min(self):
        """Test parameter with negative minimum value (temperature parameter)."""
        # Example from FHEM: idx=11, ADDITIONAL_BLOCK_HIGH_T2_TEMP
        param = Parameter(
            idx=11,
            extid="E555E4E11002E9",
            min=-30,
            max=40,
            format="int",
            read=0,
            text="ADDITIONAL_BLOCK_HIGH_T2_TEMP",
        )

        assert param.min == -30
        assert param.max == 40
        assert param.idx == 11

    def test_parameter_with_min_equals_max(self):
        """Test parameter with min=max=0 (flag/bitmask parameter)."""
        # Example from FHEM: idx=0, ACCESSORIES_CONNECTED_BITMASK
        param = Parameter(
            idx=0,
            extid="814A53C66A0802",
            min=0,
            max=0,
            format="int",
            read=0,
            text="ACCESSORIES_CONNECTED_BITMASK",
        )

        assert param.min == 0
        assert param.max == 0

    def test_parameter_with_large_max(self):
        """Test parameter with very large maximum value."""
        # Example from FHEM: idx=22, ADDITIONAL_DHW_ACKNOWLEDGED
        param = Parameter(
            idx=22,
            extid="C02D7CE3A909E9",
            min=0,
            max=16777216,
            format="int",
            read=1,
            text="ADDITIONAL_DHW_ACKNOWLEDGED",
        )

        assert param.max == 16777216


class TestParameterIsWritable:
    """Test is_writable() method."""

    def test_is_writable_returns_true_when_read_is_zero(self):
        """T006: Test is_writable() returns True when read=0 (writable)."""
        param = Parameter(
            idx=1,
            extid="61E1E1FC660023",
            min=0,
            max=5,
            format="int",
            read=0,  # Writable
            text="ACCESS_LEVEL",
        )

        assert param.is_writable() is True

    def test_is_writable_returns_false_when_read_is_one(self):
        """T006: Test is_writable() returns False when read=1 (read-only)."""
        param = Parameter(
            idx=22,
            extid="C02D7CE3A909E9",
            min=0,
            max=16777216,
            format="int",
            read=1,  # Read-only
            text="ADDITIONAL_DHW_ACKNOWLEDGED",
        )

        assert param.is_writable() is False


class TestParameterValidateValue:
    """Test validate_value() method."""

    def test_validate_value_within_range(self):
        """T011: Test validate_value() accepts values within min/max range."""
        param = Parameter(
            idx=1,
            extid="61E1E1FC660023",
            min=0,
            max=5,
            format="int",
            read=0,
            text="ACCESS_LEVEL",
        )

        # Valid values within range
        assert param.validate_value(0) is True
        assert param.validate_value(3) is True
        assert param.validate_value(5) is True

    def test_validate_value_below_minimum(self):
        """T012: Test validate_value() rejects values below minimum."""
        param = Parameter(
            idx=1,
            extid="61E1E1FC660023",
            min=0,
            max=5,
            format="int",
            read=0,
            text="ACCESS_LEVEL",
        )

        assert param.validate_value(-1) is False
        assert param.validate_value(-100) is False

    def test_validate_value_above_maximum(self):
        """T012: Test validate_value() rejects values above maximum."""
        param = Parameter(
            idx=1,
            extid="61E1E1FC660023",
            min=0,
            max=5,
            format="int",
            read=0,
            text="ACCESS_LEVEL",
        )

        assert param.validate_value(6) is False
        assert param.validate_value(100) is False

    def test_validate_value_at_boundaries(self):
        """T012: Test validate_value() at exact min and max boundaries."""
        param = Parameter(
            idx=2,
            extid="A1137CB3EB0B26",
            min=1,
            max=240,
            format="int",
            read=0,
            text="ACCESS_LEVEL_TIMEOUT_DELAY_TIME",
        )

        # Boundaries should be valid
        assert param.validate_value(1) is True
        assert param.validate_value(240) is True

        # Just outside boundaries should be invalid
        assert param.validate_value(0) is False
        assert param.validate_value(241) is False

    def test_validate_value_with_negative_range(self):
        """T012: Test validate_value() with negative minimum value."""
        param = Parameter(
            idx=11,
            extid="E555E4E11002E9",
            min=-30,
            max=40,
            format="int",
            read=0,
            text="ADDITIONAL_BLOCK_HIGH_T2_TEMP",
        )

        # Valid values in negative range
        assert param.validate_value(-30) is True
        assert param.validate_value(-15) is True
        assert param.validate_value(0) is True
        assert param.validate_value(20) is True
        assert param.validate_value(40) is True

        # Invalid values outside range
        assert param.validate_value(-31) is False
        assert param.validate_value(41) is False

    def test_validate_value_with_min_equals_max(self):
        """T012: Test validate_value() when min=max=0 (flag parameter)."""
        param = Parameter(
            idx=0,
            extid="814A53C66A0802",
            min=0,
            max=0,
            format="int",
            read=0,
            text="ACCESSORIES_CONNECTED_BITMASK",
        )

        # Only 0 should be valid
        assert param.validate_value(0) is True

        # Everything else should be invalid
        assert param.validate_value(1) is False
        assert param.validate_value(-1) is False

    def test_validate_value_with_large_maximum(self):
        """T012: Test validate_value() with very large maximum value."""
        param = Parameter(
            idx=22,
            extid="C02D7CE3A909E9",
            min=0,
            max=16777216,
            format="int",
            read=1,
            text="ADDITIONAL_DHW_ACKNOWLEDGED",
        )

        # Valid values
        assert param.validate_value(0) is True
        assert param.validate_value(1000000) is True
        assert param.validate_value(16777216) is True

        # Invalid values
        assert param.validate_value(-1) is False
        assert param.validate_value(16777217) is False


class TestHeatPumpDiscoveredNames:
    """Test HeatPump._discovered_names tracking."""

    def test_is_discovered_returns_false_initially(self):
        """Test is_discovered() returns False for params without discovery."""
        from buderus_wps.parameter import HeatPump

        hp = HeatPump()  # Uses static fallback

        # No parameters should be marked as discovered
        assert hp.is_discovered("ACCESS_LEVEL") is False
        assert hp.is_discovered("GT3_TEMP") is False

    def test_mark_discovered_adds_names(self):
        """Test mark_discovered() adds names to _discovered_names set."""
        from buderus_wps.parameter import HeatPump

        hp = HeatPump()

        hp.mark_discovered(["ACCESS_LEVEL", "GT3_TEMP"])

        assert hp.is_discovered("ACCESS_LEVEL") is True
        assert hp.is_discovered("GT3_TEMP") is True
        assert hp.is_discovered("UNKNOWN_PARAM") is False

    def test_is_discovered_case_insensitive(self):
        """Test is_discovered() is case-insensitive."""
        from buderus_wps.parameter import HeatPump

        hp = HeatPump()
        hp.mark_discovered(["ACCESS_LEVEL"])

        assert hp.is_discovered("access_level") is True
        assert hp.is_discovered("Access_Level") is True
        assert hp.is_discovered("ACCESS_LEVEL") is True

    def test_update_from_discovery_marks_all_elements(self):
        """Test update_from_discovery() marks all discovered elements."""
        from buderus_wps.element_discovery import DiscoveredElement
        from buderus_wps.parameter import HeatPump

        hp = HeatPump()

        # Create mock discovered elements
        discovered = [
            DiscoveredElement(
                idx=1,
                extid="61E1E1FC660023",
                text="ACCESS_LEVEL",
                min_value=0,
                max_value=5,
            ),
            DiscoveredElement(
                idx=682,  # Different from static default (681)
                extid="0EB5CF43420068",
                text="GT3_TEMP",
                min_value=-400,
                max_value=1500,
            ),
            DiscoveredElement(
                idx=999,
                extid="AABBCCDD001122",
                text="NEW_PARAM",  # Not in static defaults
                min_value=0,
                max_value=100,
            ),
        ]

        hp.update_from_discovery(discovered)

        # All discovered elements should be marked
        assert hp.is_discovered("ACCESS_LEVEL") is True
        assert hp.is_discovered("GT3_TEMP") is True
        assert hp.is_discovered("NEW_PARAM") is True

        # Params NOT in discovery should NOT be marked
        assert hp.is_discovered("GT10_TEMP") is False
