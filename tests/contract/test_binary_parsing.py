"""Contract tests verifying binary element parsing matches FHEM reference.

# PROTOCOL: Binary element structure from fhem/26_KM273v018.pm:2135-2143
# Perl unpack: "nH14NNc" = idx(2, BE), extid(7), max(4, BE), min(4, BE), len(1)

These tests verify that our Python implementation parses binary element data
exactly as FHEM does. This ensures compliance with Constitution Principle II
(Protocol Fidelity).
"""

import re
import struct
import pytest


class TestBinaryStructureMatchesFhem:
    """T032: Contract tests verifying binary structure matches FHEM."""

    def test_fhem_uses_network_byte_order(self):
        """Verify FHEM uses big-endian (network byte order) format.

        # PROTOCOL: 'n' = unsigned short, network (big-endian)
        # PROTOCOL: 'N' = unsigned long, network (big-endian)
        """
        with open('fhem/26_KM273v018.pm', 'r') as f:
            content = f.read()

        # Find the unpack statement
        # Pattern: unpack("nH14NNc", ...)
        pattern = r'unpack\s*\(\s*["\']nH14NNc["\']'
        match = re.search(pattern, content)

        assert match is not None, (
            "Could not find unpack(\"nH14NNc\", ...) in FHEM source. "
            "Expected network byte order format string."
        )

        print(f"✓ Found FHEM unpack format at position {match.start()}")

    def test_fhem_converts_unsigned_to_signed(self):
        """Verify FHEM converts unsigned to signed for min/max.

        # PROTOCOL: $min2 = unpack 'l*', pack 'L*', $min2;
        """
        with open('fhem/26_KM273v018.pm', 'r') as f:
            content = f.read()

        # Find the signed conversion for min
        min_pattern = r"\$min2\s*=\s*unpack\s+'l\*'\s*,\s*pack\s+'L\*'\s*,\s*\$min2"
        min_match = re.search(min_pattern, content)

        assert min_match is not None, (
            "Could not find min value signed conversion in FHEM source. "
            "Expected: $min2 = unpack 'l*', pack 'L*', $min2"
        )

        # Find the signed conversion for max
        max_pattern = r"\$max2\s*=\s*unpack\s+'l\*'\s*,\s*pack\s+'L\*'\s*,\s*\$max2"
        max_match = re.search(max_pattern, content)

        assert max_match is not None, (
            "Could not find max value signed conversion in FHEM source. "
            "Expected: $max2 = unpack 'l*', pack 'L*', $max2"
        )

        print("✓ Found signed conversion for min and max values")

    def test_fhem_header_size_is_18_bytes(self):
        """Verify FHEM checks for 18-byte header.

        # PROTOCOL: if ($imax-$i1 > 18)
        """
        with open('fhem/26_KM273v018.pm', 'r') as f:
            content = f.read()

        # Find the header size check
        pattern = r'if\s*\(\s*\$imax\s*-\s*\$i1\s*>\s*18\s*\)'
        match = re.search(pattern, content)

        assert match is not None, (
            "Could not find header size check (> 18) in FHEM source."
        )

        print("✓ Found 18-byte header size check")

    def test_fhem_rejects_len_less_than_2(self):
        """Verify FHEM rejects len values less than 2.

        # PROTOCOL: if (... ($len2 > 1) ...)
        """
        with open('fhem/26_KM273v018.pm', 'r') as f:
            content = f.read()

        # Find the len validation
        pattern = r'\$len2\s*>\s*1'
        match = re.search(pattern, content)

        assert match is not None, (
            "Could not find len > 1 validation in FHEM source."
        )

        print("✓ Found minimum len validation (len > 1)")

    def test_fhem_rejects_len_100_or_more(self):
        """Verify FHEM rejects len values of 100 or more.

        # PROTOCOL: if (... ($len2 < 100) ...)
        """
        with open('fhem/26_KM273v018.pm', 'r') as f:
            content = f.read()

        # Find the max len validation
        pattern = r'\$len2\s*<\s*100'
        match = re.search(pattern, content)

        assert match is not None, (
            "Could not find len < 100 validation in FHEM source."
        )

        print("✓ Found maximum len validation (len < 100)")

    def test_fhem_name_length_is_len_minus_1(self):
        """Verify FHEM extracts name as len-1 bytes.

        # PROTOCOL: my $element2 = substr(...,$i1+18,$len2-1);
        """
        with open('fhem/26_KM273v018.pm', 'r') as f:
            content = f.read()

        # Find the name extraction
        pattern = r'substr\s*\([^,]+,\s*\$i1\s*\+\s*18\s*,\s*\$len2\s*-\s*1\s*\)'
        match = re.search(pattern, content)

        assert match is not None, (
            "Could not find name extraction (substr(...,$i1+18,$len2-1)) in FHEM source."
        )

        print("✓ Found name extraction (len-1 bytes at offset 18)")

    def test_fhem_advances_offset_correctly(self):
        """Verify FHEM advances offset by 18+len.

        # PROTOCOL: $i1 += 18+$len2;
        """
        with open('fhem/26_KM273v018.pm', 'r') as f:
            content = f.read()

        # Find the offset advancement
        pattern = r'\$i1\s*\+=\s*18\s*\+\s*\$len2'
        match = re.search(pattern, content)

        assert match is not None, (
            "Could not find offset advancement ($i1 += 18+$len2) in FHEM source."
        )

        print("✓ Found offset advancement (18 + len)")


class TestBinaryParsingMatchesFhem:
    """Test that Python parsing matches FHEM's expected output."""

    def test_parse_known_parameter_matches_fhem(self):
        """Verify parsing produces same result as FHEM for known parameters."""
        from buderus_wps.discovery import ParameterDiscovery

        # Create binary data that should produce ACCESS_LEVEL parameter
        # This simulates what the device would send
        data = struct.pack('>H', 1)  # idx = 1 (big-endian)
        data += bytes.fromhex("61E1E1FC660023")  # extid
        data += struct.pack('>I', 5)  # max = 5 (big-endian unsigned)
        data += struct.pack('>I', 0)  # min = 0 (big-endian unsigned)
        data += struct.pack('b', 13)  # len = 13 (12 chars + null)
        data += b"ACCESS_LEVEL\x00"  # name with null terminator

        element, _ = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['idx'] == 1
        assert element['extid'] == "61E1E1FC660023"
        assert element['max'] == 5
        assert element['min'] == 0
        assert element['text'] == "ACCESS_LEVEL"

        print("✓ Parsed ACCESS_LEVEL matches FHEM expected output")

    def test_parse_negative_min_matches_fhem(self):
        """Verify negative min values are parsed like FHEM.

        FHEM converts unsigned to signed: unpack 'l*', pack 'L*', $min2
        -30 as unsigned 32-bit = 4294967266 (0xFFFFFFE2)
        """
        from buderus_wps.discovery import ParameterDiscovery

        # -30 as unsigned 32-bit is 0xFFFFFFE2
        min_unsigned = (-30) & 0xFFFFFFFF

        data = struct.pack('>H', 11)  # idx = 11
        data += bytes.fromhex("E555E4E11002E9")  # extid
        data += struct.pack('>I', 40)  # max = 40
        data += struct.pack('>I', min_unsigned)  # min = -30 as unsigned
        data += struct.pack('b', 29)  # len
        data += b"ADDITIONAL_BLOCK_HIGH_T2_TEMP\x00"

        element, _ = ParameterDiscovery.parse_element(data, 0)

        assert element is not None
        assert element['min'] == -30, f"Expected -30, got {element['min']}"
        assert element['max'] == 40

        print("✓ Negative min value (-30) parsed correctly like FHEM")

    def test_header_field_sizes_match_fhem(self):
        """Verify header field byte positions match FHEM unpack format.

        n = 2 bytes (offset 0-1)
        H14 = 7 bytes (offset 2-8)
        N = 4 bytes (offset 9-12)
        N = 4 bytes (offset 13-16)
        c = 1 byte (offset 17)
        Total header = 18 bytes
        """
        # idx at offset 0, 2 bytes
        idx_data = struct.pack('>H', 0x1234)
        assert len(idx_data) == 2

        # extid at offset 2, 7 bytes
        extid_data = bytes.fromhex("AABBCCDDEEFF00")
        assert len(extid_data) == 7

        # max at offset 9, 4 bytes
        max_data = struct.pack('>I', 0x12345678)
        assert len(max_data) == 4

        # min at offset 13, 4 bytes
        min_data = struct.pack('>I', 0x87654321)
        assert len(min_data) == 4

        # len at offset 17, 1 byte
        len_data = struct.pack('b', 10)
        assert len(len_data) == 1

        # Total header
        header = idx_data + extid_data + max_data + min_data + len_data
        assert len(header) == 18

        print("✓ Header field sizes match FHEM format (18 bytes total)")
