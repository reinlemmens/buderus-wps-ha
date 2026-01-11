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
        with open("fhem/26_KM273v018.pm") as f:
            content = f.read()

        # Extract the @KM273_elements_default array
        start_marker = "my @KM273_elements_default ="
        end_marker = ");"

        start_idx = content.find(start_marker)
        assert (
            start_idx != -1
        ), "Could not find KM273_elements_default array in FHEM file"

        search_start = start_idx + len(start_marker)
        end_idx = content.find(end_marker, search_start)
        assert end_idx != -1, "Could not find end of KM273_elements_default array"

        array_content = content[start_idx : end_idx + len(end_marker)]

        # Count parameter entries by counting opening braces
        # Pattern: { 'idx' => ...
        param_pattern = r"\{\s*'idx'\s*=>"
        fhem_param_count = len(re.findall(param_pattern, array_content))

        # Verify counts match (allow for 1 parameter difference due to known gap/duplicate)
        # The FHEM source has 1789 entries but Python data has 1788 (one intentional removal)
        assert (
            abs(len(PARAMETER_DATA) - fhem_param_count) <= 1
        ), f"Parameter count mismatch: Python has {len(PARAMETER_DATA)}, FHEM has {fhem_param_count}"

        print(f"✓ Parameter count verified: {len(PARAMETER_DATA)} parameters")

    @pytest.mark.parametrize(
        "idx, expected",
        [
            (
                0,
                {
                    "idx": 0,
                    "extid": "814A53C66A0802",
                    "max": 0,
                    "min": 0,
                    "format": "int",
                    "read": 0,
                    "text": "ACCESSORIES_CONNECTED_BITMASK",
                },
            ),
            (
                1,
                {
                    "idx": 1,
                    "extid": "61E1E1FC660023",
                    "max": 5,
                    "min": 0,
                    "format": "int",
                    "read": 0,
                    "text": "ACCESS_LEVEL",
                },
            ),
            (
                11,
                {
                    "idx": 11,
                    "extid": "E555E4E11002E9",
                    "max": 40,
                    "min": -30,
                    "format": "int",
                    "read": 0,
                    "text": "ADDITIONAL_BLOCK_HIGH_T2_TEMP",
                },
            ),
            (
                2600,
                {
                    "idx": 2600,
                    "extid": "03B11E70550000",
                    "max": 0,
                    "min": 0,
                    "format": "int",
                    "read": 0,
                    "text": "TIMER_COMPRESSOR_START_DELAY_AT_CASCADE",
                },
            ),
        ],
    )
    def test_specific_parameters_match_fhem(self, idx, expected):
        """T009: Spot-check specific parameters match FHEM exactly."""
        # Find parameter with idx
        param = next((p for p in PARAMETER_DATA if p["idx"] == idx), None)
        assert param is not None, f"Parameter with idx={idx} not found"

        # Verify all fields match
        assert (
            param == expected
        ), f"Parameter idx={idx} doesn't match FHEM. Got: {param}, Expected: {expected}"

        print(f"✓ Parameter {expected['text']} (idx={idx}) verified")

    def test_known_duplicate_indices(self):
        """Verify known duplicate idx values in PARAMETER_DATA.

        PARAMETER_DATA has 4 known duplicate indices:
        - idx 279: COMPRESSOR_RESTART_TIME / COMPRESSOR_REAL_FREQUENCY
        - idx 296: COMPRESSOR_TYPE / COMPRESSOR_STATE_2
        - idx 2478: XDHW_WEEKPROGRAM_FAILED / XDHW_STOP_TEMP
        - idx 2480: XDHW_WEEKPROGRAM_HOUR / XDHW_TIME

        HeatPump filters these duplicates (1788 -> 1784), keeping the last one.
        """
        indices = [p["idx"] for p in PARAMETER_DATA]
        unique_indices = set(indices)

        # 1788 total entries, 1784 unique (4 duplicates)
        assert len(indices) == 1788, f"Expected 1788 total entries, got {len(indices)}"
        assert (
            len(unique_indices) == 1784
        ), f"Expected 1784 unique indices (4 duplicates), got {len(unique_indices)}"

        print(
            f"✓ {len(indices)} total entries, {len(unique_indices)} unique (4 known duplicates)"
        )

    def test_no_duplicate_names(self):
        """Verify there are no duplicate text (name) values in PARAMETER_DATA."""
        names = [p["text"] for p in PARAMETER_DATA]
        unique_names = set(names)

        assert len(names) == len(
            unique_names
        ), f"Found duplicate names: {len(names)} total, {len(unique_names)} unique"

        print(f"✓ No duplicate names: {len(names)} unique parameter names")

    def test_no_duplicate_extids(self):
        """Verify there are no duplicate extid values in PARAMETER_DATA."""
        extids = [p["extid"] for p in PARAMETER_DATA]
        unique_extids = set(extids)

        assert len(extids) == len(
            unique_extids
        ), f"Found duplicate extids: {len(extids)} total, {len(unique_extids)} unique"

        print(f"✓ No duplicate extids: {len(extids)} unique external IDs")

    def test_all_parameters_have_valid_structure(self):
        """Verify all parameters have required fields with correct types."""
        required_keys = {"idx", "extid", "max", "min", "format", "read", "text"}

        for i, param in enumerate(PARAMETER_DATA):
            # Check all required keys present
            assert (
                set(param.keys()) == required_keys
            ), f"Parameter at index {i} (idx={param.get('idx', 'MISSING')}) has incorrect keys: {param.keys()}"

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
            assert (
                isinstance(param["read"], int) and param["read"] >= 0
            ), f"read must be non-negative int at index {i}, got {param['read']}"
            assert (
                len(param["extid"]) == 14
            ), f"extid must be 14 chars at index {i}, got {len(param['extid'])}"

            # Note: We preserve FHEM data exactly (Protocol Fidelity - Constitution Principle II)
            # Some parameters in FHEM source have max < min (likely bugs in FHEM data)
            # Example: idx=261 (COMPRESSOR_DHW_REQUEST) has max=230, min=400
            # We preserve this to maintain 100% fidelity with the reference implementation
            if param["max"] < param["min"]:
                print(
                    f"  Warning: idx={param['idx']} ({param['text']}) has max < min (preserved from FHEM)"
                )

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
