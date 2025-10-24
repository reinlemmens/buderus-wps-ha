"""Unit tests for ValueEncoder class."""

import struct

import pytest

from buderus_wps.value_encoder import ValueEncoder


class TestTemperatureEncodingTemp:
    """Test temperature encoding with 'temp' format (2 bytes, factor 0.1)."""

    def test_encode_positive_temperature(self) -> None:
        """Test encoding positive temperature."""
        result = ValueEncoder.encode_temperature(29.1, "temp")
        assert result == b"\x01\x23"  # 0x0123 = 291
        assert len(result) == 2

    def test_encode_negative_temperature(self) -> None:
        """Test encoding negative temperature."""
        result = ValueEncoder.encode_temperature(-10.5, "temp")
        expected = struct.pack(">h", -105)
        assert result == expected

    def test_encode_zero_temperature(self) -> None:
        """Test encoding zero temperature."""
        result = ValueEncoder.encode_temperature(0.0, "temp")
        assert result == b"\x00\x00"

    def test_encode_max_temperature(self) -> None:
        """Test encoding maximum temperature."""
        result = ValueEncoder.encode_temperature(3276.7, "temp")
        expected = struct.pack(">h", 32767)
        assert result == expected

    def test_encode_min_temperature(self) -> None:
        """Test encoding minimum temperature."""
        result = ValueEncoder.encode_temperature(-3276.8, "temp")
        expected = struct.pack(">h", -32768)
        assert result == expected

    def test_encode_out_of_range_high(self) -> None:
        """Test encoding temperature above range raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            ValueEncoder.encode_temperature(4000.0, "temp")

    def test_encode_out_of_range_low(self) -> None:
        """Test encoding temperature below range raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            ValueEncoder.encode_temperature(-4000.0, "temp")


class TestTemperatureDecodingTemp:
    """Test temperature decoding with 'temp' format (2 bytes, factor 0.1)."""

    def test_decode_positive_temperature(self) -> None:
        """Test decoding positive temperature."""
        result = ValueEncoder.decode_temperature(b"\x01\x23", "temp")
        assert result == 29.1

    def test_decode_negative_temperature(self) -> None:
        """Test decoding negative temperature."""
        data = struct.pack(">h", -105)
        result = ValueEncoder.decode_temperature(data, "temp")
        assert result == -10.5

    def test_decode_zero_temperature(self) -> None:
        """Test decoding zero temperature."""
        result = ValueEncoder.decode_temperature(b"\x00\x00", "temp")
        assert result == 0.0

    def test_decode_invalid_length(self) -> None:
        """Test decoding with wrong data length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid data length"):
            ValueEncoder.decode_temperature(b"\x01", "temp")

    def test_encode_decode_roundtrip(self) -> None:
        """Test encode-decode roundtrip produces original value."""
        original = 25.5
        encoded = ValueEncoder.encode_temperature(original, "temp")
        decoded = ValueEncoder.decode_temperature(encoded, "temp")
        assert decoded == original


class TestTemperatureEncodingTempByte:
    """Test temperature encoding with 'temp_byte' format (1 byte, factor 0.5)."""

    def test_encode_temp_byte_format(self) -> None:
        """Test encoding with temp_byte format."""
        result = ValueEncoder.encode_temperature(22.5, "temp_byte")
        assert result == b"-"  # 0x2D = 45
        assert len(result) == 1

    def test_encode_temp_byte_zero(self) -> None:
        """Test encoding zero with temp_byte format."""
        result = ValueEncoder.encode_temperature(0.0, "temp_byte")
        assert result == b"\x00"

    def test_encode_temp_byte_max(self) -> None:
        """Test encoding maximum value with temp_byte format."""
        result = ValueEncoder.encode_temperature(127.5, "temp_byte")
        assert result == b"\xff"

    def test_encode_temp_byte_out_of_range_high(self) -> None:
        """Test encoding too high temperature raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            ValueEncoder.encode_temperature(128.0, "temp_byte")

    def test_encode_temp_byte_out_of_range_low(self) -> None:
        """Test encoding negative temperature raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            ValueEncoder.encode_temperature(-1.0, "temp_byte")


class TestTemperatureDecodingTempByte:
    """Test temperature decoding with 'temp_byte' format (1 byte, factor 0.5)."""

    def test_decode_temp_byte_format(self) -> None:
        """Test decoding with temp_byte format."""
        result = ValueEncoder.decode_temperature(b"-", "temp_byte")
        assert result == 22.5

    def test_decode_temp_byte_invalid_length(self) -> None:
        """Test decoding with wrong data length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid data length"):
            ValueEncoder.decode_temperature(b"\x01\x02", "temp_byte")

    def test_encode_decode_temp_byte_roundtrip(self) -> None:
        """Test temp_byte encode-decode roundtrip."""
        original = 45.5
        encoded = ValueEncoder.encode_temperature(original, "temp_byte")
        decoded = ValueEncoder.decode_temperature(encoded, "temp_byte")
        assert decoded == original


class TestTemperatureEncodingTempUint:
    """Test temperature encoding with 'temp_uint' format (1 byte, no factor)."""

    def test_encode_temp_uint_format(self) -> None:
        """Test encoding with temp_uint format."""
        result = ValueEncoder.encode_temperature(60.0, "temp_uint")
        assert result == b"<"  # 0x3C = 60
        assert len(result) == 1

    def test_encode_temp_uint_zero(self) -> None:
        """Test encoding zero with temp_uint format."""
        result = ValueEncoder.encode_temperature(0.0, "temp_uint")
        assert result == b"\x00"

    def test_encode_temp_uint_max(self) -> None:
        """Test encoding maximum value with temp_uint format."""
        result = ValueEncoder.encode_temperature(255.0, "temp_uint")
        assert result == b"\xff"

    def test_encode_temp_uint_out_of_range_high(self) -> None:
        """Test encoding too high temperature raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            ValueEncoder.encode_temperature(256.0, "temp_uint")

    def test_encode_temp_uint_out_of_range_low(self) -> None:
        """Test encoding negative temperature raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            ValueEncoder.encode_temperature(-1.0, "temp_uint")


class TestTemperatureDecodingTempUint:
    """Test temperature decoding with 'temp_uint' format (1 byte, no factor)."""

    def test_decode_temp_uint_format(self) -> None:
        """Test decoding with temp_uint format."""
        result = ValueEncoder.decode_temperature(b"<", "temp_uint")
        assert result == 60.0

    def test_decode_temp_uint_invalid_length(self) -> None:
        """Test decoding with wrong data length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid data length"):
            ValueEncoder.decode_temperature(b"\x01\x02", "temp_uint")

    def test_encode_decode_temp_uint_roundtrip(self) -> None:
        """Test temp_uint encode-decode roundtrip."""
        original = 100.0
        encoded = ValueEncoder.encode_temperature(original, "temp_uint")
        decoded = ValueEncoder.decode_temperature(encoded, "temp_uint")
        assert decoded == original


class TestTemperatureInvalidFormat:
    """Test temperature encoding/decoding with invalid formats."""

    def test_encode_invalid_format(self) -> None:
        """Test encoding with invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown temperature format"):
            ValueEncoder.encode_temperature(25.0, "invalid")  # type: ignore

    def test_decode_invalid_format(self) -> None:
        """Test decoding with invalid format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown temperature format"):
            ValueEncoder.decode_temperature(b"\x01\x02", "invalid")  # type: ignore


class TestIntegerEncoding:
    """Test integer encoding."""

    def test_encode_int_1_byte_signed(self) -> None:
        """Test encoding 1-byte signed integer."""
        result = ValueEncoder.encode_int(127, size_bytes=1, signed=True)
        assert result == b"\x7f"
        assert len(result) == 1

    def test_encode_int_1_byte_unsigned(self) -> None:
        """Test encoding 1-byte unsigned integer."""
        result = ValueEncoder.encode_int(200, size_bytes=1, signed=False)
        assert result == b"\xc8"

    def test_encode_int_2_byte_signed(self) -> None:
        """Test encoding 2-byte signed integer."""
        result = ValueEncoder.encode_int(1000, size_bytes=2, signed=True)
        assert result == b"\x03\xe8"
        assert len(result) == 2

    def test_encode_int_2_byte_unsigned(self) -> None:
        """Test encoding 2-byte unsigned integer."""
        result = ValueEncoder.encode_int(50000, size_bytes=2, signed=False)
        assert result == b"\xc3\x50"

    def test_encode_int_4_byte_signed(self) -> None:
        """Test encoding 4-byte signed integer."""
        result = ValueEncoder.encode_int(-50000, size_bytes=4, signed=True)
        assert len(result) == 4
        expected = struct.pack(">i", -50000)
        assert result == expected

    def test_encode_int_4_byte_unsigned(self) -> None:
        """Test encoding 4-byte unsigned integer."""
        result = ValueEncoder.encode_int(4000000000, size_bytes=4, signed=False)
        assert len(result) == 4

    def test_encode_int_8_byte_signed(self) -> None:
        """Test encoding 8-byte signed integer."""
        result = ValueEncoder.encode_int(
            9223372036854775807, size_bytes=8, signed=True
        )
        assert len(result) == 8

    def test_encode_int_8_byte_unsigned(self) -> None:
        """Test encoding 8-byte unsigned integer."""
        result = ValueEncoder.encode_int(
            18446744073709551615, size_bytes=8, signed=False
        )
        assert len(result) == 8

    def test_encode_int_negative(self) -> None:
        """Test encoding negative integer."""
        result = ValueEncoder.encode_int(-128, size_bytes=1, signed=True)
        assert result == b"\x80"

    def test_encode_int_zero(self) -> None:
        """Test encoding zero."""
        result = ValueEncoder.encode_int(0, size_bytes=4, signed=True)
        assert result == b"\x00\x00\x00\x00"

    def test_encode_int_invalid_size(self) -> None:
        """Test encoding with invalid size raises ValueError."""
        with pytest.raises(ValueError, match="Invalid size_bytes"):
            ValueEncoder.encode_int(42, size_bytes=3, signed=True)

    def test_encode_int_out_of_range(self) -> None:
        """Test encoding value out of range raises ValueError."""
        with pytest.raises(ValueError, match="out of range"):
            ValueEncoder.encode_int(256, size_bytes=1, signed=False)


class TestIntegerDecoding:
    """Test integer decoding."""

    def test_decode_int_1_byte_signed(self) -> None:
        """Test decoding 1-byte signed integer."""
        result = ValueEncoder.decode_int(b"\x7f", signed=True)
        assert result == 127

    def test_decode_int_1_byte_unsigned(self) -> None:
        """Test decoding 1-byte unsigned integer."""
        result = ValueEncoder.decode_int(b"\xc8", signed=False)
        assert result == 200

    def test_decode_int_2_byte_signed(self) -> None:
        """Test decoding 2-byte signed integer."""
        result = ValueEncoder.decode_int(b"\x03\xe8", signed=True)
        assert result == 1000

    def test_decode_int_2_byte_unsigned(self) -> None:
        """Test decoding 2-byte unsigned integer."""
        result = ValueEncoder.decode_int(b"\xc3\x50", signed=False)
        assert result == 50000

    def test_decode_int_4_byte_signed(self) -> None:
        """Test decoding 4-byte signed integer."""
        data = struct.pack(">i", -50000)
        result = ValueEncoder.decode_int(data, signed=True)
        assert result == -50000

    def test_decode_int_negative(self) -> None:
        """Test decoding negative integer."""
        result = ValueEncoder.decode_int(b"\x80", signed=True)
        assert result == -128

    def test_decode_int_invalid_length(self) -> None:
        """Test decoding with invalid length raises ValueError."""
        with pytest.raises(ValueError, match="Invalid data length"):
            ValueEncoder.decode_int(b"\x01\x02\x03", signed=True)

    def test_encode_decode_int_roundtrip(self) -> None:
        """Test integer encode-decode roundtrip."""
        original = 12345
        encoded = ValueEncoder.encode_int(original, size_bytes=4, signed=True)
        decoded = ValueEncoder.decode_int(encoded, signed=True)
        assert decoded == original


class TestBigEndianByteOrder:
    """Test that all encoding uses big-endian byte order."""

    def test_temperature_uses_big_endian(self) -> None:
        """Test temperature encoding uses big-endian order."""
        # 29.1°C = 291 = 0x0123
        result = ValueEncoder.encode_temperature(29.1, "temp")
        # Big-endian: most significant byte first
        assert result[0] == 0x01  # High byte
        assert result[1] == 0x23  # Low byte

    def test_integer_uses_big_endian(self) -> None:
        """Test integer encoding uses big-endian order."""
        # 1000 = 0x03E8
        result = ValueEncoder.encode_int(1000, size_bytes=2, signed=True)
        # Big-endian: most significant byte first
        assert result[0] == 0x03  # High byte
        assert result[1] == 0xE8  # Low byte
