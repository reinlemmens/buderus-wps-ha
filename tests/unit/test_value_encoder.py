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
        result = ValueEncoder.encode_int(9223372036854775807, size_bytes=8, signed=True)
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


# =========================================================================
# FHEM Format Encoding/Decoding Tests
# PROTOCOL: Tests for all formats from fhem/26_KM273v018.pm
# =========================================================================


class TestFHEMTemperatureFormat:
    """Test FHEM 'tem' format (temperature with factor 0.1)."""

    def test_decode_tem_positive(self) -> None:
        """Test decoding positive temperature."""
        assert ValueEncoder.decode_tem(530) == 53.0
        assert ValueEncoder.decode_tem(291) == 29.1

    def test_decode_tem_negative(self) -> None:
        """Test decoding negative temperature."""
        assert ValueEncoder.decode_tem(-100) == -10.0
        assert ValueEncoder.decode_tem(-55) == -5.5

    def test_decode_tem_zero(self) -> None:
        """Test decoding zero."""
        assert ValueEncoder.decode_tem(0) == 0.0

    def test_encode_tem_positive(self) -> None:
        """Test encoding positive temperature."""
        assert ValueEncoder.encode_tem(53.0) == 530
        assert ValueEncoder.encode_tem(29.1) == 291

    def test_encode_tem_rounding(self) -> None:
        """Test encoding with rounding (FHEM uses int(value/factor + 0.5))."""
        # Note: Python float precision can cause 29.15/0.1 = 291.499... not 291.5
        # The +0.5 rounding may not bump to 292 due to float representation
        assert ValueEncoder.encode_tem(29.16) == 292  # Clearly rounds up
        assert ValueEncoder.encode_tem(29.04) == 290  # Clearly rounds down

    def test_encode_tem_negative(self) -> None:
        """Test encoding negative temperature.

        Note: For negative values, FHEM's int(val/0.1 + 0.5) behavior:
        -10.0 / 0.1 + 0.5 = -99.5, int(-99.5) = -99 (Python truncates toward zero)
        This differs from round() which would give -100.
        """
        # -10.0°C encodes to raw -99 with current FHEM-style rounding
        assert ValueEncoder.encode_tem(-10.0) == -99

    def test_encode_decode_tem_roundtrip(self) -> None:
        """Test encode-decode roundtrip for exact tenths."""
        # Use values that are exact tenths to avoid rounding issues
        for temp in [0.0, 25.5, 53.0, 100.0]:
            raw = ValueEncoder.encode_tem(temp)
            decoded = ValueEncoder.decode_tem(raw)
            assert decoded == temp


class TestFHEMPowerFormats:
    """Test FHEM power formats (pw2, pw3)."""

    def test_decode_power_pw2(self) -> None:
        """Test decoding pw2 format (factor 0.01)."""
        assert ValueEncoder.decode_power(1234, "pw2") == 12.34
        assert ValueEncoder.decode_power(0, "pw2") == 0.0

    def test_decode_power_pw3(self) -> None:
        """Test decoding pw3 format (factor 0.001)."""
        assert ValueEncoder.decode_power(12345, "pw3") == 12.345
        assert ValueEncoder.decode_power(0, "pw3") == 0.0

    def test_encode_power_pw2(self) -> None:
        """Test encoding pw2 format."""
        assert ValueEncoder.encode_power(12.34, "pw2") == 1234

    def test_encode_power_pw3(self) -> None:
        """Test encoding pw3 format."""
        assert ValueEncoder.encode_power(12.345, "pw3") == 12345

    def test_encode_decode_power_roundtrip(self) -> None:
        """Test power encode-decode roundtrip."""
        for power in [0.0, 5.55, 12.34]:
            raw = ValueEncoder.encode_power(power, "pw2")
            decoded = ValueEncoder.decode_power(raw, "pw2")
            assert decoded == power


class TestFHEMTimeFormats:
    """Test FHEM time formats (hm1, hm2)."""

    def test_decode_time_hm1(self) -> None:
        """Test decoding hm1 format (seconds)."""
        # 1 hour, 1 minute = 3660 seconds
        assert ValueEncoder.decode_time(3660, "hm1") == "1:01"
        assert ValueEncoder.decode_time(0, "hm1") == "0:00"
        assert ValueEncoder.decode_time(7200, "hm1") == "2:00"

    def test_decode_time_hm2(self) -> None:
        """Test decoding hm2 format (10-second intervals)."""
        # 120 * 10 = 1200 seconds = 20 minutes
        assert ValueEncoder.decode_time(120, "hm2") == "0:20"
        assert ValueEncoder.decode_time(0, "hm2") == "0:00"

    def test_encode_time_hm1(self) -> None:
        """Test encoding hm1 format."""
        assert ValueEncoder.encode_time("1:01", "hm1") == 3660
        assert ValueEncoder.encode_time("2:00", "hm1") == 7200

    def test_encode_time_hm2(self) -> None:
        """Test encoding hm2 format."""
        assert ValueEncoder.encode_time("0:20", "hm2") == 120

    def test_encode_decode_time_roundtrip(self) -> None:
        """Test time encode-decode roundtrip."""
        for time_str in ["0:00", "1:30", "12:45"]:
            raw = ValueEncoder.encode_time(time_str, "hm1")
            decoded = ValueEncoder.decode_time(raw, "hm1")
            assert decoded == time_str


class TestFHEMT15Format:
    """Test FHEM t15 format (15-minute intervals)."""

    def test_decode_t15(self) -> None:
        """Test decoding t15 format (bits 0-1=quarter, bits 2+=hour)."""
        # 28 = (7 << 2) | 0 = 07:00
        assert ValueEncoder.decode_t15(28) == "07:00"
        # 29 = (7 << 2) | 1 = 07:15
        assert ValueEncoder.decode_t15(29) == "07:15"
        # 30 = (7 << 2) | 2 = 07:30
        assert ValueEncoder.decode_t15(30) == "07:30"
        # 31 = (7 << 2) | 3 = 07:45
        assert ValueEncoder.decode_t15(31) == "07:45"
        # 32 = (8 << 2) | 0 = 08:00
        assert ValueEncoder.decode_t15(32) == "08:00"

    def test_encode_t15(self) -> None:
        """Test encoding t15 format."""
        assert ValueEncoder.encode_t15("07:00") == 28
        assert ValueEncoder.encode_t15("07:15") == 29
        assert ValueEncoder.encode_t15("07:30") == 30
        assert ValueEncoder.encode_t15("07:45") == 31
        assert ValueEncoder.encode_t15("08:00") == 32

    def test_encode_decode_t15_roundtrip(self) -> None:
        """Test t15 encode-decode roundtrip."""
        for time_str in ["00:00", "06:15", "12:30", "23:45"]:
            raw = ValueEncoder.encode_t15(time_str)
            decoded = ValueEncoder.decode_t15(raw)
            assert decoded == time_str


class TestFHEMTimerSwitchFormats:
    """Test FHEM timer switch formats (sw1, sw2)."""

    def test_decode_timer_switch(self) -> None:
        """Test decoding timer switch bit field."""
        assert ValueEncoder.decode_timer_switch(0xFF, "sw1") == "11111111"
        assert ValueEncoder.decode_timer_switch(0x00, "sw1") == "00000000"
        assert ValueEncoder.decode_timer_switch(0xAA, "sw1") == "10101010"

    def test_encode_timer_switch_binary(self) -> None:
        """Test encoding timer switch from binary string."""
        assert ValueEncoder.encode_timer_switch("11111111", "sw1") == 255
        assert ValueEncoder.encode_timer_switch("00000000", "sw1") == 0
        assert ValueEncoder.encode_timer_switch("10101010", "sw1") == 170

    def test_encode_timer_switch_integer(self) -> None:
        """Test encoding timer switch from integer string."""
        assert ValueEncoder.encode_timer_switch("255", "sw1") == 255
        assert ValueEncoder.encode_timer_switch("128", "sw1") == 128


class TestFHEMDecodeByFormat:
    """Test unified decode_by_format method."""

    def test_decode_tem_format(self) -> None:
        """Test decoding 'tem' format."""
        data = struct.pack(">h", 530)  # 53.0°C
        result = ValueEncoder.decode_by_format(data, "tem")
        assert result == 53.0

    def test_decode_tem_negative(self) -> None:
        """Test decoding negative temperature."""
        data = struct.pack(">h", -100)  # -10.0°C
        result = ValueEncoder.decode_by_format(data, "tem", min_val=-500)
        assert result == -10.0

    def test_decode_pw2_format(self) -> None:
        """Test decoding 'pw2' format."""
        data = struct.pack(">H", 1234)  # 12.34 kW
        result = ValueEncoder.decode_by_format(data, "pw2")
        assert result == 12.34

    def test_decode_int_format(self) -> None:
        """Test decoding 'int' format (no factor)."""
        data = struct.pack(">H", 42)
        result = ValueEncoder.decode_by_format(data, "int")
        assert result == 42

    def test_decode_dead_value(self) -> None:
        """Test decoding DEAD sensor value returns None."""
        # DEAD = 0xDEAD = -8531 as signed 16-bit
        data = struct.pack(">h", -8531)
        result = ValueEncoder.decode_by_format(data, "tem")
        assert result is None

    def test_decode_empty_data(self) -> None:
        """Test decoding empty data returns None."""
        result = ValueEncoder.decode_by_format(b"", "tem")
        assert result is None


class TestFHEMEncodeByFormat:
    """Test unified encode_by_format method."""

    def test_encode_tem_format(self) -> None:
        """Test encoding 'tem' format (human-readable to raw)."""
        # 53.0°C should encode to 530 (raw tenths)
        result = ValueEncoder.encode_by_format(53.0, "tem")
        expected = struct.pack(">h", 530)
        assert result == expected

    def test_encode_int_format(self) -> None:
        """Test encoding 'int' format (no factor)."""
        result = ValueEncoder.encode_by_format(42, "int")
        expected = struct.pack(">h", 42)
        assert result == expected

    def test_encode_pw2_format(self) -> None:
        """Test encoding 'pw2' format."""
        # 12.34 kW should encode to 1234 (raw hundredths)
        result = ValueEncoder.encode_by_format(12.34, "pw2")
        expected = struct.pack(">h", 1234)
        assert result == expected

    def test_encode_decode_roundtrip_tem(self) -> None:
        """Test encode-decode roundtrip for temperature."""
        original = 53.0
        encoded = ValueEncoder.encode_by_format(original, "tem")
        decoded = ValueEncoder.decode_by_format(encoded, "tem")
        assert decoded == original

    def test_encode_xdhw_time_int_format(self) -> None:
        """Test encoding XDHW_TIME (int format, range 0-48 hours).

        This was a bug - XDHW_TIME write failed because Python
        expected raw values but FHEM accepts human-readable.
        """
        # XDHW_TIME has format='int', so factor=1 (no scaling)
        # User enters 24 (hours), should encode to 24
        result = ValueEncoder.encode_by_format(24, "int")
        expected = struct.pack(">h", 24)
        assert result == expected


class TestFHEMFormatsModule:
    """Test formats.py helper functions."""

    def test_get_format_factor(self) -> None:
        """Test get_format_factor returns correct values."""
        from buderus_wps.formats import get_format_factor

        assert get_format_factor("tem") == 0.1
        assert get_format_factor("pw2") == 0.01
        assert get_format_factor("pw3") == 0.001
        assert get_format_factor("int") == 1
        assert get_format_factor("unknown") == 1  # Default

    def test_get_format_unit(self) -> None:
        """Test get_format_unit returns correct values."""
        from buderus_wps.formats import get_format_unit

        assert get_format_unit("tem") == "°C"
        assert get_format_unit("pw2") == "kW"
        assert get_format_unit("int") == ""

    def test_is_dead_value(self) -> None:
        """Test is_dead_value detection."""
        from buderus_wps.formats import DEAD_VALUE, is_dead_value

        assert is_dead_value(DEAD_VALUE) is True
        assert is_dead_value(-8531) is True
        assert is_dead_value(0) is False
        assert is_dead_value(530) is False

    def test_decode_select_value(self) -> None:
        """Test decode_select_value for selector formats."""
        from buderus_wps.formats import decode_select_value

        # rp1 format: room program selectors
        assert decode_select_value(0, "rp1") == "0:HP_Optimized"
        assert decode_select_value(1, "rp1") == "1:Program_1"

        # dp2 format: DHW program selectors
        assert decode_select_value(0, "dp2") == "0:Automatic"
        assert decode_select_value(1, "dp2") == "1:Always_On"

        # Unknown value returns raw string
        assert decode_select_value(99, "rp1") == "99"

    def test_encode_select_value(self) -> None:
        """Test encode_select_value for selector formats."""
        from buderus_wps.formats import encode_select_value

        # Numeric string
        assert encode_select_value("0", "rp1") == 0
        assert encode_select_value("1", "dp2") == 1

        # Full selector string
        assert encode_select_value("0:Automatic", "dp2") == 0

        # Search by partial match
        assert encode_select_value("HP_Optimized", "rp1") == 0
