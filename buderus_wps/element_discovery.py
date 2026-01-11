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
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .can_adapter import USBtinAdapter

logger = logging.getLogger(__name__)

# PROTOCOL: CAN IDs for element list discovery
ELEMENT_COUNT_REQUEST_ID = 0x01FD7FE0  # R01FD7FE00 (RTR)
ELEMENT_COUNT_RESPONSE_ID = 0x09FD7FE0  # T09FD7FE0
ELEMENT_DATA_REQUEST_ID = 0x01FD3FE0  # T01FD3FE08...
ELEMENT_DATA_RESPONSE_ID = 0x09FDBFE0  # T09FDBFE0
ELEMENT_BUFFER_READ_ID = 0x01FDBFE0  # R01FDBFE00 (RTR)

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
        """Parse total element data length from T09FD7FE0 response.

        Args:
            can_id: The CAN arbitration ID of the response
            data: The CAN message data bytes (4+ bytes)

        Returns:
            Total number of element data bytes available

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
        # FHEM uses: ($value1 >> 24) which extracts the first 4 bytes
        # from the response payload when treated as a multi-byte integer.
        count: int = struct.unpack(">I", data[:4])[0]
        return count

    def parse_data_chunk(self, data: bytes) -> list[DiscoveredElement]:
        """Parse element definitions from T09FDBFE0 response data.

        The data contains concatenated element entries. Each entry has:
        - 18-byte header (idx, extid, max, min, name_length)
        - Variable-length name string

        Args:
            data: Raw element data bytes (accumulated from multiple CAN frames)

        Returns:
            List of parsed DiscoveredElement instances
        """
        elements: list[DiscoveredElement] = []
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
    ) -> tuple[Optional[DiscoveredElement], int]:
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

        # Check if we have enough data for the name + null terminator
        if offset + ELEMENT_HEADER_SIZE + name_length > len(data):
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

        # Total bytes consumed (includes null terminator)
        total_bytes = ELEMENT_HEADER_SIZE + name_length

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
        self._last_reported_bytes: int = (
            0  # Tracks reported byte count from last discovery
        )
        self._last_received_bytes: int = (
            0  # Tracks received byte count from last discovery
        )

    def request_element_count(self, timeout: float = 5.0, max_retries: int = 3) -> int:
        """Request the total element data length.

        Sends an RTR frame to ELEMENT_COUNT_REQUEST_ID and expects a 4-byte
        response with the element count. Retries on failure.

        Args:
            timeout: Maximum time to wait for response per attempt
            max_retries: Number of attempts before giving up (default: 3)

        Returns:
            Total element data length in bytes

        Raises:
            DeviceCommunicationError: No valid response after all retries
        """
        from .can_message import CANMessage
        from .exceptions import DeviceCommunicationError, TimeoutError

        request = CANMessage(
            arbitration_id=ELEMENT_COUNT_REQUEST_ID,
            data=b"",
            is_extended_id=True,
            is_remote_frame=True,
        )

        last_error: Optional[Exception] = None

        for attempt in range(max_retries):
            self._logger.debug(
                "Requesting element count via RTR to 0x%08X (attempt %d/%d)",
                ELEMENT_COUNT_REQUEST_ID,
                attempt + 1,
                max_retries,
            )

            try:
                response = self._adapter.send_frame(request, timeout=timeout)

                # If we got unrelated traffic, keep reading until the expected response
                start_time = time.time()
                while response.arbitration_id != ELEMENT_COUNT_RESPONSE_ID:
                    remaining = timeout - (time.time() - start_time)
                    if remaining <= 0:
                        raise TimeoutError(
                            "Timed out waiting for element count response",
                            context={
                                "expected_id": f"0x{ELEMENT_COUNT_RESPONSE_ID:08X}",
                                "last_id": f"0x{response.arbitration_id:08X}",
                            },
                        )
                    response = self._adapter.receive_frame(timeout=min(1.0, remaining))

                # Parse response
                count = self._parser.parse_count_response(
                    response.arbitration_id, response.data
                )
                self._logger.info("Element data length: %d bytes", count)
                return count

            except TimeoutError as e:
                last_error = e
                if attempt < max_retries - 1:
                    self._logger.warning(
                        "Count request attempt %d/%d timed out, retrying in 0.5s",
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(0.5)

            except ValueError as e:
                last_error = e
                if attempt < max_retries - 1:
                    self._logger.warning(
                        "Count request attempt %d/%d got invalid response: %s, retrying in 0.5s",
                        attempt + 1,
                        max_retries,
                        e,
                    )
                    time.sleep(0.5)

        # All retries exhausted
        raise DeviceCommunicationError(
            f"No valid response to element count request after {max_retries} attempts",
            context={
                "request_id": f"0x{ELEMENT_COUNT_REQUEST_ID:08X}",
                "last_error": str(last_error),
            },
        )

    def request_data_chunk(
        self,
        offset: int,
        size: int = CHUNK_SIZE,
        timeout: float = 5.0,
    ) -> bytes:
        """Request a chunk of element data.

        Sends a data frame with size (4 bytes) and offset (4 bytes) to
        ELEMENT_DATA_REQUEST_ID, then sends an RTR to ELEMENT_BUFFER_READ_ID
        to trigger the streamed response frames.

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

        # Flush pending traffic to avoid mixing with discovery frames
        self._adapter.flush_input_buffer()

        # Send request without waiting (responses come as stream)
        self._adapter.send_frame_nowait(request)
        # Trigger buffered data stream (FHEM sends RTR immediately after request)
        buffer_request = CANMessage(
            arbitration_id=ELEMENT_BUFFER_READ_ID,
            data=b"",
            is_extended_id=True,
            is_remote_frame=True,
        )
        self._adapter.send_frame_nowait(buffer_request)

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

    def discover(
        self,
        timeout: float = 30.0,
        min_completion_ratio: float = 0.95,
    ) -> list[DiscoveredElement]:
        """Discover all available parameters from the heat pump.

        This is the main entry point for parameter discovery. It:
        1. Requests the element data length
        2. Reads element data in chunks
        3. Parses all element definitions
        4. Validates completeness against reported byte count

        Args:
            timeout: Maximum time for complete discovery
            min_completion_ratio: Minimum ratio of actual/reported bytes required
                (default 0.95 = 95%). Set to 0.0 to disable validation.

        Returns:
            List of all discovered elements

        Raises:
            DeviceCommunicationError: Discovery failed
            DiscoveryIncompleteError: Fewer bytes than min_completion_ratio
        """
        from .exceptions import DeviceCommunicationError, DiscoveryIncompleteError

        start_time = time.time()

        # Step 1: Get element data length in bytes
        reported_bytes = self.request_element_count(timeout=5.0)
        self._last_reported_bytes = reported_bytes  # Store for cache metadata

        if reported_bytes == 0:
            self._logger.warning("Heat pump reported 0 bytes of element data")
            return []

        # Estimated total data size (already in bytes)
        estimated_size = reported_bytes
        self._logger.info(
            "Discovering element list (%d bytes reported)", estimated_size
        )

        # Step 2: Read data in chunks
        all_data = bytearray()
        offset = 0
        chunks_read = 0
        max_chunks = (estimated_size // self.CHUNK_SIZE) + 5  # Extra margin

        while chunks_read < max_chunks and offset < reported_bytes:
            elapsed = time.time() - start_time
            remaining = timeout - elapsed
            if remaining <= 0:
                self._logger.warning("Discovery timeout after %d bytes", len(all_data))
                break

            try:
                chunk_size = min(self.CHUNK_SIZE, reported_bytes - offset)
                chunk = self.request_data_chunk(
                    offset=offset,
                    size=chunk_size,
                    timeout=min(remaining, 5.0),
                )
                all_data.extend(chunk)
                offset += len(chunk)
                chunks_read += 1

                # If we got less than requested, we're done
                if len(chunk) < chunk_size:
                    self._logger.debug(
                        "Got partial chunk (%d bytes), discovery complete", len(chunk)
                    )
                    break

            except DeviceCommunicationError:
                # No more data available
                self._logger.debug("No more data at offset %d", offset)
                break

        self._logger.info(
            "Received %d bytes total in %d chunks", len(all_data), chunks_read
        )
        self._last_received_bytes = len(all_data)

        # Step 3: Parse elements
        elements = self._parser.parse_data_chunk(bytes(all_data))

        # Step 4: Validate completeness against reported bytes
        actual_bytes = len(all_data)
        completion_ratio = actual_bytes / reported_bytes if reported_bytes > 0 else 1.0

        if actual_bytes > reported_bytes:
            self._logger.warning(
                "Discovery returned more bytes than reported: %d vs %d",
                actual_bytes,
                reported_bytes,
            )
        elif completion_ratio < min_completion_ratio:
            self._logger.warning(
                "Discovery incomplete: got %d/%d bytes (%.1f%%), "
                "threshold is %.0f%%",
                actual_bytes,
                reported_bytes,
                completion_ratio * 100,
                min_completion_ratio * 100,
            )
            raise DiscoveryIncompleteError(actual_bytes, reported_bytes)
        elif actual_bytes < reported_bytes:
            # Below 100% but above threshold - log but continue
            self._logger.info(
                "Discovery mostly complete: got %d/%d bytes (%.1f%%)",
                actual_bytes,
                reported_bytes,
                completion_ratio * 100,
            )

        elapsed = time.time() - start_time
        self._logger.info(
            "Discovery complete: %d/%d bytes in %.1fs (%d elements parsed)",
            actual_bytes,
            reported_bytes,
            elapsed,
            len(elements),
        )

        return elements

    def discover_with_cache(
        self,
        cache_path: str,
        refresh: bool = False,
        max_cache_age: Optional[float] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        min_completion_ratio: float = 0.95,
    ) -> list[DiscoveredElement]:
        """Discover elements with caching and fail-fast behavior.

        IMPORTANT: This method implements fail-fast on fresh install and
        cache-only fallback. It NEVER falls back to static defaults for idx.

        Behavior:
        - If valid cache exists and refresh=False: Load from cache
        - If discovery succeeds: Save to cache and return
        - If discovery fails AND valid cache exists: Fall back to cache
        - If discovery fails AND no cache (fresh install): Raise DiscoveryRequiredError

        Args:
            cache_path: Path to cache file (JSON format)
            refresh: If True, always perform fresh discovery
            max_cache_age: Maximum cache age in seconds. If cache is older, refresh.
                          None means no age limit (default).
            timeout: Maximum time for discovery per attempt
            max_retries: Number of retry attempts on incomplete discovery (default: 3)
            min_completion_ratio: Minimum ratio of actual/reported bytes required
                (default 0.95 = 95%). Set to 0.0 to disable validation.

        Returns:
            List of discovered elements

        Raises:
            DiscoveryRequiredError: On fresh install when discovery fails
        """
        from .exceptions import DiscoveryIncompleteError, DiscoveryRequiredError

        # Track if we have a valid cache to fall back to
        cached_elements: Optional[list[DiscoveredElement]] = None
        cache_existed = False

        # Try loading from cache
        if os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    cache_data = json.load(f)

                # Log cache metadata if available (version 2)
                version = cache_data.get("version", 1)
                complete = cache_data.get("complete", True)
                reported = cache_data.get(
                    "reported_bytes", cache_data.get("reported_count", "?")
                )
                actual = cache_data.get("actual_bytes", "?")

                # Only consider complete caches as valid fallback
                if complete:
                    cached_elements = [
                        DiscoveredElement(
                            idx=e["idx"],
                            extid=e["extid"],
                            text=e["text"],
                            min_value=e["min_value"],
                            max_value=e["max_value"],
                        )
                        for e in cache_data.get("elements", [])
                    ]
                    cache_existed = True
                    self._logger.debug(
                        "Valid cache available: %d elements (v%d, bytes=%s/%s)",
                        len(cached_elements),
                        version,
                        actual,
                        reported,
                    )

                # Check cache age if max_cache_age specified
                needs_refresh = refresh
                if max_cache_age is not None and not refresh:
                    # Support both version 1 (timestamp as float) and version 2 (timestamp_unix)
                    cache_timestamp = cache_data.get(
                        "timestamp_unix", cache_data.get("timestamp", 0)
                    )
                    # Handle ISO format timestamps from version 2
                    if isinstance(cache_timestamp, str):
                        cache_timestamp = cache_data.get("timestamp_unix", 0)

                    cache_age = time.time() - cache_timestamp
                    if cache_age > max_cache_age:
                        self._logger.info(
                            "Cache expired (age=%.0fs > max=%.0fs), will refresh",
                            cache_age,
                            max_cache_age,
                        )
                        needs_refresh = True
                    else:
                        self._logger.debug(
                            "Cache valid (age=%.0fs <= max=%.0fs)",
                            cache_age,
                            max_cache_age,
                        )

                # Force refresh if cached discovery was incomplete
                if not complete and not refresh:
                    self._logger.warning(
                        "Cached discovery incomplete (%s/%s bytes), will refresh",
                        actual,
                        reported,
                    )
                    needs_refresh = True

                # Return cached elements if no refresh needed
                if not needs_refresh and cached_elements:
                    self._logger.info(
                        "Loaded %d elements from cache v%d: %s (bytes=%s/%s)",
                        len(cached_elements),
                        version,
                        cache_path,
                        actual,
                        reported,
                    )
                    return cached_elements

            except (json.JSONDecodeError, KeyError, OSError) as e:
                self._logger.warning("Failed to load cache: %s", e)

        # Perform discovery with retry on incomplete results
        elements: list[DiscoveredElement] = []
        last_error: Optional[Exception] = None
        discovery_succeeded = False

        for attempt in range(max_retries):
            try:
                self._logger.debug("Discovery attempt %d/%d", attempt + 1, max_retries)
                elements = self.discover(
                    timeout=timeout,
                    min_completion_ratio=min_completion_ratio,
                )
                discovery_succeeded = True
                break  # Success - exit retry loop

            except DiscoveryIncompleteError as e:
                last_error = e
                if attempt < max_retries - 1:
                    self._logger.warning(
                        "Discovery attempt %d/%d incomplete (%d/%d bytes), "
                        "retrying in 1s...",
                        attempt + 1,
                        max_retries,
                        e.actual_count,
                        e.reported_count,
                    )
                    time.sleep(1.0)  # Brief delay before retry

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    self._logger.warning(
                        "Discovery attempt %d/%d failed: %s, retrying in 1s...",
                        attempt + 1,
                        max_retries,
                        e,
                    )
                    time.sleep(1.0)

        # Handle discovery failure
        if not discovery_succeeded:
            if cache_existed and cached_elements:
                # Cache-only fallback: use last successful discovery
                self._logger.warning(
                    "Discovery failed after %d attempts, falling back to cached data "
                    "(%d elements). Last error: %s",
                    max_retries,
                    len(cached_elements),
                    last_error,
                )
                return cached_elements
            else:
                # Fail-fast: no cache means we can't proceed with reliable idx values
                error_detail = str(last_error) if last_error else "unknown error"
                self._logger.error(
                    "Discovery failed after %d attempts with no valid cache. "
                    "Cannot proceed without discovered parameter indices. Error: %s",
                    max_retries,
                    error_detail,
                )
                raise DiscoveryRequiredError(error_detail)

        # Save successful discovery to cache
        try:
            from datetime import datetime, timezone

            reported_bytes = self._last_reported_bytes
            actual_bytes = self._last_received_bytes
            actual_count = len(elements)
            is_complete = (
                actual_bytes >= reported_bytes * min_completion_ratio
                if reported_bytes > 0
                else True
            )

            cache_data = {
                "version": 2,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "timestamp_unix": time.time(),
                "reported_count": reported_bytes,  # Backward compatibility (bytes)
                "actual_count": actual_count,
                "reported_bytes": reported_bytes,
                "actual_bytes": actual_bytes,
                "complete": is_complete,
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
            self._logger.info(
                "Saved %d elements (%d/%d bytes) to cache: %s (complete=%s)",
                actual_count,
                actual_bytes,
                reported_bytes,
                cache_path,
                is_complete,
            )
        except OSError as e:
            self._logger.warning("Failed to save cache: %s", e)

        return elements
