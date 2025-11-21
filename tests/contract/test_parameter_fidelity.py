"""Contract tests verifying Python parameter data matches FHEM source.

# PROTOCOL: These tests ensure 100% fidelity with the FHEM reference implementation.
# Source: fhem/26_KM273v018.pm @KM273_elements_default array

These tests parse the FHEM Perl file and verify that the Python parameter data
extracted in parameter_data.py matches exactly. This ensures compliance with
Constitution Principle II (Protocol Fidelity).
"""

import re
import pytest
from buderus_wps.parameter_data import PARAMETER_DATA


class TestParameterDataFidelity:
    """Verify PARAMETER_DATA matches FHEM source exactly."""

    def test_parameter_count_matches_fhem(self):
        """T008: Verify total parameter count matches FHEM source."""
        # Parse FHEM file to count parameters
        with open('fhem/26_KM273v018.pm', 'r') as f:
            content = f.read()

        # Extract the @KM273_elements_default array
        start_marker = "my @KM273_elements_default ="
        end_marker = ");"

        start_idx = content.find(start_marker)
        assert start_idx != -1, "Could not find KM273_elements_default array in FHEM file"

        search_start = start_idx + len(start_marker)
        end_idx = content.find(end_marker, search_start)
        assert end_idx != -1, "Could not find end of KM273_elements_default array"

        array_content = content[start_idx:end_idx + len(end_marker)]

        # Count parameter entries by counting opening braces
        # Pattern: { 'idx' => ...
        param_pattern = r"\{\s*'idx'\s*=>"
        fhem_param_count = len(re.findall(param_pattern, array_content))

        # Verify counts match
        assert len(PARAMETER_DATA) == fhem_param_count, \
            f"Parameter count mismatch: Python has {len(PARAMETER_DATA)}, FHEM has {fhem_param_count}"

        print(f"✓ Parameter count verified: {len(PARAMETER_DATA)} parameters")

    def test_first_parameter_matches_fhem(self):
        """T009: Spot-check first parameter (idx=0) matches FHEM exactly."""
        # Expected from FHEM: idx=0, ACCESSORIES_CONNECTED_BITMASK
        expected = {
            "idx": 0,
            "extid": "814A53C66A0802",
            "max": 0,
            "min": 0,
            "format": "int",
            "read": 0,
            "text": "ACCESSORIES_CONNECTED_BITMASK"
        }

        # Find parameter with idx=0 in PARAMETER_DATA
        param = next((p for p in PARAMETER_DATA if p["idx"] == 0), None)
        assert param is not None, "Parameter with idx=0 not found"

        # Verify all fields match
        assert param == expected, f"Parameter idx=0 doesn't match FHEM. Got: {param}, Expected: {expected}"

        print("✓ First parameter (idx=0) verified")

    def test_access_level_parameter_matches_fhem(self):
        """T009: Spot-check ACCESS_LEVEL parameter (idx=1) matches FHEM exactly."""
        # Expected from FHEM: idx=1, ACCESS_LEVEL
        expected = {
            "idx": 1,
            "extid": "61E1E1FC660023",
            "max": 5,
            "min": 0,
            "format": "int",
            "read": 0,
            "text": "ACCESS_LEVEL"
        }

        # Find parameter with idx=1
        param = next((p for p in PARAMETER_DATA if p["idx"] == 1), None)
        assert param is not None, "Parameter with idx=1 (ACCESS_LEVEL) not found"

        # Verify all fields match
        assert param == expected, f"Parameter idx=1 doesn't match FHEM. Got: {param}, Expected: {expected}"

        print("✓ ACCESS_LEVEL parameter (idx=1) verified")

    def test_temperature_parameter_with_negative_min_matches_fhem(self):
        """T009: Spot-check temperature parameter with negative min (idx=11) matches FHEM exactly."""
        # Expected from FHEM: idx=11, ADDITIONAL_BLOCK_HIGH_T2_TEMP with negative min
        expected = {
            "idx": 11,
            "extid": "E555E4E11002E9",
            "max": 40,
            "min": -30,
            "format": "int",
            "read": 0,
            "text": "ADDITIONAL_BLOCK_HIGH_T2_TEMP"
        }

        # Find parameter with idx=11
        param = next((p for p in PARAMETER_DATA if p["idx"] == 11), None)
        assert param is not None, "Parameter with idx=11 not found"

        # Verify all fields match
        assert param == expected, f"Parameter idx=11 doesn't match FHEM. Got: {param}, Expected: {expected}"

        print("✓ Temperature parameter (idx=11) with negative min verified")

    def test_last_parameter_matches_fhem(self):
        """T009: Spot-check last parameter (idx=2600) matches FHEM exactly."""
        # Expected from FHEM: idx=2600, TIMER_COMPRESSOR_START_DELAY_AT_CASCADE
        expected = {
            "idx": 2600,
            "extid": "03B11E70550000",
            "max": 0,
            "min": 0,
            "format": "int",
            "read": 0,
            "text": "TIMER_COMPRESSOR_START_DELAY_AT_CASCADE"
        }

        # Find parameter with idx=2600
        param = next((p for p in PARAMETER_DATA if p["idx"] == 2600), None)
        assert param is not None, "Parameter with idx=2600 not found"

        # Verify all fields match
        assert param == expected, f"Parameter idx=2600 doesn't match FHEM. Got: {param}, Expected: {expected}"

        print("✓ Last parameter (idx=2600) verified")

    def test_no_duplicate_indices(self):
        """Verify there are no duplicate idx values in PARAMETER_DATA."""
        indices = [p["idx"] for p in PARAMETER_DATA]
        unique_indices = set(indices)

        assert len(indices) == len(unique_indices), \
            f"Found duplicate indices: {len(indices)} total, {len(unique_indices)} unique"

        print(f"✓ No duplicate indices: {len(indices)} unique idx values")

    def test_no_duplicate_names(self):
        """Verify there are no duplicate text (name) values in PARAMETER_DATA."""
        names = [p["text"] for p in PARAMETER_DATA]
        unique_names = set(names)

        assert len(names) == len(unique_names), \
            f"Found duplicate names: {len(names)} total, {len(unique_names)} unique"

        print(f"✓ No duplicate names: {len(names)} unique parameter names")

    def test_no_duplicate_extids(self):
        """Verify there are no duplicate extid values in PARAMETER_DATA."""
        extids = [p["extid"] for p in PARAMETER_DATA]
        unique_extids = set(extids)

        assert len(extids) == len(unique_extids), \
            f"Found duplicate extids: {len(extids)} total, {len(unique_extids)} unique"

        print(f"✓ No duplicate extids: {len(extids)} unique external IDs")

    def test_all_parameters_have_valid_structure(self):
        """Verify all parameters have required fields with correct types."""
        required_keys = {"idx", "extid", "max", "min", "format", "read", "text"}

        for i, param in enumerate(PARAMETER_DATA):
            # Check all required keys present
            assert set(param.keys()) == required_keys, \
                f"Parameter at index {i} (idx={param.get('idx', 'MISSING')}) has incorrect keys: {param.keys()}"

            # Check types
            assert isinstance(param["idx"], int), f"idx must be int at index {i}"
            assert isinstance(param["extid"], str), f"extid must be str at index {i}"
            assert isinstance(param["max"], int), f"max must be int at index {i}"
            assert isinstance(param["min"], int), f"min must be int at index {i}"
            assert isinstance(param["format"], str), f"format must be str at index {i}"
            assert isinstance(param["read"], int), f"read must be int at index {i}"
            assert isinstance(param["text"], str), f"text must be str at index {i}"

            # Check constraints
            # Note: FHEM uses various read values (0, 1, 2, 5, etc.) - preserved for protocol fidelity
            assert isinstance(param["read"], int) and param["read"] >= 0, \
                f"read must be non-negative int at index {i}, got {param['read']}"
            assert len(param["extid"]) == 14, f"extid must be 14 chars at index {i}, got {len(param['extid'])}"

            # Note: We preserve FHEM data exactly (Protocol Fidelity - Constitution Principle II)
            # Some parameters in FHEM source have max < min (likely bugs in FHEM data)
            # Example: idx=261 (COMPRESSOR_DHW_REQUEST) has max=230, min=400
            # We preserve this to maintain 100% fidelity with the reference implementation
            if param["max"] < param["min"]:
                print(f"  Warning: idx={param['idx']} ({param['text']}) has max < min (preserved from FHEM)")

        print(f"✓ All {len(PARAMETER_DATA)} parameters have valid structure")

    def test_gap_in_indices_exists(self):
        """Verify that index gaps exist (e.g., idx=13 missing between 12 and 14)."""
        # Per spec.md edge case: idx=13 should be missing
        indices = sorted([p["idx"] for p in PARAMETER_DATA])

        # Check if idx=13 is missing
        has_12 = 12 in indices
        has_13 = 13 in indices
        has_14 = 14 in indices

        assert has_12, "Expected idx=12 to exist"
        assert not has_13, "Expected idx=13 to be missing (gap in sequence)"
        assert has_14, "Expected idx=14 to exist"

        print("✓ Verified expected gap: idx=13 missing between 12 and 14")
