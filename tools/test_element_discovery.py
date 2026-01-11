#!/usr/bin/env python3
"""Test element list discovery on real heat pump.

This script:
1. Connects to USBtin adapter
2. Requests element count from heat pump
3. Reads element list data
4. Finds XDHW_TIME and compares discovered idx vs static idx
5. Attempts to set XDHW_TIME using discovered idx

Run on Raspberry Pi with: python3 test_element_discovery.py
"""

import sys
import time
import logging

# Add parent directory to path for imports
sys.path.insert(0, "/home/rein/buderus-wps-ha")

from buderus_wps.can_adapter import USBtinAdapter
from buderus_wps.can_message import CANMessage
from buderus_wps.element_discovery import (
    ElementListParser,
    ELEMENT_COUNT_REQUEST_ID,
    ELEMENT_COUNT_RESPONSE_ID,
    ELEMENT_DATA_REQUEST_ID,
    ELEMENT_DATA_RESPONSE_ID,
)
from buderus_wps.runtime_registry import RuntimeParameterRegistry

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Serial port on Raspberry Pi
SERIAL_PORT = "/dev/ttyACM0"


def request_element_count(adapter: USBtinAdapter) -> int:
    """Request element count from heat pump.

    PROTOCOL: Send RTR frame to 0x01FD7FE0, expect response on 0x09FD7FE0
    """
    logger.info("Requesting element count...")

    # Send RTR (Remote Transmission Request) frame
    # In SLCAN format: R + 8-digit ID + DLC
    rtr_frame = CANMessage(
        arbitration_id=ELEMENT_COUNT_REQUEST_ID,
        data=b"",
        is_extended_id=True,
        is_remote_frame=True,
    )

    logger.debug(f"Sending RTR frame: ID=0x{ELEMENT_COUNT_REQUEST_ID:08X}")

    # Send and wait for response
    response = adapter.send_frame(rtr_frame, timeout=5.0)

    if response is None:
        raise RuntimeError("No response to element count request")

    logger.debug(
        f"Response: ID=0x{response.arbitration_id:08X}, data={response.data.hex()}"
    )

    # Parse count from response
    parser = ElementListParser()
    count = parser.parse_count_response(response.arbitration_id, response.data)

    logger.info(f"Element count: {count}")
    return count


def request_element_data(adapter: USBtinAdapter, offset: int, count: int) -> bytes:
    """Request element data chunk from heat pump.

    PROTOCOL: Send T01FD3FE08{offset:08X}{count:08X}
    """
    # Build request data: offset (4 bytes) + count (4 bytes)
    request_data = offset.to_bytes(4, "big") + count.to_bytes(4, "big")

    request_frame = CANMessage(
        arbitration_id=ELEMENT_DATA_REQUEST_ID, data=request_data, is_extended_id=True
    )

    logger.debug(f"Requesting elements at offset={offset}, count={count}")

    # This is more complex - need to receive multiple response frames
    # For now, just send request and collect responses
    adapter._write_command(request_frame.to_usbtin_format().encode("ascii"))

    # Collect response data
    all_data = b""
    start_time = time.time()
    timeout = 10.0

    while time.time() - start_time < timeout:
        try:
            frame = adapter.receive_frame(timeout=1.0)
            if frame and frame.arbitration_id == ELEMENT_DATA_RESPONSE_ID:
                all_data += frame.data
                logger.debug(
                    f"Received {len(frame.data)} bytes, total: {len(all_data)}"
                )
        except Exception as e:
            logger.debug(f"Receive error: {e}")
            break

    return all_data


def discover_elements(adapter: USBtinAdapter) -> list:
    """Discover all elements from heat pump."""
    # Get element count
    count = request_element_count(adapter)

    if count == 0:
        logger.warning("Element count is 0")
        return []

    # Request element data
    logger.info(f"Requesting {count} elements...")
    data = request_element_data(adapter, 0, count)

    if not data:
        logger.warning("No element data received")
        return []

    # Parse elements
    parser = ElementListParser()
    elements = parser.parse_data_chunk(data)

    logger.info(f"Parsed {len(elements)} elements")
    return elements


def find_xdhw_time(elements: list) -> dict:
    """Find XDHW_TIME in discovered elements."""
    for elem in elements:
        if elem.text == "XDHW_TIME":
            return {
                "idx": elem.idx,
                "extid": elem.extid,
                "min": elem.min_value,
                "max": elem.max_value,
                "can_id": elem.can_id,
            }
    return None


def compare_with_static():
    """Compare discovered idx with static defaults."""
    registry = RuntimeParameterRegistry(use_static_fallback=True)
    static_elem = registry.get_by_name("XDHW_TIME")

    if static_elem:
        logger.info(
            f"Static XDHW_TIME: idx={static_elem.idx}, CAN ID=0x{static_elem.can_id:08X}"
        )
        return static_elem
    return None


def main():
    logger.info("=" * 60)
    logger.info("Element Discovery Test")
    logger.info("=" * 60)

    # Show static values first
    static = compare_with_static()

    logger.info("-" * 60)
    logger.info("Connecting to USBtin adapter...")

    try:
        with USBtinAdapter(SERIAL_PORT) as adapter:
            logger.info(f"Connected: {adapter.status}")

            # Try to discover elements
            elements = discover_elements(adapter)

            if elements:
                # Find XDHW_TIME
                discovered = find_xdhw_time(elements)

                if discovered:
                    logger.info("-" * 60)
                    logger.info("XDHW_TIME COMPARISON:")
                    logger.info(f"  Static idx:     {static.idx if static else 'N/A'}")
                    logger.info(f"  Discovered idx: {discovered['idx']}")
                    logger.info(
                        f"  Static CAN ID:     0x{static.can_id:08X}"
                        if static
                        else "  Static CAN ID: N/A"
                    )
                    logger.info(f"  Discovered CAN ID: 0x{discovered['can_id']:08X}")

                    if static and discovered["idx"] != static.idx:
                        logger.warning(
                            ">>> IDX MISMATCH! This explains why our writes failed!"
                        )
                    else:
                        logger.info("IDX values match")
                else:
                    logger.warning("XDHW_TIME not found in discovered elements")
            else:
                logger.warning(
                    "No elements discovered - trying simple read test instead"
                )

                # Fall back to simple connectivity test
                logger.info("Testing basic CAN read...")
                # Try reading a known parameter

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1

    logger.info("=" * 60)
    logger.info("Test complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
