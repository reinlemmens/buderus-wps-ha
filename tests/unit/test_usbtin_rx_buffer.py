"""Regression tests for issue #17: serial RX bytes lost between frame reads.

`_read_frame()` used to keep unread bytes in a local variable, so every byte
after the first complete frame in a serial chunk was discarded. The next read
then started mid-frame and `_lenient_parse_frame()` turned the fragment into a
fake 11-bit frame (e.g. "4062200E1" -> ID 0x062 = base 0x0062 / idx 0, the C3
room temperature) carrying a setpoint or other payload.

The frame strings below come from a 10-minute capture on the real bus
(2026-11-18).
"""

from __future__ import annotations

from collections import deque

import pytest
from buderus_wps.broadcast_monitor import BroadcastMonitor
from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage

ROOM_C3 = b"T0C00006220" + b"0D3" + b"\r"  # room temp C3 = 21.1
SETPOINT_C3 = b"T0C084062200E1\r"  # adjusted setpoint C3 = 22.5
OUTDOOR_C3 = b"T0003006220064\r"  # outdoor = 10.0


class FakeSerial:
    """Minimal pyserial stand-in that delivers predefined chunks."""

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = deque(chunks)
        self.is_open = True

    @property
    def in_waiting(self) -> int:
        return len(self._chunks[0]) if self._chunks else 0

    def read(self, size: int = 1) -> bytes:
        if not self._chunks:
            return b""
        chunk = self._chunks[0]
        data, rest = chunk[:size], chunk[size:]
        if rest:
            self._chunks[0] = rest
        else:
            self._chunks.popleft()
        return data

    def reset_input_buffer(self) -> None:
        self._chunks.clear()


def _adapter(chunks: list[bytes]) -> USBtinAdapter:
    adapter = USBtinAdapter("/dev/null", read_only=True)
    adapter._serial = FakeSerial(chunks)  # type: ignore[assignment]
    return adapter


def _read_all(adapter: USBtinAdapter, limit: int = 20) -> list[CANMessage]:
    frames = []
    for _ in range(limit):
        frame = adapter._read_frame(timeout=0.1)
        if frame is None:
            break
        frames.append(frame)
    return frames


class TestReadFrameKeepsBufferedBytes:
    def test_multiple_frames_in_one_chunk_are_all_returned(self) -> None:
        adapter = _adapter([SETPOINT_C3 + ROOM_C3 + OUTDOOR_C3])

        ids = [f.arbitration_id for f in _read_all(adapter)]

        assert ids == [0x0C084062, 0x0C000062, 0x00030062]

    def test_frame_split_across_chunks_is_reassembled(self) -> None:
        # Real-world failure: chunk boundary right after "T0C08"
        adapter = _adapter([ROOM_C3 + b"T0C08", b"4062200E1\r"])

        frames = _read_all(adapter)

        assert [f.arbitration_id for f in frames] == [0x0C000062, 0x0C084062]
        assert frames[1].data == b"\x00\xe1"

    def test_flush_discards_buffered_partial_frame(self) -> None:
        adapter = _adapter([ROOM_C3 + b"T0C08"])
        assert adapter._read_frame(timeout=0.1) is not None

        adapter.flush_input_buffer()
        adapter._serial._chunks.append(OUTDOOR_C3)  # type: ignore[union-attr]

        frames = _read_all(adapter)
        assert [f.arbitration_id for f in frames] == [0x00030062]


class TestFragmentsAreNotParsedAsFrames:
    @pytest.mark.parametrize(
        "fragment",
        [
            "4062200E1",  # setpoint C3 cut after "T0C08" -> fake ID 0x062
            "0062200064",  # outdoor cut after "T0003" -> fake ID 0x062
            "C084062200E1",  # cut after "T0"
            "200E1",
        ],
    )
    def test_lenient_parse_rejects_fragment(self, fragment: str) -> None:
        adapter = USBtinAdapter("/dev/null", read_only=True)

        assert adapter._lenient_parse_frame(fragment) is None

    def test_leading_fragment_is_skipped_not_returned(self) -> None:
        # Stream starts mid-frame (e.g. right after open or flush)
        adapter = _adapter([b"4062200E1\r" + ROOM_C3])

        frames = _read_all(adapter)

        assert [f.arbitration_id for f in frames] == [0x0C000062]


class TestBroadcastMonitorIgnoresStandardIds:
    def test_standard_id_frame_does_not_map_to_room_temp(self) -> None:
        monitor = BroadcastMonitor.__new__(BroadcastMonitor)
        fake = CANMessage(arbitration_id=0x062, data=b"\x00\xe1")

        assert monitor._process_frame(fake) is None
