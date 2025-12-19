"""Unit tests for ParameterDiscovery class and binary element parsing.

# PROTOCOL: Binary element structure from fhem/26_KM273v018.pm:2135-2143
# Perl unpack format: "nH14NNc" = idx(2), extid(7), max(4), min(4), len(1)
# Network byte order (big-endian) for idx, max, min

These tests verify that parse_element() correctly parses the binary element
structure used in the CAN bus discovery protocol.
"""

import struct
import pytest


def create_element_binary(idx: int, extid: str, max_val: int, min_val: int, name: str) -> bytes:
    """Create binary element data for testing.

    # PROTOCOL: Format matches fhem/26_KM273v018.pm:2135 unpack("nH14NNc", ...)
    # Big-endian format for idx, max, min

    Args:
        idx: Parameter index (0-65535)
        extid: 14-character hex string (7 bytes)
        max_val: Maximum value (signed 32-bit)
        min_val: Minimum value (signed 32-bit)
        name: Parameter name (will be null-terminated)

    Returns:
        Binary data in FHEM format
    """
    # Pack header: idx(2 bytes BE), extid(7 bytes), max(4 bytes BE), min(4 bytes BE)
    extid_bytes = bytes.fromhex(extid)
    if len(extid_bytes) != 7:
        raise ValueError(f"extid must be 14 hex chars (7 bytes), got {len(extid)} chars")

    # Convert signed int32 to unsigned for packing
    max_unsigned = max_val & 0xFFFFFFFF
    min_unsigned = min_val & 0xFFFFFFFF

    header = struct.pack('>H', idx)  # Big-endian unsigned short
    header += extid_bytes
    header += struct.pack('>I', max_unsigned)  # Big-endian unsigned int
    header += struct.pack('>I', min_unsigned)  # Big-endian unsigned int

    # Name with length byte and null terminator
    name_bytes = name.encode('ascii') + b'\x00'
    len_byte = struct.pack('b', len(name_bytes))  # Signed char

    return header + len_byte + name_bytes


class TestParseElementValid:
    """T030: Test parse_element() with valid binary data."""

    def test_parse_element_extracts_idx(self):
        """Verify idx is correctly extracted from binary data."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name="ACCESS_LEVEL"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['idx'] == 1

    def test_parse_element_extracts_extid(self):
        """Verify extid is correctly extracted as uppercase hex string."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=0,
            extid="814A53C66A0802",
            max_val=0,
            min_val=0,
            name="ACCESSORIES_CONNECTED_BITMASK"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['extid'] == "814A53C66A0802"

    def test_parse_element_extracts_max(self):
        """Verify max is correctly extracted."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name="ACCESS_LEVEL"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['max'] == 5

    def test_parse_element_extracts_min(self):
        """Verify min is correctly extracted."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name="ACCESS_LEVEL"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['min'] == 0

    def test_parse_element_extracts_negative_min(self):
        """Verify negative min values are correctly extracted.

        # PROTOCOL: FHEM converts unsigned to signed:
        # $min2 = unpack 'l*', pack 'L*', $min2
        """
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=11,
            extid="E555E4E11002E9",
            max_val=40,
            min_val=-30,  # Negative value
            name="ADDITIONAL_BLOCK_HIGH_T2_TEMP"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['min'] == -30
        assert element['max'] == 40

    def test_parse_element_extracts_name(self):
        """Verify name is correctly extracted (null-terminated)."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name="ACCESS_LEVEL"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['text'] == "ACCESS_LEVEL"

    def test_parse_element_returns_correct_next_offset(self):
        """Verify next_offset points to the next element."""
        from buderus_wps.discovery import ParameterDiscovery

        name = "ACCESS_LEVEL"
        data = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name=name
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        # PROTOCOL: $i1 += 18+$len2 where len2 = len(name) + 1 (null terminator)
        # Header (18 bytes) includes the len byte, so:
        # next_offset = 18 + len(name) + 1 (for null terminator)
        expected_next = 18 + len(name) + 1
        assert next_offset == expected_next

    def test_parse_element_at_offset(self):
        """Verify parsing works at non-zero offset."""
        from buderus_wps.discovery import ParameterDiscovery

        # Create data with padding at the start
        padding = b'\x00' * 50
        element_data = create_element_binary(
            idx=42,
            extid="ABCDEF1234ABCD",
            max_val=100,
            min_val=10,
            name="TEST_PARAM"
        )

        data = padding + element_data

        element, next_offset = ParameterDiscovery.parse_element(data, 50)

        assert element is not None
        assert element['idx'] == 42
        assert element['text'] == "TEST_PARAM"
        # PROTOCOL: next_offset = offset + 18 + len(name) + 1 (null terminator)
        assert next_offset == 50 + 18 + len("TEST_PARAM") + 1

    def test_parse_element_with_large_max(self):
        """Verify large max values are correctly extracted."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=22,
            extid="C02D7CE3A909E9",
            max_val=16777216,  # 2^24
            min_val=0,
            name="ADDITIONAL_DHW_ACKNOWLEDGED"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['max'] == 16777216

    def test_parse_element_sets_default_format(self):
        """Verify format is set to 'int' by default."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name="ACCESS_LEVEL"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['format'] == "int"

    def test_parse_element_sets_default_read(self):
        """Verify read flag is set to 0 by default."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name="ACCESS_LEVEL"
        )

        element, next_offset = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['read'] == 0


class TestParseElementErrors:
    """T031: Test parse_element() error handling."""

    def test_parse_element_truncated_header_returns_none(self):
        """Verify truncated data (less than 18 bytes) returns None."""
        from buderus_wps.discovery import ParameterDiscovery

        # Only 10 bytes of header
        truncated_data = b'\x00\x01\x61\xE1\xE1\xFC\x66\x00\x23\x00'

        element, next_offset = ParameterDiscovery.parse_element(truncated_data, 0)

        assert element is None
        assert next_offset == -1

    def test_parse_element_truncated_name_returns_none(self):
        """Verify truncated name data returns None."""
        from buderus_wps.discovery import ParameterDiscovery

        # Full header but truncated name
        header = struct.pack('>H', 1)  # idx
        header += bytes.fromhex("61E1E1FC660023")  # extid
        header += struct.pack('>I', 5)  # max
        header += struct.pack('>I', 0)  # min
        header += struct.pack('b', 20)  # len says 20 bytes but we don't have them
        header += b'SHORT'  # Only 5 bytes instead of 19

        element, next_offset = ParameterDiscovery.parse_element(header, 0)

        assert element is None
        assert next_offset == -1

    def test_parse_element_zero_length_name_returns_none(self):
        """Verify zero-length name is handled."""
        from buderus_wps.discovery import ParameterDiscovery

        # Header with len=0
        header = struct.pack('>H', 1)  # idx
        header += bytes.fromhex("61E1E1FC660023")  # extid
        header += struct.pack('>I', 5)  # max
        header += struct.pack('>I', 0)  # min
        header += struct.pack('b', 0)  # len = 0

        element, next_offset = ParameterDiscovery.parse_element(header, 0)

        assert element is None
        assert next_offset == -1

    def test_parse_element_negative_length_returns_none(self):
        """Verify negative length byte is rejected."""
        from buderus_wps.discovery import ParameterDiscovery

        header = struct.pack('>H', 1)  # idx
        header += bytes.fromhex("61E1E1FC660023")  # extid
        header += struct.pack('>I', 5)  # max
        header += struct.pack('>I', 0)  # min
        header += struct.pack('b', -1)  # negative len

        element, next_offset = ParameterDiscovery.parse_element(header, 0)

        assert element is None
        assert next_offset == -1

    def test_parse_element_excessive_length_returns_none(self):
        """Verify unreasonably large length (>100) is rejected.

        # PROTOCOL: FHEM rejects len >= 100: if (... ($len2 < 100))
        """
        from buderus_wps.discovery import ParameterDiscovery

        header = struct.pack('>H', 1)  # idx
        header += bytes.fromhex("61E1E1FC660023")  # extid
        header += struct.pack('>I', 5)  # max
        header += struct.pack('>I', 0)  # min
        header += struct.pack('b', 100)  # len = 100 (too large)

        # Add enough bytes to satisfy the length
        header += b'X' * 100

        element, next_offset = ParameterDiscovery.parse_element(header, 0)

        assert element is None
        assert next_offset == -1

    def test_parse_element_offset_past_end_returns_none(self):
        """Verify offset past data end returns None."""
        from buderus_wps.discovery import ParameterDiscovery

        data = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name="ACCESS_LEVEL"
        )

        # Try to parse at an offset past the data
        element, next_offset = ParameterDiscovery.parse_element(data, 1000)

        assert element is None
        assert next_offset == -1

    def test_parse_element_empty_data_returns_none(self):
        """Verify empty data returns None."""
        from buderus_wps.discovery import ParameterDiscovery

        element, next_offset = ParameterDiscovery.parse_element(b'', 0)

        assert element is None
        assert next_offset == -1


class TestParseMultipleElements:
    """Test parsing multiple consecutive elements."""

    def test_parse_consecutive_elements(self):
        """Verify multiple consecutive elements can be parsed."""
        from buderus_wps.discovery import ParameterDiscovery

        # Create two consecutive elements
        element1 = create_element_binary(
            idx=0,
            extid="814A53C66A0802",
            max_val=0,
            min_val=0,
            name="ACCESSORIES_CONNECTED_BITMASK"
        )
        element2 = create_element_binary(
            idx=1,
            extid="61E1E1FC660023",
            max_val=5,
            min_val=0,
            name="ACCESS_LEVEL"
        )

        data = element1 + element2

        # Parse first element
        e1, offset1 = ParameterDiscovery.parse_element(data, 0)
        assert e1 is not None
        assert e1['idx'] == 0
        assert e1['text'] == "ACCESSORIES_CONNECTED_BITMASK"

        # Parse second element at returned offset
        e2, offset2 = ParameterDiscovery.parse_element(data, offset1)
        assert e2 is not None
        assert e2['idx'] == 1
        assert e2['text'] == "ACCESS_LEVEL"

    def test_parse_until_end_of_data(self):
        """Verify parsing continues until data exhausted."""
        from buderus_wps.discovery import ParameterDiscovery

        # Create three elements
        elements_data = b''
        for i in range(3):
            elements_data += create_element_binary(
                idx=i,
                extid=f"00000000000{i:03d}",
                max_val=100 + i,
                min_val=i,
                name=f"PARAM_{i}"
            )

        parsed = []
        offset = 0
        while offset < len(elements_data):
            element, next_offset = ParameterDiscovery.parse_element(elements_data, offset)
            if element is None:
                break
            parsed.append(element)
            offset = next_offset

        assert len(parsed) == 3
        assert [e['idx'] for e in parsed] == [0, 1, 2]
