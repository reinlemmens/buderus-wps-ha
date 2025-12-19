"""Buderus WPS Heat Pump Parameter Discovery Protocol.

# PROTOCOL: This module implements the CAN bus discovery protocol from FHEM.
# Source: fhem/26_KM273v018.pm:2052-2187

This module provides classes for discovering parameter definitions from the
Buderus WPS heat pump via the CAN bus protocol. The discovery protocol retrieves
binary element data that describes all available parameters.

Classes:
    ParameterDiscovery: Implements the discovery protocol and binary parsing

CAN IDs:
    ELEMENT_COUNT_SEND (0x01FD7FE0): Request element count
    ELEMENT_COUNT_RECV (0x09FD7FE0): Receive element count
    ELEMENT_DATA_SEND (0x01FD3FE0): Request element data
    ELEMENT_DATA_RECV (0x09FDBFE0): Receive element data

Example:
    >>> discovery = ParameterDiscovery(can_adapter)
    >>> elements = await discovery.discover()
    >>> print(f"Discovered {len(elements)} parameters")
"""

import logging
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DiscoveryError(Exception):
    """Error during parameter discovery protocol."""

    pass


class ParameterDiscovery:
    """Discovers parameters from Buderus WPS heat pump via CAN bus.

    # PROTOCOL: Discovery sequence from fhem/26_KM273v018.pm:2052-2187

    This class implements the binary protocol for retrieving parameter definitions
    from the heat pump. The protocol uses fixed CAN IDs for discovery (not the
    dynamic IDs used for parameter read/write).

    Attributes:
        ELEMENT_COUNT_SEND: CAN ID for requesting element count
        ELEMENT_COUNT_RECV: CAN ID for receiving element count
        ELEMENT_DATA_SEND: CAN ID for requesting element data
        ELEMENT_DATA_RECV: CAN ID for receiving element data
        CHUNK_SIZE: Size of data chunks (4096 bytes)

    Example:
        >>> discovery = ParameterDiscovery(can_adapter)
        >>> elements = await discovery.discover()
        >>> for elem in elements:
        ...     print(f"{elem['idx']}: {elem['text']}")
    """

    # PROTOCOL: Fixed discovery CAN IDs from fhem/26_KM273v018.pm:2052-2080
    ELEMENT_COUNT_SEND = 0x01FD7FE0
    ELEMENT_COUNT_RECV = 0x09FD7FE0
    ELEMENT_DATA_SEND = 0x01FD3FE0
    ELEMENT_DATA_RECV = 0x09FDBFE0
    ELEMENT_BUFFER_READ = 0x01FDBFE0

    # PROTOCOL: Chunk size for element data requests
    # Note: The USBtin adapter cannot keep up with the burst of CAN frames at 125kbit/s
    # Discovery typically receives ~96% of bytes but with frame loss causing data corruption
    # For reliable parameter data, use the static fallback (parameter_data.py)
    CHUNK_SIZE = 4096

    # PROTOCOL: Validation constants from fhem/26_KM273v018.pm:2139
    MIN_HEADER_SIZE = 18
    MIN_NAME_LENGTH = 2  # len must be > 1 (len > 1)
    MAX_NAME_LENGTH = 99  # len must be < 100 (len < 100)

    # Timeout and retry settings
    DEFAULT_TIMEOUT = 5.0
    MAX_RETRIES = 3
    CHUNK_READ_TIMEOUT = 5.0  # Per-chunk timeout (smaller chunks = faster)

    def __init__(self, adapter: Any = None, timeout: float = DEFAULT_TIMEOUT):
        """Initialize discovery with optional CAN adapter.

        Args:
            adapter: CAN adapter for communication (optional for testing)
            timeout: Timeout for individual CAN operations in seconds
        """
        self._adapter = adapter
        self._timeout = timeout

    @staticmethod
    def parse_element(data: bytes, offset: int) -> Tuple[Optional[Dict], int]:
        """Parse single element from binary data.

        # PROTOCOL: Binary structure from fhem/26_KM273v018.pm:2135-2143
        # Perl unpack: "nH14NNc" = idx(2, BE), extid(7), max(4, BE), min(4, BE), len(1)

        The binary format uses network byte order (big-endian):
        - idx: 2 bytes, unsigned short (big-endian)
        - extid: 7 bytes, hex string (14 hex chars)
        - max: 4 bytes, unsigned int (big-endian, converted to signed)
        - min: 4 bytes, unsigned int (big-endian, converted to signed)
        - len: 1 byte, signed char (length of name including null terminator)
        - name: len-1 bytes, ASCII string (null-terminated)

        Args:
            data: Binary data containing element(s)
            offset: Byte offset to start parsing

        Returns:
            Tuple of (element_dict, next_offset) on success.
            Returns (None, -1) on error (truncated data, invalid length, etc.)

        Example:
            >>> data = b'\\x00\\x01...'  # binary element data
            >>> element, next_offset = ParameterDiscovery.parse_element(data, 0)
            >>> print(element['text'])
            'ACCESS_LEVEL'
        """
        # Check if we have enough data for header
        if offset < 0 or offset + ParameterDiscovery.MIN_HEADER_SIZE > len(data):
            return None, -1

        try:
            # Parse fixed header (18 bytes)
            # PROTOCOL: unpack("nH14NNc", ...)
            idx = struct.unpack_from('>H', data, offset)[0]  # n = unsigned short, big-endian
            extid_bytes = data[offset + 2:offset + 9]  # H14 = 7 bytes -> 14 hex chars
            extid = extid_bytes.hex().upper()
            max_unsigned = struct.unpack_from('>I', data, offset + 9)[0]  # N = unsigned int, big-endian
            min_unsigned = struct.unpack_from('>I', data, offset + 13)[0]  # N = unsigned int, big-endian
            name_len = struct.unpack_from('b', data, offset + 17)[0]  # c = signed char

            # PROTOCOL: Convert unsigned to signed (like FHEM: unpack 'l*', pack 'L*', $val)
            max_val = struct.unpack('i', struct.pack('I', max_unsigned))[0]
            min_val = struct.unpack('i', struct.pack('I', min_unsigned))[0]

            # PROTOCOL: Validate name length (len > 1 && len < 100) from fhem line 2139
            if name_len < ParameterDiscovery.MIN_NAME_LENGTH:
                return None, -1
            if name_len >= ParameterDiscovery.MAX_NAME_LENGTH + 1:  # len must be < 100
                return None, -1

            # Check if we have enough data for name
            name_start = offset + 18
            name_end = name_start + name_len - 1  # len-1 bytes (excluding null terminator)
            if name_end > len(data):
                return None, -1

            # Extract name (PROTOCOL: substr(...,$i1+18,$len2-1))
            name_bytes = data[name_start:name_end]
            name = name_bytes.decode('ascii', errors='replace').rstrip('\x00')

            # Build element dict
            element = {
                'idx': idx,
                'extid': extid,
                'max': max_val,
                'min': min_val,
                'format': 'int',  # Default format
                'read': 0,  # Default to writable (discovery doesn't provide this)
                'text': name
            }

            # PROTOCOL: Next element at $i1 += 18+$len2
            next_offset = offset + 18 + name_len

            return element, next_offset

        except (struct.error, UnicodeDecodeError):
            return None, -1

    def _create_rtr_message(self, can_id: int, dlc: int = 0) -> Any:
        """Create an RTR (Remote Transmission Request) CAN message.

        # PROTOCOL: RTR frames request data from the device

        Args:
            can_id: CAN arbitration ID
            dlc: Data length code (typically 0 for RTR)

        Returns:
            CANMessage configured as RTR frame
        """
        # Import here to avoid circular imports
        from buderus_wps.can_message import CANMessage

        return CANMessage(
            arbitration_id=can_id,
            data=b'',
            is_extended_id=True,
            is_remote_frame=True,
            _requested_dlc=dlc
        )

    def _create_data_message(self, can_id: int, data: bytes) -> Any:
        """Create a data CAN message.

        Args:
            can_id: CAN arbitration ID
            data: Payload data (up to 8 bytes)

        Returns:
            CANMessage with data payload
        """
        from buderus_wps.can_message import CANMessage

        return CANMessage(
            arbitration_id=can_id,
            data=data,
            is_extended_id=True,
            is_remote_frame=False
        )

    def _request_element_count(self) -> int:
        """Request and receive element count from device.

        # PROTOCOL: Send RTR to 0x01FD7FE0, receive count on 0x09FD7FE0
        # FHEM: CAN_Write($hash,"R01FD7FE00") at line 2061
        # Response parsing: $readCounter = ($value1 >> 24) at line 2161

        Returns:
            Number of elements (bytes of element data)

        Raises:
            DiscoveryError: On timeout or protocol error
        """
        logger.info("Requesting element count from device")

        # Flush any pending broadcast traffic
        self._adapter.flush_input_buffer()

        # Send RTR request
        request = self._create_rtr_message(self.ELEMENT_COUNT_SEND)
        try:
            response = self._adapter.send_frame(request, timeout=self._timeout)
        except Exception as e:
            raise DiscoveryError(f"Failed to request element count: {e}") from e

        # If we got broadcast traffic, keep reading until we get our response
        start_time = time.time()
        while response.arbitration_id != self.ELEMENT_COUNT_RECV:
            if time.time() - start_time > self._timeout:
                raise DiscoveryError(
                    f"Timeout waiting for element count response. "
                    f"Last received: 0x{response.arbitration_id:08X}"
                )
            try:
                response = self._adapter.receive_frame(timeout=1.0)
            except Exception:
                continue

        # Parse element count from response
        # PROTOCOL: count is in first byte (value >> 24 in FHEM's 8-byte value)
        if len(response.data) < 1:
            raise DiscoveryError("Empty response to element count request")

        # The count is actually the total bytes of element data
        # In FHEM: readCounter from first bytes of response
        if len(response.data) >= 4:
            count = struct.unpack('>I', response.data[:4])[0]
        else:
            count = response.data[0]

        logger.info("Element data size: %d bytes", count)
        return count

    def _request_element_chunk(self, offset: int, length: int) -> bytes:
        """Request a chunk of element data from device.

        # PROTOCOL: Send data request to 0x01FD3FE0 with length and offset
        # FHEM: sprintf("T01FD3FE08%08x%08x",4096,$writeIndex) at line 2078
        # Then send RTR to 0x01FDBFE0 to read buffer
        # Device responds with multiple T09FDBFE0 frames (8 bytes each)

        Args:
            offset: Byte offset to start reading
            length: Number of bytes to request (typically CHUNK_SIZE)

        Returns:
            Received data bytes

        Raises:
            DiscoveryError: On timeout or protocol error
        """
        logger.debug("Requesting element chunk: offset=%d, length=%d", offset, length)

        # Flush any pending broadcast traffic
        self._adapter.flush_input_buffer()

        # Build data request payload: 4 bytes length + 4 bytes offset (big-endian)
        # PROTOCOL: T01FD3FE08[length:8hex][offset:8hex]
        request_data = struct.pack('>II', length, offset)
        data_request = self._create_data_message(self.ELEMENT_DATA_SEND, request_data)

        # PROTOCOL: FHEM sends both messages quickly without waiting for response
        # This is critical - waiting between messages causes frame loss
        buffer_request = self._create_rtr_message(self.ELEMENT_BUFFER_READ)

        try:
            # Send data request immediately (no wait)
            self._adapter.send_frame_nowait(data_request)
            # Immediately send RTR to trigger data stream
            self._adapter.send_frame_nowait(buffer_request)
        except Exception as e:
            raise DiscoveryError(f"Failed to send discovery request: {e}") from e

        # Now collect all the data frames that come back
        expected_bytes = min(length, self.CHUNK_SIZE)

        try:
            chunk_data = self._adapter.receive_stream(
                expected_bytes=expected_bytes,
                timeout=self.CHUNK_READ_TIMEOUT,
                frame_filter=self.ELEMENT_DATA_RECV
            )
            logger.debug(
                "Stream received: %d bytes",
                len(chunk_data)
            )
        except Exception as e:
            # Partial data is acceptable - might be end of element data
            logger.debug("Stream ended early: %s", e)
            chunk_data = b''

        logger.info(
            "Chunk complete: offset=%d, received=%d/%d bytes",
            offset, len(chunk_data), expected_bytes
        )
        return bytes(chunk_data)

    def _parse_all_elements(self, data: bytes) -> List[Dict]:
        """Parse all elements from binary data.

        # PROTOCOL: Parse loop from fhem/26_KM273v018.pm:2131-2155

        Args:
            data: Complete binary element data

        Returns:
            List of parsed element dictionaries
        """
        elements = []
        offset = 0
        last_idx = -1

        while offset < len(data):
            element, next_offset = self.parse_element(data, offset)

            if element is None:
                # Skip invalid data
                offset += 1
                continue

            # PROTOCOL: Validate idx is increasing (idx > $idLast) from line 2138
            if element['idx'] <= last_idx:
                logger.warning(
                    "Non-increasing idx at offset %d: %d <= %d",
                    offset, element['idx'], last_idx
                )
                offset += 1
                continue

            elements.append(element)
            last_idx = element['idx']
            offset = next_offset

            if len(elements) % 100 == 0:
                logger.debug("Parsed %d elements...", len(elements))

        logger.info("Parsed %d elements from %d bytes", len(elements), len(data))
        return elements

    async def discover(self) -> List[Dict]:
        """Execute full discovery protocol.

        # PROTOCOL: Discovery sequence from fhem/26_KM273v018.pm:2052-2187

        This method:
        1. Requests element count using ELEMENT_COUNT_SEND
        2. Retrieves element data in CHUNK_SIZE chunks
        3. Parses all elements from binary data

        Returns:
            List of element dicts with keys: idx, extid, max, min, format, read, text

        Raises:
            DiscoveryError: On timeout or protocol error
            RuntimeError: If no adapter is configured
        """
        if self._adapter is None:
            raise RuntimeError("No CAN adapter configured for discovery")

        logger.info("Starting parameter discovery protocol")

        # Step 1: Get element count (total bytes of element data)
        element_count = self._request_element_count()

        if element_count == 0:
            logger.warning("Device reported 0 elements")
            return []

        # Step 2: Retrieve element data in chunks
        all_data = bytearray()
        offset = 0

        while offset < element_count:
            remaining = element_count - offset
            chunk_size = min(self.CHUNK_SIZE, remaining)

            logger.info(
                "Fetching chunk: offset=%d, size=%d (%.1f%% complete)",
                offset, chunk_size, (offset / element_count) * 100
            )

            chunk = self._request_element_chunk(offset, chunk_size)
            if not chunk:
                logger.warning("Empty chunk at offset %d", offset)
                break

            all_data.extend(chunk)
            offset += len(chunk)

            # Safety check - if we got less than requested, we're done
            if len(chunk) < chunk_size:
                logger.info("Received partial chunk, assuming end of data")
                break

        logger.info("Received %d total bytes of element data", len(all_data))

        # Step 3: Parse all elements
        elements = self._parse_all_elements(bytes(all_data))

        logger.info("Discovery complete: found %d parameters", len(elements))
        return elements

    def discover_sync(self) -> List[Dict]:
        """Synchronous wrapper for discover().

        Convenience method for use in synchronous code.

        Returns:
            List of element dicts

        Raises:
            DiscoveryError: On discovery failure
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.discover())
