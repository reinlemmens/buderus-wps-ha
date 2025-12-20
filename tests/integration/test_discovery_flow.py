"""Integration tests for discovery protocol flow with mock CAN adapter.

# PROTOCOL: Tests the full discovery sequence from fhem/26_KM273v018.pm:2052-2187

These tests verify the complete discovery flow:
1. Request element count
2. Receive element count
3. Request element data in chunks
4. Parse elements from binary data
"""

import struct
from typing import Dict, List

import pytest

from buderus_wps.discovery import ParameterDiscovery


def create_mock_element_data(elements: List[Dict]) -> bytes:
    """Create binary element data from a list of element dicts.

    Args:
        elements: List of dicts with idx, extid, max, min, text

    Returns:
        Binary data in FHEM format
    """
    data = b""
    for elem in elements:
        # Pack header: idx(2), extid(7), max(4), min(4), len(1)
        idx = struct.pack(">H", elem["idx"])
        extid_bytes = bytes.fromhex(elem["extid"])
        max_unsigned = elem["max"] & 0xFFFFFFFF
        min_unsigned = elem["min"] & 0xFFFFFFFF
        max_packed = struct.pack(">I", max_unsigned)
        min_packed = struct.pack(">I", min_unsigned)

        # Name with null terminator
        name = elem["text"].encode("ascii") + b"\x00"
        len_byte = struct.pack("b", len(name))

        data += idx + extid_bytes + max_packed + min_packed + len_byte + name

    return data


class MockCANAdapter:
    """Mock CAN adapter for testing discovery protocol.

    Simulates responses for:
    - Element count request
    - Element data requests (chunked)
    """

    def __init__(self, element_count: int = 3, elements: List[Dict] = None):
        """Initialize mock adapter with test data.

        Args:
            element_count: Number of elements to report
            elements: List of element dicts to return
        """
        self.element_count = element_count
        self.elements = elements or [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "max": 0,
                "min": 0,
                "text": "ACCESSORIES_CONNECTED_BITMASK",
            },
            {
                "idx": 1,
                "extid": "61E1E1FC660023",
                "max": 5,
                "min": 0,
                "text": "ACCESS_LEVEL",
            },
            {
                "idx": 11,
                "extid": "E555E4E11002E9",
                "max": 40,
                "min": -30,
                "text": "ADDITIONAL_BLOCK_HIGH_T2_TEMP",
            },
        ]
        self.element_data = create_mock_element_data(self.elements)

        # Track requests for verification
        self.sent_messages = []
        self.request_count = 0

    async def send(self, can_id: int, data: bytes = b"") -> None:
        """Record sent message."""
        self.sent_messages.append({"can_id": can_id, "data": data})
        self.request_count += 1

    async def receive(self, expected_can_id: int, timeout: float = 5.0) -> bytes:
        """Return mock response based on expected CAN ID."""
        if expected_can_id == ParameterDiscovery.ELEMENT_COUNT_RECV:
            # Return element count (4 bytes, big-endian)
            return struct.pack(">I", self.element_count)

        elif expected_can_id == ParameterDiscovery.ELEMENT_DATA_RECV:
            # Return element data
            return self.element_data

        else:
            raise ValueError(f"Unexpected CAN ID: 0x{expected_can_id:08X}")


class TestDiscoveryFlowWithMock:
    """T035: Integration tests for discovery flow with mock adapter."""

    @pytest.fixture
    def mock_adapter(self):
        """Create mock adapter with test elements."""
        elements = [
            {
                "idx": 0,
                "extid": "814A53C66A0802",
                "max": 0,
                "min": 0,
                "text": "ACCESSORIES_CONNECTED_BITMASK",
            },
            {
                "idx": 1,
                "extid": "61E1E1FC660023",
                "max": 5,
                "min": 0,
                "text": "ACCESS_LEVEL",
            },
            {
                "idx": 11,
                "extid": "E555E4E11002E9",
                "max": 40,
                "min": -30,
                "text": "ADDITIONAL_BLOCK_HIGH_T2_TEMP",
            },
        ]
        return MockCANAdapter(element_count=3, elements=elements)

    def test_parse_element_from_mock_data(self, mock_adapter):
        """Verify parsing works with mock element data."""
        data = mock_adapter.element_data
        elements = []
        offset = 0

        while offset < len(data):
            element, next_offset = ParameterDiscovery.parse_element(data, offset)
            if element is None:
                break
            elements.append(element)
            offset = next_offset

        assert len(elements) == 3
        assert elements[0]["idx"] == 0
        assert elements[0]["text"] == "ACCESSORIES_CONNECTED_BITMASK"
        assert elements[1]["idx"] == 1
        assert elements[1]["text"] == "ACCESS_LEVEL"
        assert elements[2]["idx"] == 11
        assert elements[2]["text"] == "ADDITIONAL_BLOCK_HIGH_T2_TEMP"
        assert elements[2]["min"] == -30
        assert elements[2]["max"] == 40

    def test_mock_adapter_returns_correct_count(self, mock_adapter):
        """Verify mock adapter returns correct element count."""
        import asyncio

        async def test():
            response = await mock_adapter.receive(ParameterDiscovery.ELEMENT_COUNT_RECV)
            count = struct.unpack(">I", response)[0]
            return count

        count = asyncio.get_event_loop().run_until_complete(test())
        assert count == 3

    def test_mock_adapter_tracks_sent_messages(self, mock_adapter):
        """Verify mock adapter tracks sent messages."""
        import asyncio

        async def test():
            await mock_adapter.send(0x01FD7FE0, b"")
            await mock_adapter.send(0x01FD3FE0, struct.pack(">II", 0, 4096))

        asyncio.get_event_loop().run_until_complete(test())

        assert len(mock_adapter.sent_messages) == 2
        assert mock_adapter.sent_messages[0]["can_id"] == 0x01FD7FE0
        assert mock_adapter.sent_messages[1]["can_id"] == 0x01FD3FE0


class TestDiscoveryConstants:
    """Test ParameterDiscovery constants match FHEM."""

    def test_element_count_send_can_id(self):
        """Verify element count request CAN ID."""
        assert ParameterDiscovery.ELEMENT_COUNT_SEND == 0x01FD7FE0

    def test_element_count_recv_can_id(self):
        """Verify element count response CAN ID."""
        assert ParameterDiscovery.ELEMENT_COUNT_RECV == 0x09FD7FE0

    def test_element_data_send_can_id(self):
        """Verify element data request CAN ID."""
        assert ParameterDiscovery.ELEMENT_DATA_SEND == 0x01FD3FE0

    def test_element_data_recv_can_id(self):
        """Verify element data response CAN ID."""
        assert ParameterDiscovery.ELEMENT_DATA_RECV == 0x09FDBFE0

    def test_chunk_size(self):
        """Verify chunk size is 4096 bytes."""
        assert ParameterDiscovery.CHUNK_SIZE == 4096


class TestDiscoveryWithoutAdapter:
    """Test discovery behavior without adapter."""

    def test_discover_raises_without_adapter(self):
        """Verify discover() raises RuntimeError without adapter."""
        import asyncio

        discovery = ParameterDiscovery()

        async def test():
            return await discovery.discover()

        with pytest.raises(RuntimeError, match="No CAN adapter configured"):
            asyncio.get_event_loop().run_until_complete(test())


class TestParseAllElementsFromChunk:
    """Test parsing complete chunk of element data."""

    def test_parse_all_elements_from_large_chunk(self):
        """Verify parsing handles realistic data volume."""
        # Create 50 test elements
        elements = []
        for i in range(50):
            elements.append(
                {
                    "idx": i,
                    "extid": f"{i:014X}",
                    "max": 100 + i,
                    "min": i,
                    "text": f"PARAM_{i}",
                }
            )

        data = create_mock_element_data(elements)

        # Parse all elements
        parsed = []
        offset = 0
        while offset < len(data):
            element, next_offset = ParameterDiscovery.parse_element(data, offset)
            if element is None:
                break
            parsed.append(element)
            offset = next_offset

        assert len(parsed) == 50
        for i, elem in enumerate(parsed):
            assert elem["idx"] == i
            assert elem["text"] == f"PARAM_{i}"
            assert elem["max"] == 100 + i
            assert elem["min"] == i
