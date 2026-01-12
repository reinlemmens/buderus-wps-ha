"""
Value encoding and decoding utilities for Buderus heat pump protocol.

This module provides static methods for encoding and decoding multi-byte
values according to Buderus protocol specifications. All multi-byte values
use big-endian byte order per CAN standard.

Example:
    >>> # Encode temperature (29.1°C)
    >>> data = ValueEncoder.encode_temperature(29.1, 'temp')
    >>> data
    b'\\x01\\x23'

    >>> # Decode temperature
    >>> temp = ValueEncoder.decode_temperature(b'\\x01\\x23', 'temp')
    >>> temp
    29.1
"""

import struct
from typing import Any, Literal, Optional

from .formats import (
    decode_select_value,
    encode_select_value,
    get_format_factor,
    is_dead_value,
)

# Type aliases for format types
TemperatureFormat = Literal["temp", "temp_byte", "temp_uint"]


class ValueEncoder:
    """
    Static utility class for encoding/decoding multi-byte values.

    All methods are static. Byte order is big-endian (network byte order)
    for all multi-byte values per CAN specification.
    """

    @staticmethod
    def encode_temperature(
        temp_celsius: float, format_type: TemperatureFormat = "temp"
    ) -> bytes:
        """
        Encode temperature value to bytes.

        Buderus uses three temperature encoding formats:
        - 'temp': 2 bytes, factor 0.1, range -3276.8 to +3276.7°C
        - 'temp_byte': 1 byte, factor 0.5, range 0.0 to 127.5°C
        - 'temp_uint': 1 byte, factor 1.0, range 0 to 255°C

        Args:
            temp_celsius: Temperature in degrees Celsius
            format_type: Encoding format ('temp', 'temp_byte', or 'temp_uint')

        Returns:
            Encoded temperature (1 or 2 bytes depending on format)

        Raises:
            ValueError: If format_type is not recognized or temperature
                       is out of range for the specified format

        Examples:
            >>> ValueEncoder.encode_temperature(29.1, 'temp')
            b'\\x01\\x23'

            >>> ValueEncoder.encode_temperature(22.5, 'temp_byte')
            b'-'

            >>> ValueEncoder.encode_temperature(60.0, 'temp_uint')
            b'<'
        """
        if format_type == "temp":
            # 2 bytes, signed, factor 0.1
            value = int(temp_celsius * 10)
            if not -32768 <= value <= 32767:
                raise ValueError(
                    f"Temperature {temp_celsius}°C out of range for 'temp' format "
                    f"(-3276.8°C to +3276.7°C)"
                )
            return struct.pack(">h", value)  # Big-endian signed short

        elif format_type == "temp_byte":
            # 1 byte, factor 0.5
            value = int(temp_celsius * 2)
            if not 0 <= value <= 255:
                raise ValueError(
                    f"Temperature {temp_celsius}°C out of range for 'temp_byte' "
                    f"format (0.0°C to 127.5°C)"
                )
            return struct.pack("B", value)  # Unsigned byte

        elif format_type == "temp_uint":
            # 1 byte, no factor
            value = int(temp_celsius)
            if not 0 <= value <= 255:
                raise ValueError(
                    f"Temperature {temp_celsius}°C out of range for 'temp_uint' "
                    f"format (0°C to 255°C)"
                )
            return struct.pack("B", value)  # Unsigned byte

        else:
            raise ValueError(f"Unknown temperature format: {format_type}")

    @staticmethod
    def decode_temperature(
        data: bytes, format_type: TemperatureFormat = "temp"
    ) -> float:
        """
        Decode temperature value from bytes.

        Args:
            data: Encoded temperature data (1 or 2 bytes depending on format)
            format_type: Encoding format (must match encoding)

        Returns:
            Temperature in degrees Celsius

        Raises:
            ValueError: If format_type is not recognized or data length
                       doesn't match format requirements
            struct.error: If data cannot be unpacked (malformed)

        Examples:
            >>> ValueEncoder.decode_temperature(b'\\x01\\x23', 'temp')
            29.1

            >>> ValueEncoder.decode_temperature(b'-', 'temp_byte')
            22.5

            >>> ValueEncoder.decode_temperature(b'<', 'temp_uint')
            60.0
        """
        if format_type == "temp":
            # 2 bytes, signed, factor 0.1
            if len(data) != 2:
                raise ValueError(
                    f"Invalid data length for 'temp' format: expected 2 bytes, "
                    f"got {len(data)}"
                )
            value: int = struct.unpack(">h", data)[0]  # Big-endian signed short
            return value / 10.0

        elif format_type == "temp_byte":
            # 1 byte, factor 0.5
            if len(data) != 1:
                raise ValueError(
                    f"Invalid data length for 'temp_byte' format: expected 1 byte, "
                    f"got {len(data)}"
                )
            byte_value: int = struct.unpack("B", data)[0]
            return byte_value / 2.0

        elif format_type == "temp_uint":
            # 1 byte, no factor
            if len(data) != 1:
                raise ValueError(
                    f"Invalid data length for 'temp_uint' format: expected 1 byte, "
                    f"got {len(data)}"
                )
            value = struct.unpack("B", data)[0]
            return float(value)

        else:
            raise ValueError(f"Unknown temperature format: {format_type}")

    @staticmethod
    def encode_int(value: int, size_bytes: int = 4, signed: bool = True) -> bytes:
        """
        Encode integer value to bytes (big-endian).

        Args:
            value: Integer value to encode
            size_bytes: Number of bytes for encoding (1, 2, 4, or 8)
            signed: True for signed integer, False for unsigned

        Returns:
            Encoded integer in big-endian byte order

        Raises:
            ValueError: If size_bytes is not 1, 2, 4, or 8, or if value
                       is out of range for specified size/signed combination
            struct.error: If value cannot be packed with specified format

        Examples:
            >>> ValueEncoder.encode_int(1000, size_bytes=2, signed=True)
            b'\\x03\\xe8'

            >>> ValueEncoder.encode_int(200, size_bytes=1, signed=False)
            b'\\xc8'
        """
        format_codes = {
            (1, True): ">b",
            (1, False): ">B",
            (2, True): ">h",
            (2, False): ">H",
            (4, True): ">i",
            (4, False): ">I",
            (8, True): ">q",
            (8, False): ">Q",
        }

        fmt = format_codes.get((size_bytes, signed))
        if not fmt:
            raise ValueError(
                f"Invalid size_bytes/signed combination: {size_bytes}/{signed}. "
                f"size_bytes must be 1, 2, 4, or 8"
            )

        try:
            return struct.pack(fmt, value)
        except struct.error as e:
            raise ValueError(
                f"Value {value} out of range for {size_bytes}-byte "
                f"{'signed' if signed else 'unsigned'} integer"
            ) from e

    @staticmethod
    def decode_int(data: bytes, signed: bool = True) -> int:
        """
        Decode integer value from bytes.

        Size is automatically determined from data length.

        Args:
            data: Encoded integer data (1, 2, 4, or 8 bytes)
            signed: True for signed integer, False for unsigned

        Returns:
            Decoded integer value

        Raises:
            ValueError: If data length is not 1, 2, 4, or 8 bytes
            struct.error: If data cannot be unpacked

        Examples:
            >>> ValueEncoder.decode_int(b'\\x03\\xe8', signed=True)
            1000

            >>> ValueEncoder.decode_int(b'\\xc8', signed=False)
            200
        """
        size_bytes = len(data)
        format_codes = {
            (1, True): ">b",
            (1, False): ">B",
            (2, True): ">h",
            (2, False): ">H",
            (4, True): ">i",
            (4, False): ">I",
            (8, True): ">q",
            (8, False): ">Q",
        }

        fmt = format_codes.get((size_bytes, signed))
        if not fmt:
            raise ValueError(
                f"Invalid data length: {size_bytes} bytes. "
                f"Must be 1, 2, 4, or 8 bytes"
            )

        result: int = struct.unpack(fmt, data)[0]
        return result

    # =========================================================================
    # FHEM-Compatible Format Decoding/Encoding
    # PROTOCOL: Matches %KM273_format from fhem/26_KM273v018.pm:2011-2025
    # =========================================================================

    @staticmethod
    def decode_by_format(
        data: bytes, format_type: str, min_val: int = 0
    ) -> Optional[Any]:
        """Decode raw bytes using FHEM format specification.

        # PROTOCOL: Format decoding from fhem/26_KM273v018.pm:2714-2740

        This is the main entry point for decoding parameter values from the
        heat pump. It handles all FHEM format types and DEAD sensor detection.

        Args:
            data: Raw bytes from CAN response (typically 1-4 bytes)
            format_type: FHEM format name ('tem', 'pw2', 'int', etc.)
            min_val: Minimum value from parameter definition (for signedness)

        Returns:
            Decoded value (float, int, or str depending on format)
            Returns None if DEAD sensor value detected

        Example:
            >>> ValueEncoder.decode_by_format(b'\\x02\\x12', 'tem')
            53.0
            >>> ValueEncoder.decode_by_format(b'\\xDE\\xAD', 'tem')
            None  # DEAD sensor
        """
        if not data:
            return None

        # PROTOCOL: Check for DEAD sensor value first (0xDEAD = -8531 as signed 16-bit)
        # DEAD value is only valid for 2-byte temperature sensors, always check as signed
        if len(data) == 2:
            signed_value = struct.unpack(">h", data)[0]
            if is_dead_value(signed_value):
                return None

        # Determine signedness from min value (FHEM convention)
        signed = min_val < 0

        # Get raw integer value
        if len(data) == 1:
            raw_value = struct.unpack("b" if signed else "B", data)[0]
        elif len(data) == 2:
            raw_value = struct.unpack(">h" if signed else ">H", data)[0]
        elif len(data) == 4:
            raw_value = struct.unpack(">i" if signed else ">I", data)[0]
        else:
            # For other lengths, use big-endian conversion
            raw_value = int.from_bytes(data, "big", signed=signed)

        # Handle format-specific decoding
        if format_type == "tem":
            return ValueEncoder.decode_tem(raw_value)
        elif format_type in ("pw2", "pw3"):
            return ValueEncoder.decode_power(raw_value, format_type)
        elif format_type in ("hm1", "hm2"):
            return ValueEncoder.decode_time(raw_value, format_type)
        elif format_type == "t15":
            return ValueEncoder.decode_t15(raw_value)
        elif format_type in ("sw1", "sw2"):
            return ValueEncoder.decode_timer_switch(raw_value, format_type)
        elif format_type in ("rp1", "rp2", "dp1", "dp2"):
            return decode_select_value(raw_value, format_type)
        else:
            # 'int' or unknown format - return raw value
            return raw_value

    @staticmethod
    def encode_by_format(
        value: Any, format_type: str, size_bytes: int = 2, min_val: int = 0
    ) -> bytes:
        """Encode a human-readable value to raw bytes using FHEM format.

        # PROTOCOL: Format encoding from fhem/26_KM273v018.pm:2728-2729
        # FHEM: $value1 = int($value / $factor + 0.5)

        This is the main entry point for encoding parameter values to send
        to the heat pump. It converts human-readable values to raw bytes.

        Args:
            value: Human-readable value (e.g., 53.0 for temperature)
            format_type: FHEM format name ('tem', 'pw2', 'int', etc.)
            size_bytes: Number of bytes for output (1, 2, or 4)
            min_val: Minimum value from parameter definition (for signedness)

        Returns:
            Encoded bytes in big-endian order

        Example:
            >>> ValueEncoder.encode_by_format(53.0, 'tem')
            b'\\x02\\x12'  # 530 = 53.0 / 0.1
        """
        signed = min_val < 0

        # Handle format-specific encoding
        if format_type == "tem":
            raw_value = ValueEncoder.encode_tem(value)
        elif format_type in ("pw2", "pw3"):
            raw_value = ValueEncoder.encode_power(value, format_type)
        elif format_type in ("hm1", "hm2"):
            raw_value = ValueEncoder.encode_time(value, format_type)
        elif format_type == "t15":
            raw_value = ValueEncoder.encode_t15(value)
        elif format_type in ("sw1", "sw2"):
            raw_value = ValueEncoder.encode_timer_switch(value, format_type)
        elif format_type in ("rp1", "rp2", "dp1", "dp2"):
            raw_value = encode_select_value(str(value), format_type)
        else:
            # 'int' or unknown - value is already raw
            raw_value = int(value)

        # Pack to bytes
        return ValueEncoder.encode_int(raw_value, size_bytes=size_bytes, signed=signed)

    # =========================================================================
    # Temperature Format (tem)
    # PROTOCOL: factor=0.1, unit=°C from fhem/26_KM273v018.pm:2015
    # =========================================================================

    @staticmethod
    def decode_tem(raw_value: int) -> float:
        """Decode temperature from raw value (factor 0.1).

        # PROTOCOL: 'tem' format with factor=0.1 from fhem line 2015

        Args:
            raw_value: Raw integer from CAN (e.g., 530)

        Returns:
            Temperature in degrees Celsius (e.g., 53.0)

        Example:
            >>> ValueEncoder.decode_tem(530)
            53.0
            >>> ValueEncoder.decode_tem(-100)
            -10.0
        """
        return raw_value * 0.1

    @staticmethod
    def encode_tem(temp_celsius: float) -> int:
        """Encode temperature to raw value (factor 0.1).

        # PROTOCOL: FHEM line 2729: $value1 = int($value / $factor + 0.5)

        Args:
            temp_celsius: Temperature in degrees Celsius (e.g., 53.0)

        Returns:
            Raw integer for CAN (e.g., 530)

        Example:
            >>> ValueEncoder.encode_tem(53.0)
            530
            >>> ValueEncoder.encode_tem(29.15)
            292  # Rounded from 291.5
        """
        return int(temp_celsius / 0.1 + 0.5)

    # =========================================================================
    # Power Formats (pw2, pw3)
    # PROTOCOL: pw2=0.01kW, pw3=0.001kW from fhem/26_KM273v018.pm:2016-2017
    # =========================================================================

    @staticmethod
    def decode_power(raw_value: int, format_type: str = "pw2") -> float:
        """Decode power from raw value.

        # PROTOCOL: 'pw2' factor=0.01, 'pw3' factor=0.001 from fhem lines 2016-2017

        Args:
            raw_value: Raw integer from CAN
            format_type: 'pw2' (factor 0.01) or 'pw3' (factor 0.001)

        Returns:
            Power in kW

        Example:
            >>> ValueEncoder.decode_power(1234, 'pw2')
            12.34
            >>> ValueEncoder.decode_power(12345, 'pw3')
            12.345
        """
        factor = get_format_factor(format_type)
        return raw_value * factor

    @staticmethod
    def encode_power(power_kw: float, format_type: str = "pw2") -> int:
        """Encode power to raw value.

        Args:
            power_kw: Power in kW
            format_type: 'pw2' (factor 0.01) or 'pw3' (factor 0.001)

        Returns:
            Raw integer for CAN

        Example:
            >>> ValueEncoder.encode_power(12.34, 'pw2')
            1234
            >>> ValueEncoder.encode_power(12.345, 'pw3')
            12345
        """
        factor = get_format_factor(format_type)
        return int(power_kw / factor + 0.5)

    # =========================================================================
    # Time Formats (hm1, hm2)
    # PROTOCOL: hm1=1s, hm2=10s intervals from fhem/26_KM273v018.pm:2013-2014
    # =========================================================================

    @staticmethod
    def decode_time(raw_value: int, format_type: str = "hm1") -> str:
        """Decode time value to HH:MM string.

        # PROTOCOL: 'hm1' in seconds, 'hm2' in 10-second intervals

        Args:
            raw_value: Raw integer from CAN (seconds or 10s intervals)
            format_type: 'hm1' (seconds) or 'hm2' (10-second intervals)

        Returns:
            Time as "HH:MM" string

        Example:
            >>> ValueEncoder.decode_time(3661, 'hm1')  # 1 hour 1 minute 1 second
            '1:01'
            >>> ValueEncoder.decode_time(120, 'hm2')   # 1200 seconds = 20 minutes
            '0:20'
        """
        factor = get_format_factor(format_type)
        total_seconds = raw_value * factor
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}:{minutes:02d}"

    @staticmethod
    def encode_time(time_str: str, format_type: str = "hm1") -> int:
        """Encode time string to raw value.

        Args:
            time_str: Time as "HH:MM" or "H:MM" string
            format_type: 'hm1' (seconds) or 'hm2' (10-second intervals)

        Returns:
            Raw integer for CAN

        Example:
            >>> ValueEncoder.encode_time('1:01', 'hm1')
            3660  # 1 hour 1 minute in seconds (rounded to minutes)
            >>> ValueEncoder.encode_time('0:20', 'hm2')
            120   # 20 minutes = 1200 seconds / 10
        """
        parts = time_str.split(":")
        if len(parts) == 2:
            hours = int(parts[0])
            minutes = int(parts[1])
        elif len(parts) == 1:
            hours = 0
            minutes = int(parts[0])
        else:
            raise ValueError(f"Invalid time format: {time_str}")

        total_seconds = hours * 3600 + minutes * 60
        factor = get_format_factor(format_type)
        return int(total_seconds / factor + 0.5)

    # =========================================================================
    # 15-Minute Interval Format (t15)
    # PROTOCOL: bits 0-1=quarter, bits 2+=hour from fhem/26_KM273v018.pm:2012
    # =========================================================================

    @staticmethod
    def decode_t15(raw_value: int) -> str:
        """Decode 15-minute interval to HH:MM string.

        # PROTOCOL: 't15' format - bits 0-1 = quarter (0-3), bits 2+ = hour

        Args:
            raw_value: Raw integer (bits 0-1=quarter, bits 2+=hour)

        Returns:
            Time as "HH:MM" string

        Example:
            >>> ValueEncoder.decode_t15(28)  # hour=7 (28>>2), quarter=0 (28&3)
            '07:00'
            >>> ValueEncoder.decode_t15(29)  # hour=7, quarter=1
            '07:15'
            >>> ValueEncoder.decode_t15(30)  # hour=7, quarter=2
            '07:30'
        """
        quarter = raw_value & 0x03  # bits 0-1
        hour = raw_value >> 2  # bits 2+
        minutes = quarter * 15
        return f"{hour:02d}:{minutes:02d}"

    @staticmethod
    def encode_t15(time_str: str) -> int:
        """Encode HH:MM string to 15-minute interval.

        Args:
            time_str: Time as "HH:MM" string (minutes rounded to 15-min intervals)

        Returns:
            Raw integer (bits 0-1=quarter, bits 2+=hour)

        Example:
            >>> ValueEncoder.encode_t15('07:00')
            28
            >>> ValueEncoder.encode_t15('07:15')
            29
            >>> ValueEncoder.encode_t15('07:30')
            30
        """
        parts = time_str.split(":")
        hour = int(parts[0])
        minutes = int(parts[1]) if len(parts) > 1 else 0
        quarter = (minutes + 7) // 15  # Round to nearest 15-min interval
        if quarter > 3:
            quarter = 3
        return (hour << 2) | quarter

    # =========================================================================
    # Timer Switch Formats (sw1, sw2)
    # PROTOCOL: Bit fields for timer programming from fhem/26_KM273v018.pm
    # =========================================================================

    @staticmethod
    def decode_timer_switch(raw_value: int, format_type: str = "sw1") -> str:
        """Decode timer switch bit field to string representation.

        # PROTOCOL: Timer switch formats encode on/off times as bit fields

        Args:
            raw_value: Raw integer bit field
            format_type: 'sw1' or 'sw2'

        Returns:
            String representation of timer bits

        Example:
            >>> ValueEncoder.decode_timer_switch(0xFF, 'sw1')
            '11111111'  # All bits set
        """
        # Convert to binary string representation
        # The actual interpretation depends on the specific parameter
        return format(raw_value, "08b")

    @staticmethod
    def encode_timer_switch(value: str, format_type: str = "sw1") -> int:
        """Encode timer switch string to bit field.

        Args:
            value: Binary string or integer value
            format_type: 'sw1' or 'sw2'

        Returns:
            Raw integer bit field

        Example:
            >>> ValueEncoder.encode_timer_switch('11111111', 'sw1')
            255
            >>> ValueEncoder.encode_timer_switch('128', 'sw1')
            128
        """
        # Try parsing as binary string first
        if all(c in "01" for c in str(value)):
            return int(str(value), 2)
        # Otherwise parse as integer
        return int(value)
