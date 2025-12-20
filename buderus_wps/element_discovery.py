"""Element list discovery protocol for Buderus WPS heat pumps.

This module implements the CAN protocol for reading the parameter element list
from the heat pump at runtime. This is necessary because different firmware
versions may have different idx values for the same parameter names.

Protocol Reference: FHEM 26_KM273v018.pm lines 2052-2164

CAN Message Protocol:
- Request element count: R01FD7FE00 -> Response: T09FD7FE0 (count in bytes 0-3)
- Request element data: T01FD3FE08{offset:08X}{index:08X} -> Response: T09FDBFE0

Element data format per entry (18 bytes header + variable name):
- Bytes 0-1: idx (uint16, big-endian)
- Bytes 2-8: extid (7 bytes hex string)
- Bytes 9-12: max (int32, big-endian, signed)
- Bytes 13-16: min (int32, big-endian, signed)
- Byte 17: name_length
- Bytes 18+: name (ASCII string, name_length-1 bytes)
"""

import logging
import struct
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# PROTOCOL: CAN IDs for element list discovery
ELEMENT_COUNT_REQUEST_ID = 0x01FD7FE0  # R01FD7FE00 (RTR)
ELEMENT_COUNT_RESPONSE_ID = 0x09FD7FE0  # T09FD7FE0
ELEMENT_DATA_REQUEST_ID = 0x01FD3FE0  # T01FD3FE08...
ELEMENT_DATA_RESPONSE_ID = 0x09FDBFE0  # T09FDBFE0

# PROTOCOL: Element header size (before variable-length name)
ELEMENT_HEADER_SIZE = 18


@dataclass
class DiscoveredElement:
    """A parameter element discovered from the heat pump.

    Attributes:
        idx: Element index used to construct CAN IDs (0-4095)
        extid: External ID string (14 hex characters)
        text: Parameter name (e.g., 'XDHW_TIME')
        min_value: Minimum allowed value (signed)
        max_value: Maximum allowed value (signed)
    """

    idx: int
    extid: str
    text: str
    min_value: int
    max_value: int

    @property
    def can_id(self) -> int:
        """Calculate CAN ID for this element.

        PROTOCOL: CAN ID formula from FHEM line 2229:
        0x04003FE0 | (idx << 14)
        """
        return 0x04003FE0 | (self.idx << 14)


class ElementListParser:
    """Parser for element list discovery CAN responses.

    This parser handles the binary protocol for extracting parameter definitions
    from the heat pump's element list responses.
    """

    def parse_count_response(self, can_id: int, data: bytes) -> int:
        """Parse element count from T09FD7FE0 response.

        Args:
            can_id: The CAN arbitration ID of the response
            data: The CAN message data bytes (4+ bytes)

        Returns:
            The total number of elements available

        Raises:
            ValueError: If CAN ID doesn't match or data is too short
        """
        if can_id != ELEMENT_COUNT_RESPONSE_ID:
            raise ValueError(
                f"Unexpected CAN ID 0x{can_id:08X}, "
                f"expected 0x{ELEMENT_COUNT_RESPONSE_ID:08X}"
            )

        if len(data) < 4:
            raise ValueError(
                f"Insufficient data: got {len(data)} bytes, need at least 4"
            )

        # PROTOCOL: Count is in first 4 bytes, big-endian unsigned
        # Actually FHEM uses: ($value1 >> 24) which suggests only first byte
        # But full 4-byte count is safer for large element lists
        count: int = struct.unpack(">I", data[:4])[0]
        return count

    def parse_data_chunk(self, data: bytes) -> List[DiscoveredElement]:
        """Parse element definitions from T09FDBFE0 response data.

        The data contains concatenated element entries. Each entry has:
        - 18-byte header (idx, extid, max, min, name_length)
        - Variable-length name string

        Args:
            data: Raw element data bytes (accumulated from multiple CAN frames)

        Returns:
            List of parsed DiscoveredElement instances
        """
        elements: List[DiscoveredElement] = []
        offset = 0

        while offset + ELEMENT_HEADER_SIZE <= len(data):
            try:
                element, bytes_consumed = self._parse_single_element(data, offset)
                if element is not None:
                    elements.append(element)
                offset += bytes_consumed
            except Exception as e:
                logger.warning(f"Failed to parse element at offset {offset}: {e}")
                # Try to skip to next element by scanning for valid idx
                offset += 1

        return elements

    def _parse_single_element(
        self, data: bytes, offset: int
    ) -> Tuple[Optional[DiscoveredElement], int]:
        """Parse a single element from data at given offset.

        Args:
            data: The full data buffer
            offset: Starting offset for this element

        Returns:
            Tuple of (element or None if invalid, bytes consumed)
        """
        # Check minimum header size
        if offset + ELEMENT_HEADER_SIZE > len(data):
            return None, len(data) - offset

        # PROTOCOL: Parse 18-byte header
        # Bytes 0-1: idx (uint16 big-endian)
        idx = struct.unpack(">H", data[offset : offset + 2])[0]

        # Bytes 2-8: extid (7 bytes as hex string)
        extid_bytes = data[offset + 2 : offset + 9]
        extid = extid_bytes.hex().upper()

        # Bytes 9-12: max (int32 big-endian signed)
        max_value = struct.unpack(">i", data[offset + 9 : offset + 13])[0]

        # Bytes 13-16: min (int32 big-endian signed)
        min_value = struct.unpack(">i", data[offset + 13 : offset + 17])[0]

        # Byte 17: name_length (includes original null terminator)
        name_length = data[offset + 17]

        if name_length == 0:
            logger.warning(f"Element at offset {offset} has zero name length, skipping")
            return None, ELEMENT_HEADER_SIZE

        # Actual name length is name_length - 1 (excluding null terminator)
        actual_name_len = name_length - 1

        # Check if we have enough data for the name
        if offset + ELEMENT_HEADER_SIZE + actual_name_len > len(data):
            logger.warning(
                f"Element at offset {offset} has name_length={name_length} but "
                f"only {len(data) - offset - ELEMENT_HEADER_SIZE} bytes remain"
            )
            return None, len(data) - offset

        # Parse name
        name_bytes = data[
            offset
            + ELEMENT_HEADER_SIZE : offset
            + ELEMENT_HEADER_SIZE
            + actual_name_len
        ]
        try:
            text = name_bytes.decode("ascii")
        except UnicodeDecodeError:
            # Try with replacement characters for non-ASCII
            text = name_bytes.decode("ascii", errors="replace")
            if text != name_bytes.decode("ascii", errors="ignore"):
                logger.warning(
                    f"Element at offset {offset} has non-ASCII name, skipping"
                )
                return None, ELEMENT_HEADER_SIZE + actual_name_len

        # Total bytes consumed
        total_bytes = ELEMENT_HEADER_SIZE + actual_name_len

        element = DiscoveredElement(
            idx=idx,
            extid=extid,
            text=text,
            min_value=min_value,
            max_value=max_value,
        )

        return element, total_bytes
