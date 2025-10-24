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
from typing import Literal

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
            value = struct.unpack(">h", data)[0]  # Big-endian signed short
            return value / 10.0

        elif format_type == "temp_byte":
            # 1 byte, factor 0.5
            if len(data) != 1:
                raise ValueError(
                    f"Invalid data length for 'temp_byte' format: expected 1 byte, "
                    f"got {len(data)}"
                )
            value = struct.unpack("B", data)[0]
            return value / 2.0

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

        return struct.unpack(fmt, data)[0]
