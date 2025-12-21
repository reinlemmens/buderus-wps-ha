"""Element list discovery protocol for Buderus WPS heat pumps.

This module implements the CAN protocol for reading the parameter element list
from the heat pump at runtime. This is necessary because different firmware
versions may have different idx values for the same parameter names.

Protocol Reference: FHEM 26_KM273v018.pm lines 2052-2164

CAN Message Protocol:
- Request element count: R01FD7FE00 -> Response: T09FD7FE0 (count in bytes 0-3)
- Request element data: T01FD3FE08{size:4B}{offset:4B} -> Response: T09FDBFE0

Element data format per entry (18 bytes header + variable name):
- Bytes 0-1: idx (uint16, big-endian)
- Bytes 2-8: extid (7 bytes hex string)
- Bytes 9-12: max (int32, big-endian, signed)
- Bytes 13-16: min (int32, big-endian, signed)
- Byte 17: name_length
- Bytes 18+: name (ASCII string, name_length-1 bytes)
"""

import json
import logging
import os
import struct
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from .can_adapter import USBtinAdapter

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


class ElementDiscovery:
    """FHEM-compatible element discovery for Buderus WPS heat pumps.

    This class orchestrates the CAN communication to discover all available
    parameters from the heat pump. It uses the ElementListParser for parsing
    the binary response data.

    Usage:
        >>> from buderus_wps import USBtinAdapter
        >>> with USBtinAdapter('/dev/ttyACM0') as adapter:
        ...     discovery = ElementDiscovery(adapter)
        ...     elements = discovery.discover()
        ...     for elem in elements:
        ...         print(f"{elem.text}: idx={elem.idx}")
    """

    # Chunk size for data requests (per FHEM implementation)
    CHUNK_SIZE = 4096

    # Estimated bytes per element (18-byte header + ~30 byte average name)
    BYTES_PER_ELEMENT = 50

    def __init__(
        self,
        adapter: "USBtinAdapter",
        discovery_logger: Optional[logging.Logger] = None,
    ) -> None:
        """Initialize element discovery.

        Args:
            adapter: Connected USBtinAdapter instance
            discovery_logger: Optional logger for debug output
        """
        self._adapter = adapter
        self._logger = discovery_logger or logger
        self._parser = ElementListParser()

    def request_element_count(self, timeout: float = 5.0) -> int:
        """Request the number of discoverable elements.

        Sends an RTR frame to ELEMENT_COUNT_REQUEST_ID and expects a 4-byte
        response with the element count.

        Args:
            timeout: Maximum time to wait for response

        Returns:
            Number of discoverable elements

        Raises:
            DeviceCommunicationError: No valid response received
        """
        from .can_message import CANMessage
        from .exceptions import DeviceCommunicationError, TimeoutError

        request = CANMessage(
            arbitration_id=ELEMENT_COUNT_REQUEST_ID,
            data=b"",
            is_extended_id=True,
            is_remote_frame=True,
        )

        self._logger.debug(
            "Requesting element count via RTR to 0x%08X", ELEMENT_COUNT_REQUEST_ID
        )

        try:
            response = self._adapter.send_frame(request, timeout=timeout)
        except TimeoutError:
            raise DeviceCommunicationError(
                "No response to element count request",
                context={"request_id": f"0x{ELEMENT_COUNT_REQUEST_ID:08X}"},
            )

        # Parse response
        count = self._parser.parse_count_response(response.arbitration_id, response.data)
        self._logger.info("Element count: %d", count)
        return count

    def request_data_chunk(
        self,
        offset: int,
        size: int = CHUNK_SIZE,
        timeout: float = 5.0,
    ) -> bytes:
        """Request a chunk of element data.

        Sends a data frame with size (4 bytes) and offset (4 bytes) to
        ELEMENT_DATA_REQUEST_ID, then collects the streamed response frames.

        Args:
            offset: Byte offset to start reading from
            size: Number of bytes to request (default: 4096)
            timeout: Maximum time to wait for complete response

        Returns:
            Raw element data bytes

        Raises:
            DeviceCommunicationError: No data received
        """
        from .can_message import CANMessage
        from .exceptions import DeviceCommunicationError, TimeoutError

        # Build request: size (4 bytes BE) + offset (4 bytes BE)
        request_data = struct.pack(">II", size, offset)

        request = CANMessage(
            arbitration_id=ELEMENT_DATA_REQUEST_ID,
            data=request_data,
            is_extended_id=True,
            is_remote_frame=False,
        )

        self._logger.debug(
            "Requesting %d bytes at offset %d from 0x%08X",
            size,
            offset,
            ELEMENT_DATA_REQUEST_ID,
        )

        # Send request without waiting (responses come as stream)
        self._adapter.send_frame_nowait(request)

        # Collect response stream
        try:
            data = self._adapter.receive_stream(
                expected_bytes=size,
                timeout=timeout,
                frame_filter=ELEMENT_DATA_RESPONSE_ID,
            )
            self._logger.debug("Received %d bytes in chunk", len(data))
            return data
        except TimeoutError:
            raise DeviceCommunicationError(
                f"No data received for chunk at offset {offset}",
                context={
                    "offset": offset,
                    "size": size,
                    "response_id": f"0x{ELEMENT_DATA_RESPONSE_ID:08X}",
                },
            )

    def discover(self, timeout: float = 30.0) -> List[DiscoveredElement]:
        """Discover all available parameters from the heat pump.

        This is the main entry point for parameter discovery. It:
        1. Requests the element count
        2. Reads element data in chunks
        3. Parses all element definitions

        Args:
            timeout: Maximum time for complete discovery

        Returns:
            List of all discovered elements

        Raises:
            DeviceCommunicationError: Discovery failed
        """
        from .exceptions import DeviceCommunicationError

        start_time = time.time()

        # Step 1: Get element count
        count = self.request_element_count(timeout=5.0)

        if count == 0:
            self._logger.warning("Heat pump reported 0 elements")
            return []

        # Estimate total data size
        estimated_size = count * self.BYTES_PER_ELEMENT
        self._logger.info(
            "Discovering %d elements (~%d bytes estimated)", count, estimated_size
        )

        # Step 2: Read data in chunks
        all_data = bytearray()
        offset = 0
        chunks_read = 0
        max_chunks = (estimated_size // self.CHUNK_SIZE) + 5  # Extra margin

        while chunks_read < max_chunks:
            elapsed = time.time() - start_time
            remaining = timeout - elapsed
            if remaining <= 0:
                self._logger.warning("Discovery timeout after %d bytes", len(all_data))
                break

            try:
                chunk = self.request_data_chunk(
                    offset=offset,
                    size=self.CHUNK_SIZE,
                    timeout=min(remaining, 5.0),
                )
                all_data.extend(chunk)
                offset += len(chunk)
                chunks_read += 1

                # If we got less than requested, we're done
                if len(chunk) < self.CHUNK_SIZE:
                    self._logger.debug(
                        "Got partial chunk (%d bytes), discovery complete", len(chunk)
                    )
                    break

            except DeviceCommunicationError:
                # No more data available
                self._logger.debug("No more data at offset %d", offset)
                break

        self._logger.info("Received %d bytes total in %d chunks", len(all_data), chunks_read)

        # Step 3: Parse elements
        elements = self._parser.parse_data_chunk(bytes(all_data))

        elapsed = time.time() - start_time
        self._logger.info(
            "Discovery complete: %d elements in %.1fs", len(elements), elapsed
        )

        return elements

    def discover_with_cache(
        self,
        cache_path: str,
        refresh: bool = False,
        timeout: float = 30.0,
    ) -> List[DiscoveredElement]:
        """Discover elements with optional caching.

        If a cache file exists and refresh is False, loads from cache.
        Otherwise performs discovery and saves to cache.

        Args:
            cache_path: Path to cache file (JSON format)
            refresh: If True, always perform fresh discovery
            timeout: Maximum time for discovery

        Returns:
            List of discovered elements
        """
        # Try loading from cache
        if not refresh and os.path.exists(cache_path):
            try:
                with open(cache_path, "r") as f:
                    cache_data = json.load(f)

                elements = [
                    DiscoveredElement(
                        idx=e["idx"],
                        extid=e["extid"],
                        text=e["text"],
                        min_value=e["min_value"],
                        max_value=e["max_value"],
                    )
                    for e in cache_data.get("elements", [])
                ]
                self._logger.info("Loaded %d elements from cache: %s", len(elements), cache_path)
                return elements

            except (json.JSONDecodeError, KeyError, OSError) as e:
                self._logger.warning("Failed to load cache: %s", e)

        # Perform discovery
        elements = self.discover(timeout=timeout)

        # Save to cache
        try:
            cache_data = {
                "version": 1,
                "timestamp": time.time(),
                "count": len(elements),
                "elements": [
                    {
                        "idx": e.idx,
                        "extid": e.extid,
                        "text": e.text,
                        "min_value": e.min_value,
                        "max_value": e.max_value,
                    }
                    for e in elements
                ],
            }
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
            self._logger.info("Saved %d elements to cache: %s", len(elements), cache_path)
        except OSError as e:
            self._logger.warning("Failed to save cache: %s", e)

        return elements
