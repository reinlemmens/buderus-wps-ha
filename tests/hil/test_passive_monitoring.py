"""Hardware-in-loop tests for passive CAN monitoring.

T077: HIL test for passive CAN monitoring with real USBtin adapter.

These tests require physical hardware:
- USBtin CAN adapter connected at SERIAL_PORT
- Buderus WPS heat pump on CAN bus broadcasting data

Run with: pytest tests/hil/ --run-hil

Hardware Verified: 2025-12-05 on Raspberry Pi with USBtin at /dev/ttyACM0
"""

import os
import time
from typing import Dict

import pytest

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import (
    CAN_PREFIX_DATA,
    CAN_PREFIX_STATUS,
    ELEMENT_E21,
    ELEMENT_E22,
)

# Configuration - can be overridden via environment variables
SERIAL_PORT = os.environ.get("USBTIN_PORT", "/dev/ttyACM0")
LISTEN_DURATION = float(os.environ.get("HIL_LISTEN_DURATION", "5.0"))


# Skip all HIL tests if hardware is not available or --run-hil not specified
pytestmark = pytest.mark.skipif(
    not os.path.exists(SERIAL_PORT) or not os.environ.get("RUN_HIL_TESTS"),
    reason=f"HIL tests require hardware at {SERIAL_PORT} and RUN_HIL_TESTS=1",
)


class TestPassiveMonitoring:
    """Test passive CAN bus monitoring with real hardware.

    These tests validate:
    - Connection to USBtin adapter
    - Receiving broadcast CAN messages
    - CAN ID decoding from real heat pump data
    - Data consistency with known FHEM values
    """

    def test_connection_opens(self):
        """Verify connection to USBtin adapter opens successfully."""
        with USBtinAdapter(SERIAL_PORT) as adapter:
            assert adapter.is_open
            assert adapter.status == "connected"

    def test_receive_broadcast_messages(self):
        """Verify broadcast CAN messages are received from heat pump."""
        with USBtinAdapter(SERIAL_PORT) as adapter:
            messages_received = 0
            start = time.time()

            while time.time() - start < LISTEN_DURATION:
                try:
                    frame = adapter.receive_frame(timeout=0.5)
                    if frame:
                        messages_received += 1
                except TimeoutError:
                    pass

            # Heat pump broadcasts 30+ messages/second typically
            # Expect at least 10 in 5 seconds (conservative)
            assert messages_received >= 10, (
                f"Expected at least 10 messages in {LISTEN_DURATION}s, "
                f"got {messages_received}"
            )

    def test_can_id_decoding_real_data(self):
        """Verify CAN ID decoding works with real broadcast data."""
        with USBtinAdapter(SERIAL_PORT) as adapter:
            data_frames_found = False
            start = time.time()

            while time.time() - start < LISTEN_DURATION:
                try:
                    frame = adapter.receive_frame(timeout=0.5)
                    if frame and frame.data:
                        prefix, param_idx, element_type = frame.decode_broadcast_id()

                        # Verify prefix is a known value
                        assert prefix in (
                            CAN_PREFIX_DATA,
                            CAN_PREFIX_STATUS,
                            0x08,
                        ), f"Unknown prefix 0x{prefix:02X} in CAN ID 0x{frame.arbitration_id:08X}"

                        # Verify element_type is reasonable (12 bits)
                        assert 0 <= element_type <= 0xFFF

                        if prefix == CAN_PREFIX_DATA:
                            data_frames_found = True

                except TimeoutError:
                    pass

            assert data_frames_found, "No data frames (prefix 0x0C) received"

    def test_collect_temperature_readings(self):
        """Collect temperature readings and verify they are in valid range."""
        readings: Dict[int, int] = {}

        with USBtinAdapter(SERIAL_PORT) as adapter:
            start = time.time()

            while time.time() - start < LISTEN_DURATION:
                try:
                    frame = adapter.receive_frame(timeout=0.5)
                    if frame and frame.data:
                        prefix, param_idx, element_type = frame.decode_broadcast_id()

                        # Collect data frames with E21/E22 element types (temperatures)
                        if prefix == CAN_PREFIX_DATA and element_type in (
                            ELEMENT_E21,
                            ELEMENT_E22,
                        ):
                            value = int.from_bytes(frame.data, "big", signed=True)
                            readings[frame.arbitration_id] = value

                except TimeoutError:
                    pass

        # Verify we collected some temperature readings
        assert len(readings) > 0, "No temperature readings collected"

        # Verify temperature values are in reasonable range
        # Heat pump temps typically -40°C to 100°C (-400 to 1000 in 0.1°C units)
        for can_id, value in readings.items():
            assert -500 <= value <= 1200, (
                f"Temperature value {value} at CAN ID 0x{can_id:08X} "
                f"out of expected range (-500 to 1200 = -50°C to 120°C)"
            )


class TestFHEMComparison:
    """Compare live readings with known FHEM reference values.

    These tests use CAN IDs verified against FHEM plugin output (2025-12-05).
    """

    # Known FHEM readings for comparison (CAN ID -> expected range)
    # Values are in 0.1°C units, ranges account for real-time variation
    KNOWN_TEMPERATURE_CAN_IDS = [
        0x0C084060,  # GT1 temperature
        0x0C084061,  # GT1-2 temperature
        0x0C084062,  # GT1-3 temperature
        0x0C084063,  # GT1-4 temperature
        0x0C0E8060,  # GT8 temperature (flow temp)
    ]

    def test_known_can_ids_present(self):
        """Verify known CAN IDs from FHEM are present in broadcast data."""
        readings: Dict[int, int] = {}

        with USBtinAdapter(SERIAL_PORT) as adapter:
            start = time.time()

            while time.time() - start < LISTEN_DURATION * 2:  # Longer wait for all IDs
                try:
                    frame = adapter.receive_frame(timeout=0.5)
                    if frame and frame.data:
                        readings[frame.arbitration_id] = int.from_bytes(
                            frame.data, "big", signed=True
                        )
                except TimeoutError:
                    pass

        # Check how many known IDs were found
        found_ids = [cid for cid in self.KNOWN_TEMPERATURE_CAN_IDS if cid in readings]

        assert len(found_ids) >= 3, (
            f"Expected at least 3 of {len(self.KNOWN_TEMPERATURE_CAN_IDS)} known CAN IDs, "
            f"found {len(found_ids)}: {[hex(cid) for cid in found_ids]}"
        )

    def test_temperature_values_reasonable(self):
        """Verify temperature values are in physically reasonable ranges."""
        readings: Dict[int, int] = {}

        with USBtinAdapter(SERIAL_PORT) as adapter:
            start = time.time()

            while time.time() - start < LISTEN_DURATION * 2:
                try:
                    frame = adapter.receive_frame(timeout=0.5)
                    if (
                        frame
                        and frame.data
                        and frame.arbitration_id in self.KNOWN_TEMPERATURE_CAN_IDS
                    ):
                        readings[frame.arbitration_id] = int.from_bytes(
                            frame.data, "big", signed=True
                        )
                except TimeoutError:
                    pass

        for can_id, value in readings.items():
            # Indoor temps (GT1-4): typically 15-30°C (150-300)
            if can_id in [0x0C084060, 0x0C084061, 0x0C084062, 0x0C084063]:
                assert (
                    100 <= value <= 400
                ), f"Indoor temp at 0x{can_id:08X} = {value/10}°C seems out of range"
            # Flow temp (GT8): typically 20-70°C (200-700)
            elif can_id == 0x0C0E8060:
                assert (
                    150 <= value <= 800
                ), f"Flow temp at 0x{can_id:08X} = {value/10}°C seems out of range"
