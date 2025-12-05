"""Unit tests for element list discovery protocol parsing.

Tests the ElementListParser class that parses CAN responses from the heat pump's
element list discovery protocol.

Protocol Reference: FHEM 26_KM273v018.pm lines 2052-2164
"""

import pytest
from buderus_wps.element_discovery import ElementListParser, DiscoveredElement


class TestParseCountResponse:
    """Tests for ElementListParser.parse_count_response()"""

    def test_parse_valid_count_response(self):
        """Parse element count from T09FD7FE0 response."""
        # Response format: T09FD7FE0 + DLC + count (4 bytes big-endian in data)
        # Example: count = 1789 (0x06FD) parameters
        parser = ElementListParser()

        # CAN ID 0x09FD7FE0, DLC=4, data=0x000006FD (1789)
        can_id = 0x09FD7FE0
        data = bytes([0x00, 0x00, 0x06, 0xFD])

        count = parser.parse_count_response(can_id, data)
        assert count == 1789

    def test_parse_count_wrong_can_id(self):
        """Reject response with wrong CAN ID."""
        parser = ElementListParser()

        # Wrong CAN ID (should be 0x09FD7FE0)
        can_id = 0x04003FE0
        data = bytes([0x00, 0x00, 0x06, 0xFD])

        with pytest.raises(ValueError, match="Unexpected CAN ID"):
            parser.parse_count_response(can_id, data)

    def test_parse_count_short_data(self):
        """Reject response with insufficient data bytes."""
        parser = ElementListParser()

        can_id = 0x09FD7FE0
        data = bytes([0x00, 0x06])  # Only 2 bytes, need at least 4

        with pytest.raises(ValueError, match="Insufficient data"):
            parser.parse_count_response(can_id, data)

    def test_parse_count_zero(self):
        """Handle zero element count."""
        parser = ElementListParser()

        can_id = 0x09FD7FE0
        data = bytes([0x00, 0x00, 0x00, 0x00])

        count = parser.parse_count_response(can_id, data)
        assert count == 0


class TestParseDataChunk:
    """Tests for ElementListParser.parse_data_chunk()"""

    def test_parse_single_element(self):
        """Parse a single element from data chunk."""
        parser = ElementListParser()

        # Element format (18 bytes header + name):
        # - Bytes 0-1: idx (uint16 big-endian)
        # - Bytes 2-8: extid (7 bytes)
        # - Bytes 9-12: max (int32 big-endian, signed)
        # - Bytes 13-16: min (int32 big-endian, signed)
        # - Byte 17: name_length
        # - Bytes 18+: name (name_length-1 bytes, null-terminated in original)

        # Example: XDHW_TIME, idx=2475, max=48, min=0
        idx_bytes = (2475).to_bytes(2, 'big')  # 0x09AB
        extid = bytes.fromhex('E1263DCA71010F')  # 7 bytes
        max_val = (48).to_bytes(4, 'big', signed=True)
        min_val = (0).to_bytes(4, 'big', signed=True)
        name = b'XDHW_TIME'
        name_len = bytes([len(name) + 1])  # +1 for original null terminator

        data = idx_bytes + extid + max_val + min_val + name_len + name

        elements = parser.parse_data_chunk(data)

        assert len(elements) == 1
        elem = elements[0]
        assert elem.idx == 2475
        assert elem.extid == 'E1263DCA71010F'
        assert elem.max_value == 48
        assert elem.min_value == 0
        assert elem.text == 'XDHW_TIME'

    def test_parse_multiple_elements(self):
        """Parse multiple elements from a single data chunk."""
        parser = ElementListParser()

        def make_element(idx: int, name: str, max_val: int = 100, min_val: int = 0) -> bytes:
            idx_bytes = idx.to_bytes(2, 'big')
            extid = bytes([0x00] * 7)  # Dummy extid
            max_bytes = max_val.to_bytes(4, 'big', signed=True)
            min_bytes = min_val.to_bytes(4, 'big', signed=True)
            name_bytes = name.encode('ascii')
            name_len = bytes([len(name_bytes) + 1])
            return idx_bytes + extid + max_bytes + min_bytes + name_len + name_bytes

        data = make_element(100, 'PARAM_A') + make_element(101, 'PARAM_B') + make_element(102, 'PARAM_C')

        elements = parser.parse_data_chunk(data)

        assert len(elements) == 3
        assert elements[0].idx == 100
        assert elements[0].text == 'PARAM_A'
        assert elements[1].idx == 101
        assert elements[1].text == 'PARAM_B'
        assert elements[2].idx == 102
        assert elements[2].text == 'PARAM_C'

    def test_parse_negative_min_value(self):
        """Parse element with negative min value (signed int32)."""
        parser = ElementListParser()

        idx_bytes = (11).to_bytes(2, 'big')
        extid = bytes.fromhex('E555E4E11002E9')
        max_val = (40).to_bytes(4, 'big', signed=True)
        min_val = (-30).to_bytes(4, 'big', signed=True)  # Negative!
        name = b'ADDITIONAL_BLOCK_HIGH_T2_TEMP'
        name_len = bytes([len(name) + 1])

        data = idx_bytes + extid + max_val + min_val + name_len + name

        elements = parser.parse_data_chunk(data)

        assert len(elements) == 1
        assert elements[0].min_value == -30
        assert elements[0].max_value == 40

    def test_parse_empty_data(self):
        """Handle empty data chunk."""
        parser = ElementListParser()

        elements = parser.parse_data_chunk(bytes())
        assert elements == []

    def test_parse_incomplete_header(self):
        """Handle truncated data with incomplete header."""
        parser = ElementListParser()

        # Only 10 bytes, but header needs 18
        incomplete_data = bytes([0x00] * 10)

        # Should return empty list (incomplete element ignored)
        elements = parser.parse_data_chunk(incomplete_data)
        assert elements == []


class TestParseMalformedData:
    """Tests for malformed element data handling."""

    def test_invalid_name_length_too_large(self):
        """Handle name_length larger than remaining data."""
        parser = ElementListParser()

        idx_bytes = (100).to_bytes(2, 'big')
        extid = bytes([0x00] * 7)
        max_val = (100).to_bytes(4, 'big', signed=True)
        min_val = (0).to_bytes(4, 'big', signed=True)
        name_len = bytes([255])  # Way too large
        name = b'SHORT'

        data = idx_bytes + extid + max_val + min_val + name_len + name

        # Should skip malformed element and continue
        elements = parser.parse_data_chunk(data)
        assert elements == []

    def test_zero_name_length(self):
        """Handle element with zero name length."""
        parser = ElementListParser()

        idx_bytes = (100).to_bytes(2, 'big')
        extid = bytes([0x00] * 7)
        max_val = (100).to_bytes(4, 'big', signed=True)
        min_val = (0).to_bytes(4, 'big', signed=True)
        name_len = bytes([0])  # Zero length

        data = idx_bytes + extid + max_val + min_val + name_len

        # Should skip element with empty name
        elements = parser.parse_data_chunk(data)
        assert elements == []

    def test_non_ascii_name(self):
        """Handle element with non-ASCII characters in name."""
        parser = ElementListParser()

        idx_bytes = (100).to_bytes(2, 'big')
        extid = bytes([0x00] * 7)
        max_val = (100).to_bytes(4, 'big', signed=True)
        min_val = (0).to_bytes(4, 'big', signed=True)
        name = bytes([0x80, 0x81, 0x82])  # Non-ASCII
        name_len = bytes([len(name) + 1])

        data = idx_bytes + extid + max_val + min_val + name_len + name

        # Should handle gracefully (decode with 'replace' or skip)
        elements = parser.parse_data_chunk(data)
        # Either skipped or decoded with replacement chars
        assert len(elements) <= 1


class TestDiscoveredElement:
    """Tests for DiscoveredElement dataclass."""

    def test_discovered_element_creation(self):
        """Create DiscoveredElement with all fields."""
        elem = DiscoveredElement(
            idx=2475,
            extid='E1263DCA71010F',
            text='XDHW_TIME',
            min_value=0,
            max_value=48
        )

        assert elem.idx == 2475
        assert elem.extid == 'E1263DCA71010F'
        assert elem.text == 'XDHW_TIME'
        assert elem.min_value == 0
        assert elem.max_value == 48

    def test_discovered_element_can_id_calculation(self):
        """Calculate CAN ID from idx using formula: 0x04003FE0 | (idx << 14)."""
        elem = DiscoveredElement(
            idx=2475,
            extid='E1263DCA71010F',
            text='XDHW_TIME',
            min_value=0,
            max_value=48
        )

        expected_can_id = 0x04003FE0 | (2475 << 14)
        assert elem.can_id == expected_can_id
        assert elem.can_id == 0x066AFFE0
