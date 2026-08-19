"""Contract tests verifying parameter data matches the device element list.

# PROTOCOL: idx values are device-specific and come from element discovery.
# PARAMETER_DATA is generated from a real device capture (the authoritative
# source for CAN addressing on this heat pump) with format/read metadata
# merged from the FHEM reference implementation (fhem/26_KM273v018.pm).
# Regenerate with: python3 tools/generate_parameter_data.py

These tests parse the device capture and verify that PARAMETER_DATA matches
it exactly. Duplicate idx values are forbidden: idx maps 1:1 to a CAN ID
(0x04003FE0 | idx << 14), so a duplicate would make two parameters share a
CAN ID and shadow each other in idx-based lookups (GitHub issue #11).
"""

import re

import pytest
from buderus_wps.parameter_data import PARAMETER_DATA

CAPTURE_PATH = "fhem/fhem-capture/capture-20251224-174533.hex"
ELEMENT_RE = re.compile(
    r"KM273_ReadElementList done, "
    r"idx=(\d+) extid=([0-9a-f]+) max=(-?\d+) min=(-?\d+) element=([A-Za-z0-9_]+)"
)


def parse_capture():
    elements = {}
    with open(CAPTURE_PATH, errors="replace") as fh:
        for line in fh:
            m = ELEMENT_RE.search(line)
            if m:
                elements[m.group(5)] = {
                    "idx": int(m.group(1)),
                    "extid": m.group(2).upper(),
                    "max": int(m.group(3)),
                    "min": int(m.group(4)),
                }
    return elements


class TestParameterDataFidelity:
    """Verify PARAMETER_DATA matches the device element list exactly."""

    def test_parameter_count_matches_device(self):
        """T008: Verify total parameter count matches the device capture."""
        device = parse_capture()
        assert len(device) > 0, f"No elements parsed from {CAPTURE_PATH}"
        assert len(PARAMETER_DATA) == len(device), (
            f"Parameter count mismatch: Python has {len(PARAMETER_DATA)}, "
            f"device capture has {len(device)}"
        )

        print(f"✓ Parameter count verified: {len(PARAMETER_DATA)} parameters")

    def test_all_parameters_match_device(self):
        """Every entry's idx/extid/min/max must match the device capture."""
        device = parse_capture()
        for param in PARAMETER_DATA:
            elem = device.get(param["text"])
            assert elem is not None, f"{param['text']} not in device capture"
            for key in ("idx", "extid", "max", "min"):
                assert param[key] == elem[key], (
                    f"{param['text']}.{key}: Python has {param[key]!r}, "
                    f"device has {elem[key]!r}"
                )

        print(f"✓ All {len(PARAMETER_DATA)} parameters match the device capture")

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
            # Device idx 2605 (FHEM static table had 2600); regression check
            # that the device value wins.
            (
                2605,
                {
                    "idx": 2605,
                    "extid": "03B11E70550000",
                    "max": 0,
                    "min": 0,
                    "format": "int",
                    "read": 0,
                    "text": "TIMER_COMPRESSOR_START_DELAY_AT_CASCADE",
                },
            ),
            # The two parameters from issue #11: device-true indices, no
            # longer colliding with XDHW_WEEKPROGRAM_FAILED/_HOUR.
            (
                2478,
                {
                    "idx": 2478,
                    "extid": "EE1597E1AD010E",
                    "max": 650,
                    "min": 500,
                    "format": "tem",
                    "read": 1,
                    "text": "XDHW_STOP_TEMP",
                },
            ),
            (
                2480,
                {
                    "idx": 2480,
                    "extid": "E1263DCA71010F",
                    "max": 48,
                    "min": 0,
                    "format": "int",
                    "read": 1,
                    "text": "XDHW_TIME",
                },
            ),
        ],
    )
    def test_specific_parameters(self, idx, expected):
        """T009: Spot-check specific parameters."""
        # Find parameter with idx
        param = next((p for p in PARAMETER_DATA if p["idx"] == idx), None)
        assert param is not None, f"Parameter with idx={idx} not found"

        # Verify all fields match
        assert param == expected, (
            f"Parameter idx={idx} doesn't match. Got: {param}, Expected: {expected}"
        )

        print(f"✓ Parameter {expected['text']} (idx={idx}) verified")

    def test_no_duplicate_indices(self):
        """Duplicate idx values are forbidden (regression test for issue #11).

        idx maps 1:1 to a CAN ID, so duplicates make parameters shadow each
        other in idx lookups and can corrupt the discovery merge.
        """
        indices = [p["idx"] for p in PARAMETER_DATA]
        duplicates = sorted({i for i in indices if indices.count(i) > 1})

        assert not duplicates, f"Duplicate idx values found: {duplicates}"

        print(f"✓ {len(indices)} entries, all idx values unique")

    def test_no_duplicate_names(self):
        """Verify there are no duplicate text (name) values in PARAMETER_DATA."""
        names = [p["text"] for p in PARAMETER_DATA]
        unique_names = set(names)

        assert len(names) == len(unique_names), (
            f"Found duplicate names: {len(names)} total, {len(unique_names)} unique"
        )

        print(f"✓ No duplicate names: {len(names)} unique parameter names")

    def test_no_duplicate_extids(self):
        """Verify there are no duplicate extid values in PARAMETER_DATA."""
        extids = [p["extid"] for p in PARAMETER_DATA]
        unique_extids = set(extids)

        assert len(extids) == len(unique_extids), (
            f"Found duplicate extids: {len(extids)} total, {len(unique_extids)} unique"
        )

        print(f"✓ No duplicate extids: {len(extids)} unique external IDs")

    def test_all_parameters_have_valid_structure(self):
        """Verify all parameters have required fields with correct types."""
        required_keys = {"idx", "extid", "max", "min", "format", "read", "text"}

        for i, param in enumerate(PARAMETER_DATA):
            # Check all required keys present
            assert set(param.keys()) == required_keys, (
                f"Parameter at index {i} (idx={param.get('idx', 'MISSING')}) has incorrect keys: {param.keys()}"
            )

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
            assert isinstance(param["read"], int) and param["read"] >= 0, (
                f"read must be non-negative int at index {i}, got {param['read']}"
            )
            assert len(param["extid"]) == 14, (
                f"extid must be 14 chars at index {i}, got {len(param['extid'])}"
            )

            # Note: Some parameters have max < min (preserved from device/FHEM data)
            if param["max"] < param["min"]:
                print(
                    f"  Warning: idx={param['idx']} ({param['text']}) has max < min (preserved)"
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
