"""Contract tests verifying CAN ID formulas match FHEM reference implementation.

# PROTOCOL: CAN ID construction formulas from fhem/26_KM273v018.pm:2229-2230
# Read:  rtr = 0x04003FE0 | (idx << 14)
# Write: txd = 0x0C003FE0 | (idx << 14)

These tests parse the FHEM Perl file and verify that our Python implementation
uses the exact same formulas. This ensures compliance with Constitution
Principle II (Protocol Fidelity).
"""

import re

import pytest

from buderus_wps.parameter import Parameter
from buderus_wps.parameter_data import PARAMETER_DATA


class TestCanIdFormulasMatchFhem:
    """T026: Contract tests verifying CAN ID formulas match FHEM exactly."""

    def test_fhem_contains_read_can_id_formula(self):
        """Verify FHEM source contains the expected read CAN ID formula."""
        with open("fhem/26_KM273v018.pm") as f:
            content = f.read()

        # Look for the read CAN ID formula near line 2229
        # Pattern: my $rtr = sprintf("%08X",0x04003FE0 | ($idx << 14));
        pattern = r'\$rtr\s*=\s*sprintf\s*\(\s*["\']%08X["\']\s*,\s*0x04003FE0\s*\|\s*\(\s*\$idx\s*<<\s*14\s*\)\s*\)'

        match = re.search(pattern, content)
        assert match is not None, (
            "Could not find read CAN ID formula in FHEM source. "
            'Expected pattern: $rtr = sprintf("%08X",0x04003FE0 | ($idx << 14))'
        )

        print(f"✓ Found read CAN ID formula at position {match.start()}")

    def test_fhem_contains_write_can_id_formula(self):
        """Verify FHEM source contains the expected write CAN ID formula."""
        with open("fhem/26_KM273v018.pm") as f:
            content = f.read()

        # Look for the write CAN ID formula near line 2230
        # Pattern: my $txd = sprintf("%08X",0x0C003FE0 | ($idx << 14));
        pattern = r'\$txd\s*=\s*sprintf\s*\(\s*["\']%08X["\']\s*,\s*0x0C003FE0\s*\|\s*\(\s*\$idx\s*<<\s*14\s*\)\s*\)'

        match = re.search(pattern, content)
        assert match is not None, (
            "Could not find write CAN ID formula in FHEM source. "
            'Expected pattern: $txd = sprintf("%08X",0x0C003FE0 | ($idx << 14))'
        )

        print(f"✓ Found write CAN ID formula at position {match.start()}")

    def test_read_base_can_id_matches_fhem(self):
        """Verify read base CAN ID 0x04003FE0 matches FHEM."""
        with open("fhem/26_KM273v018.pm") as f:
            content = f.read()

        # Verify the base value is present
        assert (
            "0x04003FE0" in content
        ), "Base read CAN ID 0x04003FE0 not found in FHEM source"

        # Create parameter with idx=0 to test base value
        param = Parameter(
            idx=0,
            extid="814A53C66A0802",
            min=0,
            max=0,
            format="int",
            read=0,
            text="TEST",
        )

        # idx=0 means no shift, so should equal base value
        assert param.get_read_can_id() == 0x04003FE0
        print("✓ Read base CAN ID 0x04003FE0 verified")

    def test_write_base_can_id_matches_fhem(self):
        """Verify write base CAN ID 0x0C003FE0 matches FHEM."""
        with open("fhem/26_KM273v018.pm") as f:
            content = f.read()

        # Verify the base value is present
        assert (
            "0x0C003FE0" in content
        ), "Base write CAN ID 0x0C003FE0 not found in FHEM source"

        # Create parameter with idx=0 to test base value
        param = Parameter(
            idx=0,
            extid="814A53C66A0802",
            min=0,
            max=0,
            format="int",
            read=0,
            text="TEST",
        )

        # idx=0 means no shift, so should equal base value
        assert param.get_write_can_id() == 0x0C003FE0
        print("✓ Write base CAN ID 0x0C003FE0 verified")

    def test_shift_amount_is_14_bits(self):
        """Verify the formula uses 14-bit left shift as in FHEM."""
        with open("fhem/26_KM273v018.pm") as f:
            content = f.read()

        # Verify shift amount is 14 in FHEM source
        pattern = r"<<\s*14"
        matches = re.findall(pattern, content)

        # Should find at least 2 occurrences (read and write formulas)
        assert (
            len(matches) >= 2
        ), f"Expected at least 2 occurrences of '<< 14' in FHEM, found {len(matches)}"

        # Verify our implementation uses 14-bit shift
        param = Parameter(
            idx=1,
            extid="0000000000000000",
            min=0,
            max=100,
            format="int",
            read=0,
            text="TEST",
        )

        # idx=1 << 14 = 16384 = 0x4000
        expected_shift = 0x4000

        # Read: 0x04003FE0 + 0x4000 = 0x04007FE0
        assert param.get_read_can_id() == 0x04003FE0 + expected_shift

        # Write: 0x0C003FE0 + 0x4000 = 0x0C007FE0
        assert param.get_write_can_id() == 0x0C003FE0 + expected_shift

        print("✓ 14-bit shift verified")


class TestCanIdCalculationForRealParameters:
    """Test CAN ID calculation using actual parameters from PARAMETER_DATA."""

    @pytest.fixture
    def known_parameters(self):
        """Return well-known parameters for testing."""
        return {
            0: {
                "name": "ACCESSORIES_CONNECTED_BITMASK",
                "read_can": 0x04003FE0,  # Base (no shift)
                "write_can": 0x0C003FE0,  # Base (no shift)
            },
            1: {
                "name": "ACCESS_LEVEL",
                "read_can": 0x04007FE0,  # 0x04003FE0 | (1 << 14)
                "write_can": 0x0C007FE0,  # 0x0C003FE0 | (1 << 14)
            },
            11: {
                "name": "ADDITIONAL_BLOCK_HIGH_T2_TEMP",
                "read_can": 0x0402FFE0,  # 0x04003FE0 | (11 << 14)
                "write_can": 0x0C02FFE0,  # 0x0C003FE0 | (11 << 14)
            },
        }

    def test_idx_0_can_ids_match_expected(self, known_parameters):
        """Verify CAN IDs for idx=0 (ACCESSORIES_CONNECTED_BITMASK)."""
        param_data = next(p for p in PARAMETER_DATA if p["idx"] == 0)
        param = Parameter(**param_data)
        expected = known_parameters[0]

        assert param.get_read_can_id() == expected["read_can"], (
            f"idx=0 read CAN ID mismatch: got 0x{param.get_read_can_id():08X}, "
            f"expected 0x{expected['read_can']:08X}"
        )
        assert param.get_write_can_id() == expected["write_can"], (
            f"idx=0 write CAN ID mismatch: got 0x{param.get_write_can_id():08X}, "
            f"expected 0x{expected['write_can']:08X}"
        )
        print(
            f"✓ idx=0 ({param.text}): read=0x{param.get_read_can_id():08X}, write=0x{param.get_write_can_id():08X}"
        )

    def test_idx_1_can_ids_match_expected(self, known_parameters):
        """Verify CAN IDs for idx=1 (ACCESS_LEVEL)."""
        param_data = next(p for p in PARAMETER_DATA if p["idx"] == 1)
        param = Parameter(**param_data)
        expected = known_parameters[1]

        assert param.get_read_can_id() == expected["read_can"], (
            f"idx=1 read CAN ID mismatch: got 0x{param.get_read_can_id():08X}, "
            f"expected 0x{expected['read_can']:08X}"
        )
        assert param.get_write_can_id() == expected["write_can"], (
            f"idx=1 write CAN ID mismatch: got 0x{param.get_write_can_id():08X}, "
            f"expected 0x{expected['write_can']:08X}"
        )
        print(
            f"✓ idx=1 ({param.text}): read=0x{param.get_read_can_id():08X}, write=0x{param.get_write_can_id():08X}"
        )

    def test_idx_11_can_ids_match_expected(self, known_parameters):
        """Verify CAN IDs for idx=11 (ADDITIONAL_BLOCK_HIGH_T2_TEMP)."""
        param_data = next(p for p in PARAMETER_DATA if p["idx"] == 11)
        param = Parameter(**param_data)
        expected = known_parameters[11]

        assert param.get_read_can_id() == expected["read_can"], (
            f"idx=11 read CAN ID mismatch: got 0x{param.get_read_can_id():08X}, "
            f"expected 0x{expected['read_can']:08X}"
        )
        assert param.get_write_can_id() == expected["write_can"], (
            f"idx=11 write CAN ID mismatch: got 0x{param.get_write_can_id():08X}, "
            f"expected 0x{expected['write_can']:08X}"
        )
        print(
            f"✓ idx=11 ({param.text}): read=0x{param.get_read_can_id():08X}, write=0x{param.get_write_can_id():08X}"
        )

    def test_formula_consistency_across_all_parameters(self):
        """Verify CAN ID formula is consistent for all parameters in PARAMETER_DATA."""
        errors = []

        for param_data in PARAMETER_DATA:
            param = Parameter(**param_data)
            idx = param.idx

            # Calculate expected values using the FHEM formula
            expected_read = 0x04003FE0 | (idx << 14)
            expected_write = 0x0C003FE0 | (idx << 14)

            actual_read = param.get_read_can_id()
            actual_write = param.get_write_can_id()

            if actual_read != expected_read:
                errors.append(
                    f"idx={idx} read: got 0x{actual_read:08X}, expected 0x{expected_read:08X}"
                )
            if actual_write != expected_write:
                errors.append(
                    f"idx={idx} write: got 0x{actual_write:08X}, expected 0x{expected_write:08X}"
                )

        assert not errors, "CAN ID formula inconsistencies:\n" + "\n".join(errors)
        print(f"✓ CAN ID formula verified for all {len(PARAMETER_DATA)} parameters")

    def test_max_idx_can_id_within_valid_range(self):
        """Verify CAN IDs for maximum idx value are within valid CAN ID range."""
        # Find maximum idx in PARAMETER_DATA
        max_idx_param_data = max(PARAMETER_DATA, key=lambda p: p["idx"])
        param = Parameter(**max_idx_param_data)

        read_id = param.get_read_can_id()
        write_id = param.get_write_can_id()

        # CAN IDs should fit in 29 bits (extended CAN frame)
        max_can_id = 0x1FFFFFFF

        assert (
            read_id <= max_can_id
        ), f"Max idx={param.idx} produces read CAN ID 0x{read_id:08X} which exceeds 29-bit limit"
        assert (
            write_id <= max_can_id
        ), f"Max idx={param.idx} produces write CAN ID 0x{write_id:08X} which exceeds 29-bit limit"

        print(
            f"✓ Max idx={param.idx} CAN IDs within valid range: read=0x{read_id:08X}, write=0x{write_id:08X}"
        )
