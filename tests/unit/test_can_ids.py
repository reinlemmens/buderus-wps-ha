"""Unit tests for CAN ID calculation methods.

# PROTOCOL: CAN ID formulas from fhem/26_KM273v018.pm:2229-2230
# Read:  rtr = 0x04003FE0 | (idx << 14)
# Write: txd = 0x0C003FE0 | (idx << 14)

These tests verify that Parameter.get_read_can_id() and Parameter.get_write_can_id()
correctly implement the FHEM CAN ID construction formulas.
"""

import pytest

from buderus_wps.parameter import Parameter


# Fixtures for common test parameters
@pytest.fixture
def param_idx_0():
    """Parameter with idx=0 (base case, no shift)."""
    return Parameter(
        idx=0,
        extid="814A53C66A0802",
        min=0,
        max=0,
        format="int",
        read=0,
        text="ACCESSORIES_CONNECTED_BITMASK",
    )


@pytest.fixture
def param_idx_1():
    """Parameter with idx=1 (ACCESS_LEVEL)."""
    return Parameter(
        idx=1,
        extid="61E1E1FC660023",
        min=0,
        max=5,
        format="int",
        read=0,
        text="ACCESS_LEVEL",
    )


@pytest.fixture
def param_idx_11():
    """Parameter with idx=11 (ADDITIONAL_BLOCK_HIGH_T2_TEMP)."""
    return Parameter(
        idx=11,
        extid="E555E4E11002E9",
        min=-30,
        max=40,
        format="int",
        read=0,
        text="ADDITIONAL_BLOCK_HIGH_T2_TEMP",
    )


@pytest.fixture
def param_idx_100():
    """Parameter with idx=100 for testing larger index shifts."""
    return Parameter(
        idx=100,
        extid="0000000000000000",
        min=0,
        max=100,
        format="int",
        read=0,
        text="TEST_PARAM_100",
    )


@pytest.fixture
def param_idx_1000():
    """Parameter with idx=1000 for testing large index shifts."""
    return Parameter(
        idx=1000,
        extid="0000000000000000",
        min=0,
        max=100,
        format="int",
        read=0,
        text="TEST_PARAM_1000",
    )


class TestGetReadCanId:
    """T024: Test get_read_can_id() method.

    # PROTOCOL: Read CAN ID formula: rtr = 0x04003FE0 | (idx << 14)
    Source: fhem/26_KM273v018.pm:2229
    """

    def test_idx_0_returns_base_can_id(self, param_idx_0):
        """Verify idx=0 returns base CAN ID 0x04003FE0 (no shift)."""
        expected = 0x04003FE0
        assert param_idx_0.get_read_can_id() == expected

    def test_idx_1_shifts_correctly(self, param_idx_1):
        """Verify idx=1 produces 0x04007FE0 (shifts 1 << 14 = 0x4000)."""
        # 0x04003FE0 | (1 << 14) = 0x04003FE0 | 0x4000 = 0x04007FE0
        expected = 0x04007FE0
        assert param_idx_1.get_read_can_id() == expected

    def test_idx_11_shifts_correctly(self, param_idx_11):
        """Verify idx=11 produces correct CAN ID."""
        # 0x04003FE0 | (11 << 14) = 0x04003FE0 | 0x2C000 = 0x0402FFE0
        expected = 0x04003FE0 | (11 << 14)
        assert param_idx_11.get_read_can_id() == expected
        assert param_idx_11.get_read_can_id() == 0x0402FFE0

    def test_idx_100_shifts_correctly(self, param_idx_100):
        """Verify idx=100 produces correct CAN ID."""
        # 0x04003FE0 | (100 << 14) = 0x04003FE0 | 0x190000 = 0x04193FE0
        expected = 0x04003FE0 | (100 << 14)
        assert param_idx_100.get_read_can_id() == expected
        assert param_idx_100.get_read_can_id() == 0x04193FE0

    def test_idx_1000_shifts_correctly(self, param_idx_1000):
        """Verify idx=1000 produces correct CAN ID."""
        # 0x04003FE0 | (1000 << 14) = 0x04003FE0 | 0xFA0000 = 0x04FA3FE0
        expected = 0x04003FE0 | (1000 << 14)
        assert param_idx_1000.get_read_can_id() == expected
        assert param_idx_1000.get_read_can_id() == 0x04FA3FE0

    def test_read_can_id_is_integer(self, param_idx_1):
        """Verify get_read_can_id() returns an integer."""
        result = param_idx_1.get_read_can_id()
        assert isinstance(result, int)

    def test_read_can_id_matches_formula(self, param_idx_1):
        """Verify CAN ID matches the FHEM formula exactly."""
        idx = param_idx_1.idx
        expected = 0x04003FE0 | (idx << 14)
        assert param_idx_1.get_read_can_id() == expected


class TestGetWriteCanId:
    """T025: Test get_write_can_id() method.

    # PROTOCOL: Write CAN ID formula: txd = 0x0C003FE0 | (idx << 14)
    Source: fhem/26_KM273v018.pm:2230
    """

    def test_idx_0_returns_base_can_id(self, param_idx_0):
        """Verify idx=0 returns base CAN ID 0x0C003FE0 (no shift)."""
        expected = 0x0C003FE0
        assert param_idx_0.get_write_can_id() == expected

    def test_idx_1_shifts_correctly(self, param_idx_1):
        """Verify idx=1 produces 0x0C007FE0 (shifts 1 << 14 = 0x4000)."""
        # 0x0C003FE0 | (1 << 14) = 0x0C003FE0 | 0x4000 = 0x0C007FE0
        expected = 0x0C007FE0
        assert param_idx_1.get_write_can_id() == expected

    def test_idx_11_shifts_correctly(self, param_idx_11):
        """Verify idx=11 produces correct CAN ID."""
        # 0x0C003FE0 | (11 << 14) = 0x0C003FE0 | 0x2C000 = 0x0C02FFE0
        expected = 0x0C003FE0 | (11 << 14)
        assert param_idx_11.get_write_can_id() == expected
        assert param_idx_11.get_write_can_id() == 0x0C02FFE0

    def test_idx_100_shifts_correctly(self, param_idx_100):
        """Verify idx=100 produces correct CAN ID."""
        # 0x0C003FE0 | (100 << 14) = 0x0C003FE0 | 0x190000 = 0x0C193FE0
        expected = 0x0C003FE0 | (100 << 14)
        assert param_idx_100.get_write_can_id() == expected
        assert param_idx_100.get_write_can_id() == 0x0C193FE0

    def test_idx_1000_shifts_correctly(self, param_idx_1000):
        """Verify idx=1000 produces correct CAN ID."""
        # 0x0C003FE0 | (1000 << 14) = 0x0C003FE0 | 0xFA00000 = 0x0FA03FE0
        # Wait, this overlaps with higher bits, need to check
        expected = 0x0C003FE0 | (1000 << 14)
        assert param_idx_1000.get_write_can_id() == expected

    def test_write_can_id_is_integer(self, param_idx_1):
        """Verify get_write_can_id() returns an integer."""
        result = param_idx_1.get_write_can_id()
        assert isinstance(result, int)

    def test_write_can_id_matches_formula(self, param_idx_1):
        """Verify CAN ID matches the FHEM formula exactly."""
        idx = param_idx_1.idx
        expected = 0x0C003FE0 | (idx << 14)
        assert param_idx_1.get_write_can_id() == expected


class TestCanIdRelationship:
    """Test relationship between read and write CAN IDs."""

    def test_write_can_id_differs_from_read_can_id(self, param_idx_1):
        """Verify read and write CAN IDs are different for same parameter."""
        read_id = param_idx_1.get_read_can_id()
        write_id = param_idx_1.get_write_can_id()
        assert read_id != write_id

    def test_read_and_write_ids_have_same_shift(self, param_idx_1):
        """Verify read and write CAN IDs use the same idx shift.

        The difference between read and write IDs should be constant:
        0x0C003FE0 - 0x04003FE0 = 0x08000000
        """
        read_id = param_idx_1.get_read_can_id()
        write_id = param_idx_1.get_write_can_id()
        expected_diff = 0x0C003FE0 - 0x04003FE0
        assert write_id - read_id == expected_diff

    def test_can_id_difference_is_constant_across_indices(self):
        """Verify the difference between read/write IDs is constant for all indices."""
        expected_diff = 0x0C003FE0 - 0x04003FE0

        for idx in [0, 1, 10, 100, 500, 1000, 1789]:
            param = Parameter(
                idx=idx,
                extid="0000000000000000",
                min=0,
                max=100,
                format="int",
                read=0,
                text=f"TEST_PARAM_{idx}",
            )
            read_id = param.get_read_can_id()
            write_id = param.get_write_can_id()
            assert write_id - read_id == expected_diff, f"Failed for idx={idx}"
